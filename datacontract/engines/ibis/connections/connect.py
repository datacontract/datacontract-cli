"""Build an ibis backend connection for an ODCS server.

Replaces the per-source soda configuration builders. Each branch maps the
``Server`` fields and the same ``DATACONTRACT_*`` environment variables the soda
connections used onto an ``ibis.<backend>.connect(...)`` call. File sources reuse
the DuckDB view builder (``duckdb_connection.py``) and Kafka reuses the topic
reader (``kafka.py``), which likewise loads its messages into DuckDB; both are
wrapped with the ibis duckdb backend. Only the Spark-session server types
(``dataframe``, ``databricks``) use the ibis pyspark backend.
"""

from __future__ import annotations

import logging
import typing

from open_data_contract_standard.model import OpenDataContractStandard, Server

from datacontract.config import DEPRECATED_OPTIONS, Config, unknown_snowflake_env_names
from datacontract.engines.ibis.connections import aws_credentials
from datacontract.engines.ibis.connections.duckdb_connection import get_duckdb_connection
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Check, ResultEnum, Run
from datacontract.model.server import get_server_type

if typing.TYPE_CHECKING:
    import ibis
    from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)

_FILE_SERVER_TYPES = {"s3", "gcs", "azure", "local"}
_SUPPORTED_FILE_FORMATS = {"json", "parquet", "csv", "delta"}


def _import_ibis():
    try:
        import ibis

        return ibis
    except ImportError as e:  # pragma: no cover - import guard
        raise ImportError(
            "ibis-framework is required to run datacontract tests. "
            "Install with: pip install 'datacontract-cli[<server-type>]'"
        ) from e


def connect_ibis(
    run: Run,
    data_contract: OpenDataContractStandard,
    server: Server,
    spark: "SparkSession" = None,
    duckdb_connection=None,
    schema_name: str = "all",
    config: Config | None = None,
    untrusted_contract: bool = False,
) -> "ibis.BaseBackend | None":
    """Return a connected ibis backend, or ``None`` if the server is unsupported.

    On an unsupported server type/format an explanatory warning ``Check`` is
    appended to ``run`` (mirroring the previous soda behaviour).
    """
    ibis = _import_ibis()
    config = Config.resolve(config)
    server_type = get_server_type(server)

    if server_type in _FILE_SERVER_TYPES:
        if server.format not in _SUPPORTED_FILE_FORMATS:
            _unsupported(run, f"Format {server.format} not yet supported by datacontract CLI")
            return None
        run.log_info(f"Connecting to {server_type} {server.format} via duckdb")
        con = get_duckdb_connection(
            data_contract,
            server,
            run,
            duckdb_connection,
            schema_name=schema_name,
            config=config,
            untrusted_contract=untrusted_contract,
        )
        return ibis.duckdb.from_connection(con)

    if server_type == "duckdb":
        return _connect_duckdb_database(ibis, server, run, config)

    if server_type == "kafka":
        from datacontract.engines.ibis.connections.kafka import read_kafka_topic

        run.log_info(f"Connecting to kafka {server.format} via duckdb")
        con = read_kafka_topic(data_contract, server, run, config, duckdb_connection)
        return ibis.duckdb.from_connection(con)

    if server_type == "dataframe":
        if spark is None:
            run.log_warn(
                "Server type dataframe only works with the Python library and requires a Spark session, "
                "please provide one with the DataContract class"
            )
            return None
        from datacontract.engines.ibis.connections.kafka import add_spark_nested_views_for_contract

        add_spark_nested_views_for_contract(spark, data_contract, schema_name=schema_name)
        return ibis.pyspark.connect(session=spark)

    if server_type == "databricks":
        if spark is not None:
            run.log_info("Connecting to databricks via spark")
            database_name = ".".join(filter(None, [server.catalog, server.schema_]))
            if database_name:
                spark.sql(f"USE {database_name}")
            from datacontract.engines.ibis.connections.kafka import add_spark_nested_views_for_contract

            add_spark_nested_views_for_contract(spark, data_contract, schema_name=schema_name)
            return ibis.pyspark.connect(session=spark)
        return _connect_databricks(ibis, server, run, config)

    if server_type == "postgres":
        return ibis.postgres.connect(
            host=config.get_postgres_host() or server.host,
            port=config.get_postgres_port() or (int(server.port) if server.port else 5432),
            user=config.get_postgres_username(required=True),
            password=config.get_postgres_password(required=True),
            database=config.get_postgres_database() or server.database,
            schema=config.get_postgres_schema() or server.schema_,
        )

    if server_type == "redshift":
        from datacontract.engines.ibis.connections.redshift_credentials import resolve_redshift_login
        from datacontract.engines.ibis.connections.redshift_patch import CLIENT_ENCODING

        host = config.get_redshift_host() or server.host
        database = config.get_redshift_database() or server.database
        login = resolve_redshift_login(host, database, config)
        kwargs = dict(
            host=host,
            port=config.get_redshift_port() or (int(server.port) if server.port else 5439),
            user=login.user,
            database=database,
            schema=config.get_redshift_schema() or server.schema_,
            client_encoding=CLIENT_ENCODING,
        )
        if login.password:
            kwargs["password"] = login.password
        if login.sslmode:
            kwargs["sslmode"] = login.sslmode
        # Redshift speaks the postgres wire protocol; ibis has no dedicated backend.
        con = ibis.postgres.connect(**kwargs)
        # ibis's postgres schema introspection joins pg_catalog.pg_enum, which
        # Redshift does not expose; patch it out so model lookups don't fail.
        from datacontract.engines.ibis.connections.redshift_patch import apply_redshift_compatibility_patch

        apply_redshift_compatibility_patch(con)
        return con

    if server_type == "mysql":
        return _connect_mysql_via_duckdb(ibis, data_contract, server, run, schema_name, config)

    if server_type == "snowflake":
        return ibis.snowflake.connect(**_snowflake_connection_kwargs(server, run, config))

    if server_type == "bigquery":
        return _connect_bigquery(ibis, server, config)

    # `mssql` is what ODBC, ibis and dbt call SQL Server; ODCS spells it `sqlserver`.
    if server_type in ("sqlserver", "mssql"):
        return _connect_sqlserver(ibis, server, config)

    if server_type == "oracle":
        from datacontract.engines.ibis.connections.oracle_patch import apply_oracle_compatibility_patch

        service_name = config.get_oracle_service_name() or server.serviceName or server.database
        oracle_client_dir = config.get_oracle_client_dir()
        if oracle_client_dir:
            import oracledb

            oracledb.init_oracle_client(lib_dir=oracle_client_dir)
        con = ibis.oracle.connect(
            host=config.get_oracle_host() or server.host,
            port=config.get_oracle_port() or (int(server.port) if server.port else 1521),
            user=config.get_oracle_username(required=True),
            password=config.get_oracle_password(required=True),
            service_name=service_name,
        )
        apply_oracle_compatibility_patch(con)
        return con

    if server_type == "trino":
        return _connect_trino(ibis, server, config)

    if server_type == "athena":
        return _connect_athena(ibis, server, config)

    if server_type == "impala":
        return _connect_impala(ibis, server, config)

    _unsupported(run, f"Server type {server_type} not yet supported by datacontract CLI")
    return None


def _connect_databricks(ibis, server: Server, run: Run, config: Config):
    """Connect to Databricks SQL directly, selecting the auth method from env vars.

    Auth is resolved in priority order, so an existing token-based setup keeps
    working unchanged:

    1. personal access token (``DATACONTRACT_DATABRICKS_TOKEN``) — the default
    2. OAuth machine-to-machine / service principal, from
       ``DATACONTRACT_DATABRICKS_CLIENT_ID`` + ``DATACONTRACT_DATABRICKS_CLIENT_SECRET``
       (the usual choice for CI/CD)
    3. a local Databricks config profile (``DATACONTRACT_DATABRICKS_PROFILE``),
       delegating to the Databricks SDK's unified auth (also covers Azure CLI/MSI)
    4. an explicit connector ``auth_type`` (``DATACONTRACT_DATABRICKS_AUTH_TYPE``),
       e.g. ``databricks-oauth`` for the interactive user-to-machine browser flow

    The OAuth credential providers build their SDK ``Config`` lazily, so token
    exchange happens when the connection is opened rather than while reading env.
    """
    # the config option wins over the contract, like the other server-detail overrides
    host = (
        config.get_databricks_server_hostname() or server.host or config.get_databricks_server_hostname(required=True)
    )
    kwargs = dict(
        server_hostname=host,
        http_path=config.get_databricks_http_path(),
        catalog=config.get_databricks_catalog() or server.catalog,
        schema=config.get_databricks_schema() or server.schema_,
    )

    token = config.get_databricks_token()
    client_id = config.get_databricks_client_id()
    client_secret = config.get_databricks_client_secret()
    profile = config.get_databricks_profile()
    auth_type = config.get_databricks_auth_type()

    if token:
        run.log_info("Connecting to databricks with a personal access token")
        return _databricks_connect(ibis, access_token=token, **kwargs)

    if client_id and client_secret:
        run.log_info("Connecting to databricks with an OAuth service principal (M2M)")
        sdk_host = host if host.startswith("http") else f"https://{host}"
        kwargs["credentials_provider"] = _databricks_credentials_provider(
            service_principal=True, host=sdk_host, client_id=client_id, client_secret=client_secret
        )
        return _databricks_connect(ibis, **kwargs)

    if profile:
        run.log_info(f"Connecting to databricks with config profile '{profile}'")
        kwargs["credentials_provider"] = _databricks_credentials_provider(profile=profile)
        return _databricks_connect(ibis, **kwargs)

    if auth_type:
        run.log_info(f"Connecting to databricks with auth_type '{auth_type}'")
        return _databricks_connect(ibis, auth_type=auth_type, **kwargs)

    # Nothing configured: fail with the same clear message as before.
    token = config.get_databricks_token(required=True)
    return _databricks_connect(ibis, access_token=token, **kwargs)


def _databricks_connect(ibis, **kwargs):
    """Connect to Databricks without creating ibis's memtable staging volume.

    ibis's Databricks backend creates a staging volume for memtables in the
    target schema at connect time (``CREATE VOLUME IF NOT EXISTS``), named
    after the client host and pid and never cleaned up. Contract tests only
    ever read, so the volume is never used: skipping its setup lets read-only
    principals without CREATE VOLUME permission run tests and keeps repeated
    runs from littering the schema with per-run volumes.

    Workaround until https://github.com/dataqcompany/ibis/pull/2 (drops the
    CREATE VOLUME requirement for read-only connections) is merged and
    released; then the ``_post_connect`` patch can go.
    """
    from ibis.backends.databricks import Backend

    from datacontract.engines.ibis.connections.databricks_patch import apply_databricks_compatibility_patch

    # Databricks-only column types (GEOGRAPHY(4326), …) otherwise fail the whole
    # model when ibis reflects the table.
    apply_databricks_compatibility_patch()

    original_post_connect = Backend._post_connect
    Backend._post_connect = lambda self, *, memtable_volume=None: None
    try:
        return ibis.databricks.connect(**kwargs)
    finally:
        Backend._post_connect = original_post_connect


def _databricks_credentials_provider(service_principal: bool = False, **config_kwargs):
    """Return a ``credentials_provider`` callable for the Databricks SQL connector.

    The connector expects a zero-arg callable returning a header factory. We
    build the SDK ``Config`` lazily inside that callable so authentication (and
    any OAuth token exchange) happens at connect time, with credential resolution
    delegated to the Databricks SDK's unified auth.

    ``service_principal`` hands over the SDK's OAuth service-principal provider
    rather than the generic ``Config.authenticate`` header factory. Since
    databricks-sql-connector 4.3.0 every provider is wrapped in a token-federation
    layer, and a token that unified auth resolved through some other issuer (Azure
    AD, say) sends it into a token exchange that fails, so ``OpenSession`` is
    rejected with HTTP 400 (#1389). We already know these credentials name a
    service principal, so we ask for that provider by name; falling back to
    ``authenticate`` when the host publishes no OIDC endpoints and there is
    therefore no such provider to hand over.
    """

    def credentials_provider():
        from databricks.sdk.core import Config, oauth_service_principal

        config = Config(**config_kwargs)
        if service_principal:
            return oauth_service_principal(config) or config.authenticate
        return config.authenticate

    return credentials_provider


def _connect_bigquery(ibis, server: Server, config: Config):
    credentials = _bigquery_credentials(config)
    billing_project = config.get_bigquery_billing_project()
    project = config.get_bigquery_project() or server.project
    dataset = config.get_bigquery_dataset() or server.dataset
    if billing_project and not project:
        raise DataContractException(
            type="bigquery-connection",
            name="missing_project",
            reason=(
                "Project is required for BigQuery connection when a billing project is set. "
                "Set the server's `project` or DATACONTRACT_BIGQUERY_PROJECT."
            ),
            engine="datacontract-cli",
        )
    if not dataset:
        raise DataContractException(
            type="bigquery-connection",
            name="missing_dataset",
            reason=(
                "Dataset is required for BigQuery connection. "
                "Set the server's `dataset` or DATACONTRACT_BIGQUERY_DATASET."
            ),
            engine="datacontract-cli",
        )

    # ibis reads the billing project from ``project_id`` and the data project from a
    # ``<project>.<dataset>`` qualified ``dataset_id``. Passing a pre-built client
    # instead would make ibis take its project as both.
    kwargs = dict(
        project_id=billing_project or project,
        dataset_id=f"{project}.{dataset}" if project else dataset,
    )
    if credentials:
        kwargs["credentials"] = credentials
    return ibis.bigquery.connect(**kwargs)


_BIGQUERY_SCOPES = ["https://www.googleapis.com/auth/bigquery"]


def _bigquery_credentials(config: Config):
    """Resolve the BigQuery credentials, or ``None`` to let ibis use ADC/WIF.

    ``DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH`` selects a service account key
    file. ``DATACONTRACT_BIGQUERY_IMPERSONATION_ACCOUNT`` then impersonates that
    service account, using the key file (or the ambient default credentials) as the
    source principal — the caller needs ``roles/iam.serviceAccountTokenCreator`` on
    the target.
    """
    credentials_path = config.get_bigquery_account_info_json_path()
    credentials = None
    if credentials_path:
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_file(credentials_path)

    impersonation_account = config.get_bigquery_impersonation_account()
    if impersonation_account:
        import google.auth
        from google.auth import impersonated_credentials

        source_credentials = credentials
        if source_credentials is None:
            source_credentials, _ = google.auth.default(scopes=_BIGQUERY_SCOPES)
        credentials = impersonated_credentials.Credentials(
            source_credentials=source_credentials,
            target_principal=impersonation_account,
            target_scopes=_BIGQUERY_SCOPES,
        )

    return credentials


def _connect_impala(ibis, server: Server, config: Config):
    """Connect to Impala, making the transport and auth options configurable.

    ``auth_mechanism`` is a native ``ibis.impala.connect`` argument; ``use_http_transport``
    and ``http_path`` are forwarded verbatim by ibis to ``impyla.connect``. None of the
    three used to be passed at all, so a Cloudera Virtual Warehouse (LDAP over HTTPS on
    443) fell back to impyla's binary NOSASL defaults and failed the thrift handshake with
    ``TSocket read 0 bytes``.

    Each option defaults to impyla's own default, so an unconfigured connection behaves
    exactly as it did before. The one exception is ``use_ssl``, which has defaulted to
    true since Impala support landed and stays that way.
    """
    return ibis.impala.connect(
        host=config.get_impala_host() or server.host,
        port=config.get_impala_port() or (int(server.port) if server.port else 21050),
        user=config.get_impala_username(),
        password=config.get_impala_password(),
        database=config.get_impala_database() or getattr(server, "database", None),
        use_ssl=config.get_impala_use_ssl(default=True),
        auth_mechanism=(config.get_impala_auth_mechanism() or "NOSASL"),
        use_http_transport=config.get_impala_use_http_transport(default=False),
        http_path=(config.get_impala_http_path() or ""),
    )


def _snowflake_private_key(value: str | None):
    """Normalize DATACONTRACT_SNOWFLAKE_PRIVATE_KEY to DER bytes.

    The connector accepts the private key as DER bytes on every supported
    version; the base64-DER string form only works from connector 3.13 on, and
    PEM text never does. Accept both PEM (converted) and base64-DER (decoded),
    so the option works regardless of the pinned connector version.
    """
    if not value:
        return None
    if "-----BEGIN" in value:
        try:
            from cryptography.hazmat.primitives import serialization

            key = serialization.load_pem_private_key(value.encode(), password=None)
            return key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        except Exception as e:
            raise DataContractException(
                type="snowflake-connection",
                name="invalid_private_key",
                reason=f"DATACONTRACT_SNOWFLAKE_PRIVATE_KEY could not be read as an unencrypted PEM private key: {e}. "
                f"For encrypted keys, use DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_FILE with "
                f"DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_FILE_PWD.",
                engine="datacontract-cli",
            )
    import base64

    try:
        return base64.b64decode(value, validate=True)
    except Exception:
        raise DataContractException(
            type="snowflake-connection",
            name="invalid_private_key",
            reason="DATACONTRACT_SNOWFLAKE_PRIVATE_KEY must be a PEM private key or base64-encoded DER.",
            engine="datacontract-cli",
        )


def _snowflake_connection_kwargs(server: Server, run: Run, config: Config) -> dict:
    """Build the ``ibis.snowflake.connect`` kwargs, one line per supported option.

    Every option is enumerated; the old behavior of forwarding any
    DATACONTRACT_SNOWFLAKE_* variable verbatim is gone (unknown names are warned
    about instead — see unknown_snowflake_env_names). ``account``, ``database``
    and ``schema`` come from the ODCS server object unless the matching config
    option overrides them; the driver's ``user`` parameter keeps its
    DATACONTRACT_SNOWFLAKE_USERNAME spelling.
    """
    for name in unknown_snowflake_env_names():
        run.log_warn(
            f"{name} is not a supported Snowflake option and is ignored. Arbitrary "
            f"DATACONTRACT_SNOWFLAKE_* variables are no longer forwarded to the connector; "
            f"use a connections.toml for parameters the CLI does not support directly."
        )

    kwargs = {}

    def put(param, value):
        if value:
            kwargs[param] = value

    put("user", config.get_snowflake_username())
    put("password", config.get_snowflake_password())
    put("authenticator", config.get_snowflake_authenticator())
    put("role", config.get_snowflake_role())
    put("token", config.get_snowflake_token())
    put("passcode", config.get_snowflake_passcode())
    put("private_key", _snowflake_private_key(config.get_snowflake_private_key()))
    put("private_key_file", config.get_snowflake_private_key_file())
    put("private_key_file_pwd", config.get_snowflake_private_key_file_pwd())
    put("warehouse", config.get_snowflake_warehouse())
    put("host", config.get_snowflake_host())
    put("login_timeout", config.get_snowflake_login_timeout())
    put("network_timeout", config.get_snowflake_network_timeout())
    put("socket_timeout", config.get_snowflake_socket_timeout())
    put("port", config.get_snowflake_port())

    # Names this CLI documented for key-pair auth and timeouts that snowflake-connector-python
    # has never accepted. The driver ignores unknown parameters instead of raising, so setting
    # one of these used to do nothing at all and surfaced as an unrelated authentication error.
    # They are kept as synonyms for the real parameters, with a deprecation warning; an
    # explicitly set replacement wins over the deprecated synonym. The mapping lives in
    # DEPRECATED_OPTIONS, shared with the accessor warnings and the generated docs.
    for deprecated_field, replacement_field in DEPRECATED_OPTIONS.items():
        if not deprecated_field.startswith("snowflake_"):
            continue
        value = getattr(config, f"get_{deprecated_field}")()
        if not value:
            continue
        deprecated = deprecated_field.removeprefix("snowflake_").upper()
        replacement = replacement_field.removeprefix("snowflake_")
        run.log_warn(
            f"DATACONTRACT_SNOWFLAKE_{deprecated} is deprecated and will be removed in a future release, "
            f"use DATACONTRACT_SNOWFLAKE_{replacement.upper()} instead"
        )
        kwargs.setdefault(replacement, value)

    # ibis tries to CREATE DATABASE for helper UDFs on connect (create_object_udfs=True).
    # datacontract only reads, and the read-only roles used for testing lack CREATE DATABASE,
    # so this otherwise emits a noisy "Insufficient privileges" warning. Default it off, but
    # let users opt back in via DATACONTRACT_SNOWFLAKE_CREATE_OBJECT_UDFS=true.
    return dict(
        create_object_udfs=config.get_snowflake_create_object_udfs(default=False),
        account=config.get_snowflake_account() or server.account,
        database=config.get_snowflake_database() or server.database,
        schema=config.get_snowflake_schema() or server.schema_,
        **kwargs,
    )


def _connect_duckdb_database(ibis, server: Server, run: Run, config: Config):
    """Connect to a DuckDB database file.

    Distinct from the file server types (`local`, `s3`, …), which read data files
    *through* DuckDB into views: here the DuckDB database itself is the data
    source, and the contract's schema objects are the tables inside it. ODCS
    carries the path to the database file in the server's `database` field.
    """
    path = config.get_duckdb_database() or server.database
    if not path:
        _unsupported(run, "For server type 'duckdb', a 'database' (the path to the database file) must be defined.")
        return None
    read_only = path != ":memory:"
    run.log_info(f"Connecting to the duckdb database at {path}")
    try:
        # Opened read-only: a test reads the data, and a second process may hold
        # the same database open at the same time.
        con = ibis.duckdb.connect(path, read_only=read_only)
    except Exception as e:
        raise DataContractException(
            type="connection",
            name="Connect to duckdb",
            result=ResultEnum.error,
            reason=f"Could not open the duckdb database at {path}: {e}",
            engine="datacontract-cli",
            original_exception=e,
        )

    schema = config.get_duckdb_schema() or server.schema_
    if schema:
        # `connect()` takes no schema, so the session's search path is set here:
        # otherwise an unqualified table name in a quality rule's SQL resolves
        # against `main` and is not found.
        escaped = schema.replace('"', '""')
        con.raw_sql(f'USE "{escaped}"')
    return con


def _connect_mysql_via_duckdb(ibis, data_contract, server: Server, run: Run, schema_name: str, config: Config):
    """Connect to MySQL through DuckDB's ``mysql`` extension.

    ibis's native MySQL backend requires ``mysqlclient`` (a C extension with no
    macOS/Linux wheels, needing system MySQL client libraries to build). Routing
    through DuckDB keeps the install pure-pip: DuckDB ATTACHes the MySQL database
    and we expose each contract model as a view in the default catalog so the
    rest of the engine works unchanged.
    """
    import duckdb

    from datacontract.engines.ibis.connections.duckdb_connection import _load_extension

    user = config.get_mysql_username(required=True)
    password = config.get_mysql_password(required=True)
    host = config.get_mysql_host() or server.host or "localhost"
    port = config.get_mysql_port() or (int(server.port) if server.port else 3306)
    database = config.get_mysql_database() or server.database

    con = duckdb.connect()
    _load_extension(con, "mysql", "mysql")

    parts = [f"host={host}", f"port={port}", f"user={user}", f"password={password}"]
    if database:
        parts.append(f"database={database}")
    conn_str = " ".join(parts).replace("'", "''")
    run.log_info(f"Attaching MySQL {host}:{port} via the duckdb mysql extension")
    con.execute(f"ATTACH '{conn_str}' AS mysqldb (TYPE mysql)")

    if data_contract.schema_:
        for schema_obj in data_contract.schema_:
            if schema_name != "all" and schema_obj.name != schema_name:
                continue
            model = schema_obj.physicalName or schema_obj.name
            _materialize_attached_table(con, "mysqldb", database, model)

    return ibis.duckdb.from_connection(con)


def _materialize_attached_table(con, catalog: str, database: str | None, model: str):
    """Copy an attached-catalog table into a local DuckDB table named ``model``.

    Materializing (rather than a view over the attached catalog) ensures all
    checks run against local DuckDB data. Pushing complex check queries through
    the DuckDB MySQL scanner can trigger DuckDB binder errors (e.g. on the
    grouped duplicate-count query), so we read the rows once and check locally.
    """
    candidates = []
    if database:
        candidates.append(f'{catalog}."{database}"."{model}"')
    candidates.append(f'{catalog}."{model}"')
    last_error = None
    for src in candidates:
        try:
            con.execute(f'CREATE OR REPLACE TABLE "{model}" AS SELECT * FROM {src}')
            return
        except Exception as e:  # noqa: BLE001 - try the next naming candidate
            last_error = e
    if last_error is not None:
        logger.warning("Could not read MySQL table '%s': %s", model, last_error)


def _connect_sqlserver(ibis, server: Server, config: Config):
    return ibis.mssql.connect(**_sqlserver_connection_kwargs(server, config))


def _sqlserver_connection_kwargs(server: Server, config: Config) -> dict:
    """Build the ``ibis.mssql.connect`` kwargs, selecting the auth mode from env vars.

    ``DATACONTRACT_SQLSERVER_AUTHENTICATION`` picks the mode (default ``sql``):

    - ``sql`` — SQL Server auth with ``USERNAME`` / ``PASSWORD``
    - ``windows`` — Windows integrated auth (Kerberos/NTLM), no credentials
    - ``ActiveDirectoryPassword`` — Entra ID with ``USERNAME`` / ``PASSWORD``
    - ``ActiveDirectoryServicePrincipal`` — Entra ID with ``CLIENT_ID`` / ``CLIENT_SECRET``
    - ``ActiveDirectoryInteractive`` — Entra ID browser login (``USERNAME`` as a hint)
    - ``cli`` — reuse an ``az login`` session via the Azure default credential chain

    The legacy ``DATACONTRACT_SQLSERVER_TRUSTED_CONNECTION=true`` is equivalent to
    ``windows``, and applies only when ``DATACONTRACT_SQLSERVER_AUTHENTICATION`` is
    unset — an explicitly chosen mode always wins. Extra keys (``Authentication``,
    ``Trusted_Connection``, ``Encrypt``, ``TrustServerCertificate``) are forwarded
    verbatim by ibis to ``pyodbc.connect`` and become connection-string attributes,
    so they use the ODBC spellings.
    """
    driver = _get_custom_property(server, "driver") or config.get_sqlserver_driver()

    # TRUSTED_CONNECTION predates the AUTHENTICATION variable, so it only fills in when no
    # mode was chosen. Letting it override instead would mean a leftover flag silently
    # downgrades a configured Entra ID login to Windows auth, with no error to explain it.
    authentication = config.get_sqlserver_authentication()
    trusted_connection = config.get_sqlserver_trusted_connection(default=False)
    if trusted_connection:
        logger.warning(
            "DATACONTRACT_SQLSERVER_TRUSTED_CONNECTION is deprecated and will be removed in a "
            "future release, use DATACONTRACT_SQLSERVER_AUTHENTICATION=windows instead."
        )
    if authentication is None:
        authentication = "windows" if trusted_connection else "sql"
    else:
        authentication = authentication.strip().lower()
        if trusted_connection and authentication != "windows":
            logger.warning(
                "DATACONTRACT_SQLSERVER_TRUSTED_CONNECTION is ignored because "
                "DATACONTRACT_SQLSERVER_AUTHENTICATION=%s is set.",
                authentication,
            )

    kwargs = dict(
        host=config.get_sqlserver_host() or server.host,
        port=config.get_sqlserver_port() or (int(server.port) if server.port else 1433),
        database=config.get_sqlserver_database() or server.database,
        driver=driver,
        user=None,
        password=None,
    )

    # ODBC Driver 18 encrypts and verifies the server certificate by default.
    kwargs["Encrypt"] = "yes" if config.get_sqlserver_encrypted_connection(default=True) else "no"
    if config.get_sqlserver_trust_server_certificate(default=False):
        kwargs["TrustServerCertificate"] = "yes"

    if authentication == "windows":
        kwargs["Trusted_Connection"] = "yes"
    elif authentication == "cli":
        # DefaultAzureCredential includes the Azure CLI session (requires ODBC
        # Driver 18.1+). Suppress ibis's no-credentials Trusted_Connection default.
        kwargs["Authentication"] = "ActiveDirectoryDefault"
        kwargs["Trusted_Connection"] = "no"
    elif authentication == "activedirectoryserviceprincipal":
        kwargs["Authentication"] = "ActiveDirectoryServicePrincipal"
        kwargs["user"] = config.get_sqlserver_client_id(required=True)
        kwargs["password"] = config.get_sqlserver_client_secret(required=True)
    elif authentication == "activedirectorypassword":
        kwargs["Authentication"] = "ActiveDirectoryPassword"
        kwargs["user"] = config.get_sqlserver_username(required=True)
        kwargs["password"] = config.get_sqlserver_password(required=True)
    elif authentication == "activedirectoryinteractive":
        kwargs["Authentication"] = "ActiveDirectoryInteractive"
        kwargs["Trusted_Connection"] = "no"
        username = config.get_sqlserver_username()
        if username:
            kwargs["user"] = username  # login hint; no password for the browser flow
    else:
        kwargs["user"] = config.get_sqlserver_username(required=True)
        kwargs["password"] = config.get_sqlserver_password(required=True)

    return kwargs


def _connect_athena(ibis, server: Server, config: Config):
    # regionName is a contract value, so the variable still wins over it
    credentials = aws_credentials.client_kwargs(aws_credentials.configured_region(server.regionName, config), config)
    schema = config.get_athena_schema() or server.schema_
    staging_dir = config.get_athena_staging_dir() or getattr(server, "stagingDir", None)
    catalog = config.get_athena_catalog() or server.catalog
    if not schema:
        raise DataContractException(
            type="athena-connection",
            name="missing_schema",
            reason="Schema is required for Athena connection.",
            engine="datacontract-cli",
        )
    if not staging_dir:
        raise DataContractException(
            type="athena-connection",
            name="missing_s3_staging_dir",
            reason="S3 staging directory is required for Athena connection.",
            engine="datacontract-cli",
        )
    kwargs = dict(
        s3_staging_dir=staging_dir,
        aws_access_key_id=credentials["aws_access_key_id"],
        aws_secret_access_key=credentials["aws_secret_access_key"],
        aws_session_token=credentials["aws_session_token"],
        region_name=credentials["region_name"],
        schema_name=schema,
    )
    # Optional data source / catalog; pyathena defaults it to `awsdatacatalog`.
    if catalog:
        kwargs["catalog_name"] = catalog
    return ibis.athena.connect(**kwargs)


def _connect_trino(ibis, server: Server, config: Config):
    authentication = (config.get_trino_authentication() or "basic").strip().lower()

    kwargs = dict(
        host=config.get_trino_host() or server.host,
        port=config.get_trino_port() or (int(server.port) if server.port else 8080),
        user=None,
        database=config.get_trino_catalog() or server.catalog,
        schema=config.get_trino_schema() or server.schema_,
    )

    if authentication == "basic":
        user = config.get_trino_username(required=True)
        kwargs["user"] = user

        password = config.get_trino_password()
        if password:
            import trino as trino_pkg

            kwargs["auth"] = trino_pkg.auth.BasicAuthentication(user, password)
            kwargs["http_scheme"] = "https"
        return ibis.trino.connect(**kwargs)
    elif authentication == "jwt":
        import trino as trino_pkg

        kwargs["auth"] = trino_pkg.auth.JWTAuthentication(config.get_trino_jwt_token(required=True))
        kwargs["http_scheme"] = "https"
        return ibis.trino.connect(**kwargs)
    elif authentication == "oauth2":
        import trino as trino_pkg

        kwargs["auth"] = trino_pkg.auth.OAuth2Authentication()
        kwargs["http_scheme"] = "https"
        return ibis.trino.connect(**kwargs)
    else:
        raise DataContractException(
            type="trino-connection",
            name="unsupported_authentication",
            reason=(
                "Unsupported DATACONTRACT_TRINO_AUTHENTICATION value "
                f"{authentication!r}. Supported values are: basic, jwt, oauth2."
            ),
            engine="datacontract-cli",
        )


def _get_custom_property(server: Server, name: str):
    if server.customProperties:
        for prop in server.customProperties:
            if prop.property == name:
                return prop.value
    return None


def _unsupported(run: Run, reason: str):
    run.checks.append(
        Check(
            type="general",
            name="Check that server type is supported",
            result=ResultEnum.warning,
            reason=reason,
            engine="datacontract-cli",
        )
    )
    run.log_warn(reason)
