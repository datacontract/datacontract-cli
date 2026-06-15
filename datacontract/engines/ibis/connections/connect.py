"""Build an ibis backend connection for an ODCS server.

Replaces the per-source soda configuration builders. Each branch maps the
``Server`` fields and the same ``DATACONTRACT_*`` environment variables the soda
connections used onto an ``ibis.<backend>.connect(...)`` call. File sources
reuse the DuckDB view builder (``duckdb_connection.py``) and Spark sources reuse
the Spark/Kafka helpers (``kafka.py``), wrapping the resulting connection/session
with the ibis duckdb / pyspark backend.
"""

from __future__ import annotations

import logging
import os
import typing

from open_data_contract_standard.model import OpenDataContractStandard, Server

from datacontract.engines.ibis.connections.duckdb_connection import get_duckdb_connection
from datacontract.model.exceptions import DataContractException, require_env
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
) -> "ibis.BaseBackend | None":
    """Return a connected ibis backend, or ``None`` if the server is unsupported.

    On an unsupported server type/format an explanatory warning ``Check`` is
    appended to ``run`` (mirroring the previous soda behaviour).
    """
    ibis = _import_ibis()
    server_type = get_server_type(server)

    if server_type in _FILE_SERVER_TYPES:
        if server.format not in _SUPPORTED_FILE_FORMATS:
            _unsupported(run, f"Format {server.format} not yet supported by datacontract CLI")
            return None
        run.log_info(f"Connecting to {server_type} {server.format} via duckdb")
        con = get_duckdb_connection(data_contract, server, run, duckdb_connection, schema_name=schema_name)
        return ibis.duckdb.from_connection(con)

    if server_type == "kafka":
        from datacontract.engines.ibis.connections.kafka import create_spark_session, read_kafka_topic

        if spark is None:
            spark = create_spark_session()
        read_kafka_topic(spark, data_contract, server)
        return ibis.pyspark.connect(session=spark)

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
        return _connect_databricks(ibis, server, run)

    if server_type == "postgres":
        return ibis.postgres.connect(
            host=server.host,
            port=int(server.port) if server.port else 5432,
            user=require_env("DATACONTRACT_POSTGRES_USERNAME", server_type="postgres"),
            password=require_env("DATACONTRACT_POSTGRES_PASSWORD", server_type="postgres"),
            database=server.database,
            schema=server.schema_,
        )

    if server_type == "redshift":
        kwargs = dict(
            host=server.host,
            port=int(server.port) if server.port else 5439,
            user=require_env("DATACONTRACT_REDSHIFT_USERNAME", server_type="redshift"),
            database=server.database,
            schema=server.schema_,
        )
        password = os.getenv("DATACONTRACT_REDSHIFT_PASSWORD")
        if password:
            kwargs["password"] = password
        # Redshift speaks the postgres wire protocol; ibis has no dedicated backend.
        return ibis.postgres.connect(**kwargs)

    if server_type == "mysql":
        return _connect_mysql_via_duckdb(ibis, data_contract, server, run, schema_name)

    if server_type == "snowflake":
        prefix = "DATACONTRACT_SNOWFLAKE_"
        extra = {k.replace(prefix, "").lower(): v for k, v in os.environ.items() if k.startswith(prefix)}
        # ibis passes kwargs straight to snowflake-connector-python, which uses
        # `user` (not soda's `username`). Keep DATACONTRACT_SNOWFLAKE_USERNAME working.
        if "username" in extra:
            extra.setdefault("user", extra.pop("username"))
        # ibis tries to CREATE DATABASE for helper UDFs on connect (create_object_udfs=True).
        # datacontract only reads, and the read-only roles used for testing lack CREATE DATABASE,
        # so this otherwise emits a noisy "Insufficient privileges" warning. Default it off, but
        # let users opt back in via DATACONTRACT_SNOWFLAKE_CREATE_OBJECT_UDFS=true (env values are
        # strings, so coerce it; an unset/blank/non-"true" value keeps UDF creation disabled).
        create_object_udfs = str(extra.pop("create_object_udfs", "")).strip().lower() == "true"
        return ibis.snowflake.connect(
            create_object_udfs=create_object_udfs,
            account=server.account,
            database=server.database,
            schema=server.schema_,
            **extra,
        )

    if server_type == "bigquery":
        kwargs = dict(project_id=server.project, dataset_id=server.dataset)
        credentials_path = os.getenv("DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH")
        if credentials_path:
            from google.oauth2 import service_account

            kwargs["credentials"] = service_account.Credentials.from_service_account_file(credentials_path)
        return ibis.bigquery.connect(**kwargs)

    if server_type == "sqlserver":
        return _connect_sqlserver(ibis, server)

    if server_type == "oracle":
        service_name = server.serviceName or server.database
        oracle_client_dir = os.getenv("DATACONTRACT_ORACLE_CLIENT_DIR")
        if oracle_client_dir:
            import oracledb

            oracledb.init_oracle_client(lib_dir=oracle_client_dir)
        return ibis.oracle.connect(
            host=server.host,
            port=int(server.port) if server.port else 1521,
            user=require_env("DATACONTRACT_ORACLE_USERNAME", server_type="oracle"),
            password=require_env("DATACONTRACT_ORACLE_PASSWORD", server_type="oracle"),
            service_name=service_name,
        )

    if server_type == "trino":
        user = require_env("DATACONTRACT_TRINO_USERNAME", server_type="trino")
        password = os.getenv("DATACONTRACT_TRINO_PASSWORD")
        kwargs = dict(
            host=server.host,
            port=int(server.port) if server.port else 8080,
            user=user,
            database=server.catalog,
            schema=server.schema_,
        )
        if password:
            import trino as trino_pkg

            kwargs["auth"] = trino_pkg.auth.BasicAuthentication(user, password)
            kwargs["http_scheme"] = "https"
        return ibis.trino.connect(**kwargs)

    if server_type == "athena":
        return _connect_athena(ibis, server)

    if server_type == "impala":
        return ibis.impala.connect(
            host=server.host,
            port=int(server.port) if server.port else 21050,
            user=os.getenv("DATACONTRACT_IMPALA_USERNAME"),
            password=os.getenv("DATACONTRACT_IMPALA_PASSWORD"),
            database=getattr(server, "database", None),
            use_ssl=_get_bool_env("DATACONTRACT_IMPALA_USE_SSL", True),
        )

    _unsupported(run, f"Server type {server_type} not yet supported by datacontract CLI")
    return None


def _connect_databricks(ibis, server: Server, run: Run):
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
    host = server.host or require_env("DATACONTRACT_DATABRICKS_SERVER_HOSTNAME", server_type="databricks")
    kwargs = dict(
        server_hostname=host,
        http_path=os.getenv("DATACONTRACT_DATABRICKS_HTTP_PATH"),
        catalog=server.catalog,
        schema=server.schema_,
    )

    token = os.getenv("DATACONTRACT_DATABRICKS_TOKEN")
    client_id = os.getenv("DATACONTRACT_DATABRICKS_CLIENT_ID")
    client_secret = os.getenv("DATACONTRACT_DATABRICKS_CLIENT_SECRET")
    profile = os.getenv("DATACONTRACT_DATABRICKS_PROFILE")
    auth_type = os.getenv("DATACONTRACT_DATABRICKS_AUTH_TYPE")

    if token:
        run.log_info("Connecting to databricks with a personal access token")
        return ibis.databricks.connect(access_token=token, **kwargs)

    if client_id and client_secret:
        run.log_info("Connecting to databricks with an OAuth service principal (M2M)")
        sdk_host = host if host.startswith("http") else f"https://{host}"
        kwargs["credentials_provider"] = _databricks_credentials_provider(
            host=sdk_host, client_id=client_id, client_secret=client_secret
        )
        return ibis.databricks.connect(**kwargs)

    if profile:
        run.log_info(f"Connecting to databricks with config profile '{profile}'")
        kwargs["credentials_provider"] = _databricks_credentials_provider(profile=profile)
        return ibis.databricks.connect(**kwargs)

    if auth_type:
        run.log_info(f"Connecting to databricks with auth_type '{auth_type}'")
        return ibis.databricks.connect(auth_type=auth_type, **kwargs)

    # Nothing configured: fail with the same clear message as before.
    token = require_env("DATACONTRACT_DATABRICKS_TOKEN", server_type="databricks")
    return ibis.databricks.connect(access_token=token, **kwargs)


def _databricks_credentials_provider(**config_kwargs):
    """Return a ``credentials_provider`` callable for the Databricks SQL connector.

    The connector expects a zero-arg callable returning a header factory. We
    build the SDK ``Config`` lazily inside that callable so authentication (and
    any OAuth token exchange) happens at connect time, with credential resolution
    delegated to the Databricks SDK's unified auth.
    """

    def credentials_provider():
        from databricks.sdk.core import Config

        return Config(**config_kwargs).authenticate

    return credentials_provider


def _connect_mysql_via_duckdb(ibis, data_contract, server: Server, run: Run, schema_name: str):
    """Connect to MySQL through DuckDB's ``mysql`` extension.

    ibis's native MySQL backend requires ``mysqlclient`` (a C extension with no
    macOS/Linux wheels, needing system MySQL client libraries to build). Routing
    through DuckDB keeps the install pure-pip: DuckDB ATTACHes the MySQL database
    and we expose each contract model as a view in the default catalog so the
    rest of the engine works unchanged.
    """
    import duckdb

    from datacontract.engines.ibis.connections.duckdb_connection import _load_extension

    user = require_env("DATACONTRACT_MYSQL_USERNAME", server_type="mysql")
    password = require_env("DATACONTRACT_MYSQL_PASSWORD", server_type="mysql")
    host = server.host or "localhost"
    port = int(server.port) if server.port else 3306
    database = server.database

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


def _connect_sqlserver(ibis, server: Server):
    return ibis.mssql.connect(**_sqlserver_connection_kwargs(server))


def _sqlserver_connection_kwargs(server: Server) -> dict:
    """Build the ``ibis.mssql.connect`` kwargs, selecting the auth mode from env vars.

    ``DATACONTRACT_SQLSERVER_AUTHENTICATION`` picks the mode (default ``sql``):

    - ``sql`` — SQL Server auth with ``USERNAME`` / ``PASSWORD``
    - ``windows`` — Windows integrated auth (Kerberos/NTLM), no credentials
    - ``ActiveDirectoryPassword`` — Entra ID with ``USERNAME`` / ``PASSWORD``
    - ``ActiveDirectoryServicePrincipal`` — Entra ID with ``CLIENT_ID`` / ``CLIENT_SECRET``
    - ``ActiveDirectoryInteractive`` — Entra ID browser login (``USERNAME`` as a hint)
    - ``cli`` — reuse an ``az login`` session via the Azure default credential chain

    The legacy ``DATACONTRACT_SQLSERVER_TRUSTED_CONNECTION=true`` is equivalent to
    ``windows`` and takes precedence. Extra keys (``Authentication``,
    ``Trusted_Connection``, ``Encrypt``, ``TrustServerCertificate``) are forwarded
    verbatim by ibis to ``pyodbc.connect`` and become connection-string attributes,
    so they use the ODBC spellings.
    """
    driver = _get_custom_property(server, "driver") or os.getenv("DATACONTRACT_SQLSERVER_DRIVER")

    authentication = os.getenv("DATACONTRACT_SQLSERVER_AUTHENTICATION", "sql").lower()
    if _get_bool_env("DATACONTRACT_SQLSERVER_TRUSTED_CONNECTION", False):
        authentication = "windows"

    kwargs = dict(
        host=server.host,
        port=int(server.port) if server.port else 1433,
        database=server.database,
        driver=driver,
        user=None,
        password=None,
    )

    # ODBC Driver 18 encrypts and verifies the server certificate by default.
    kwargs["Encrypt"] = "yes" if _get_bool_env("DATACONTRACT_SQLSERVER_ENCRYPTED_CONNECTION", True) else "no"
    if _get_bool_env("DATACONTRACT_SQLSERVER_TRUST_SERVER_CERTIFICATE", False):
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
        kwargs["user"] = require_env("DATACONTRACT_SQLSERVER_CLIENT_ID", server_type="sqlserver")
        kwargs["password"] = require_env("DATACONTRACT_SQLSERVER_CLIENT_SECRET", server_type="sqlserver")
    elif authentication == "activedirectorypassword":
        kwargs["Authentication"] = "ActiveDirectoryPassword"
        kwargs["user"] = require_env("DATACONTRACT_SQLSERVER_USERNAME", server_type="sqlserver")
        kwargs["password"] = require_env("DATACONTRACT_SQLSERVER_PASSWORD", server_type="sqlserver")
    elif authentication == "activedirectoryinteractive":
        kwargs["Authentication"] = "ActiveDirectoryInteractive"
        kwargs["Trusted_Connection"] = "no"
        username = os.getenv("DATACONTRACT_SQLSERVER_USERNAME")
        if username:
            kwargs["user"] = username  # login hint; no password for the browser flow
    else:
        kwargs["user"] = require_env("DATACONTRACT_SQLSERVER_USERNAME", server_type="sqlserver")
        kwargs["password"] = require_env("DATACONTRACT_SQLSERVER_PASSWORD", server_type="sqlserver")

    return kwargs


def _connect_athena(ibis, server: Server):
    s3_access_key_id = os.getenv("DATACONTRACT_S3_ACCESS_KEY_ID")
    s3_secret_access_key = os.getenv("DATACONTRACT_S3_SECRET_ACCESS_KEY")
    if not server.schema_:
        raise DataContractException(
            type="athena-connection",
            name="missing_schema",
            reason="Schema is required for Athena connection.",
            engine="datacontract",
        )
    if not getattr(server, "stagingDir", None):
        raise DataContractException(
            type="athena-connection",
            name="missing_s3_staging_dir",
            reason="S3 staging directory is required for Athena connection.",
            engine="datacontract",
        )
    return ibis.athena.connect(
        s3_staging_dir=server.stagingDir,
        aws_access_key_id=s3_access_key_id,
        aws_secret_access_key=s3_secret_access_key,
        region_name=os.getenv("DATACONTRACT_S3_REGION") or getattr(server, "region_name", None),
        schema_name=server.schema_,
    )


def _get_custom_property(server: Server, name: str):
    if server.customProperties:
        for prop in server.customProperties:
            if prop.property == name:
                return prop.value
    return None


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "y", "on")


def _unsupported(run: Run, reason: str):
    run.checks.append(
        Check(
            type="general",
            name="Check that server type is supported",
            result=ResultEnum.warning,
            reason=reason,
            engine="datacontract",
        )
    )
    run.log_warn(reason)
