import logging
import re
from typing import TYPE_CHECKING, Any, List, Optional

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty, Server

from datacontract.config import Config
from datacontract.engines.ibis.connections import aws_credentials
from datacontract.engines.ibis.connections.aws_credentials import resolve_aws_credentials
from datacontract.export.duckdb_type_converter import convert_to_duckdb_csv_type, convert_to_duckdb_json_type
from datacontract.export.sql_type_converter import convert_to_duckdb
from datacontract.model.run import Run

if TYPE_CHECKING:
    import duckdb

logger = logging.getLogger(__name__)


def _import_duckdb():
    try:
        import duckdb

        return duckdb
    except ImportError:
        raise ImportError("duckdb is required for this server type. Install with: pip install datacontract-cli[duckdb]")


def get_duckdb_connection(
    data_contract: OpenDataContractStandard,
    server: Server,
    run: Run,
    duckdb_connection: "duckdb.DuckDBPyConnection | None" = None,
    schema_name: str = "all",
    config: Config | None = None,
    untrusted_contract: bool = False,
) -> "duckdb.DuckDBPyConnection":
    duckdb = _import_duckdb()
    config = Config.resolve(config)
    own_connection = duckdb_connection is None
    if own_connection:
        con = duckdb.connect(database=":memory:")
    else:
        con = duckdb_connection

    path: str = ""
    if server.type == "local":
        path = server.path
    if server.type == "s3":
        path = server.location
        setup_s3_connection(con, server, config)
    if server.type == "gcs":
        path = server.location
        setup_gcs_connection(con, server, config)
    if server.type == "azure":
        path = server.location
        setup_azure_connection(con, server, config)

    if server.format == "delta":
        # Updating an extension reaches the network and the extension directory,
        # both of which the sandbox below takes away -- so do it first, and once
        # for the whole connection rather than once per model.
        con.sql("update extensions;")  # Make sure we have the latest delta extension

    model_paths = _model_paths(data_contract, path, schema_name)
    if untrusted_contract and own_connection:
        # After the extensions are loaded and the secrets created -- both need
        # access the sandbox takes away -- and before any contract-supplied SQL
        # can run. Not applied to a connection the caller handed us: that one is
        # theirs to configure.
        restrict_to_paths(con, model_paths)

    if data_contract.schema_:
        for schema_obj in data_contract.schema_:
            model_name = schema_obj.name
            if schema_name != "all" and model_name != schema_name:
                continue
            model_path = _model_path(path, model_name)
            run.log_info(f"Creating table {model_name} for {model_path}")

            if server.format == "json":
                json_format = "auto"
                if server.delimiter == "new_line":
                    json_format = "newline_delimited"
                elif server.delimiter == "array":
                    json_format = "array"
                columns = to_json_types(schema_obj)
                if columns is None:
                    con.sql(f"""
                            CREATE VIEW "{model_name}" AS SELECT * FROM read_json_auto('{model_path}', format='{json_format}', hive_partitioning=1);
                            """)
                else:
                    con.sql(
                        f"""CREATE VIEW "{model_name}" AS SELECT * FROM read_json_auto('{model_path}', format='{json_format}', columns={columns}, hive_partitioning=1);"""
                    )
                    add_nested_views(con, model_name, schema_obj.properties)
                # Raw view without the columns= projection to check for absent columns (check_property_is_present)
                con.sql(
                    f"""CREATE VIEW "{model_name}__raw__" AS SELECT * FROM read_json_auto('{model_path}', format='{json_format}', hive_partitioning=1);"""
                )
            elif server.format == "parquet":
                create_view_with_schema_union(con, schema_obj, model_path, "read_parquet", to_parquet_types)
            elif server.format == "csv":
                create_view_with_schema_union(con, schema_obj, model_path, "read_csv", to_csv_types)
            elif server.format == "delta":
                con.sql(f"""CREATE VIEW "{model_name}" AS SELECT * FROM delta_scan('{model_path}');""")
            table_info = con.sql(f'PRAGMA table_info("{model_name}");').fetchall()
            if table_info:
                run.log_info(f"DuckDB Table Info: {table_info}")
    return con


def _model_path(path: str, model_name: str) -> str:
    """The data location of one model: the server path with `{model}` filled in."""
    return path.format(model=model_name) if "{model}" in path else path


def _model_paths(data_contract: OpenDataContractStandard, path: str, schema_name: str) -> list[str]:
    """Every location this connection is going to read, one per model under test."""
    if not path or not data_contract.schema_:
        return []
    return [
        _model_path(path, schema_obj.name)
        for schema_obj in data_contract.schema_
        if schema_name == "all" or schema_obj.name == schema_name
    ]


# duckdb globs against the filesystem, so a location holding one of these has to be
# allowed as a directory prefix rather than as an exact file.
_GLOB_CHARACTERS = ("*", "?", "[")


def restrict_to_paths(con, paths: list[str]) -> None:
    """Confine the connection to `paths` and nothing else.

    A data contract carries SQL (`quality.type: sql`) that runs on this
    connection, and for a file server type that connection is duckdb -- which
    reads and writes the local filesystem. So the contract's own data locations
    are the only ones it may touch: `read_text('/etc/passwd')` and `COPY ... TO`
    alike are then refused by duckdb itself.

    `enable_external_access = false` is one-way -- duckdb refuses to re-enable it,
    and refuses to widen `allowed_paths`/`allowed_directories` once it is off --
    so the restriction holds without `lock_configuration`, which would also stop
    ibis from setting the session timezone.

    Must run after the extensions are loaded (installing one needs access this
    takes away) and before any contract-supplied SQL.
    """
    directories = sorted({_glob_root(p) for p in paths if _is_glob(p)})
    files = sorted({p for p in paths if not _is_glob(p)})
    if directories:
        con.sql(f"SET allowed_directories = {_sql_list(directories)}")
    if files:
        con.sql(f"SET allowed_paths = {_sql_list(files)}")
    con.sql("SET enable_external_access = false")


def _is_glob(path: str) -> bool:
    return any(character in path for character in _GLOB_CHARACTERS) or path.endswith("/")


def _glob_root(path: str) -> str:
    """The fixed prefix of a glob, which is the directory duckdb has to be allowed into."""
    cut = min((path.find(c) for c in _GLOB_CHARACTERS if c in path), default=len(path))
    root = path[:cut].rstrip("/")
    return root or "/"


def _sql_list(values: list[str]) -> str:
    return "[" + ", ".join(f"'{_sql_literal(value)}'" for value in values) + "]"


def create_view_with_schema_union(con, schema_obj: SchemaObject, model_path: str, read_function: str, type_converter):
    """Create a view by unioning empty schema table with data files using union_by_name"""
    converted_types = type_converter(schema_obj)
    model_name = schema_obj.name

    # Raw view to check for absent columns (check_property_is_present)
    con.sql(
        f"""CREATE VIEW "{model_name}__raw__" AS
            SELECT * FROM {read_function}('{model_path}', union_by_name=true, hive_partitioning=1);"""
    )

    if converted_types:
        # Create empty table with contract schema
        columns_def = [f'"{col_name}" {col_type}' for col_name, col_type in converted_types.items()]
        create_empty_table = f"""CREATE TABLE "{model_name}" ({", ".join(columns_def)});"""
        con.sql(create_empty_table)

        # Read columns existing in both current data contract and data
        intersecting_columns = con.sql(f"""SELECT column_name
            FROM (DESCRIBE SELECT * FROM {read_function}('{model_path}', union_by_name=true, hive_partitioning=1))
            INTERSECT SELECT column_name
            FROM information_schema.columns
            WHERE table_name = '{model_name}'""").fetchall()

        # Insert data into table by name, but only columns existing in contract and data
        if intersecting_columns:
            selected_columns = ", ".join(f'"{column[0]}"' for column in intersecting_columns)
            insert_data_sql = f"""INSERT INTO "{model_name}" BY NAME
                (SELECT {selected_columns} FROM {read_function}('{model_path}', union_by_name=true, hive_partitioning=1));"""
            con.sql(insert_data_sql)
    else:
        # Fallback
        con.sql(
            f"""CREATE VIEW "{model_name}" AS SELECT * FROM {read_function}('{model_path}', union_by_name=true, hive_partitioning=1);"""
        )


def to_csv_types(schema_obj: SchemaObject) -> dict[Any, str | None] | None:
    if schema_obj is None:
        return None
    columns = {}
    if schema_obj.properties:
        for prop in schema_obj.properties:
            columns[prop.physicalName or prop.name] = convert_to_duckdb_csv_type(prop)
    return columns


def to_parquet_types(schema_obj: SchemaObject) -> dict[Any, str | None] | None:
    """Get proper SQL types for Parquet (preserves decimals, etc.)"""
    if schema_obj is None:
        return None
    columns = {}
    if schema_obj.properties:
        for prop in schema_obj.properties:
            columns[prop.physicalName or prop.name] = convert_to_duckdb(prop)
    return columns


def to_json_types(schema_obj: SchemaObject) -> dict[Any, str | None] | None:
    if schema_obj is None:
        return None
    columns = {}
    if schema_obj.properties:
        for prop in schema_obj.properties:
            columns[prop.physicalName or prop.name] = convert_to_duckdb_json_type(prop)
    return columns


def _get_type(prop: SchemaProperty) -> Optional[str]:
    """Get the type from a schema property. Prefers physicalType for accurate type checking."""
    if prop.physicalType:
        return prop.physicalType
    if prop.logicalType:
        return prop.logicalType
    return None


def add_nested_views(con: "duckdb.DuckDBPyConnection", model_name: str, properties: List[SchemaProperty] | None):
    model_name = model_name.strip('"')
    if properties is None:
        return
    for prop in properties:
        prop_type = _get_type(prop)
        if prop_type is None or prop_type.lower() not in ["array", "object"]:
            continue
        field_type = prop_type.lower()
        if field_type == "array" and prop.items is None:
            continue
        elif field_type == "object" and (prop.properties is None or len(prop.properties) == 0):
            continue

        field_name = prop.physicalName or prop.name
        nested_model_name = f"{model_name}__{field_name}"
        max_depth = 2 if field_type == "array" else 1

        ## if parent field is not required, the nested objects may resolve
        ## to a row of NULLs -- but if the objects themselves have required
        ## fields, this will fail the check.
        where = "" if prop.required else f" WHERE {field_name} IS NOT NULL"
        con.sql(f"""
            CREATE VIEW IF NOT EXISTS "{nested_model_name}" AS
            SELECT unnest({field_name}, max_depth := {max_depth}) as {field_name} FROM "{model_name}" {where}
            """)
        if field_type == "array":
            add_nested_views(con, nested_model_name, prop.items.properties if prop.items else None)
        elif field_type == "object":
            add_nested_views(con, nested_model_name, prop.properties)


def _load_extension(con, name: str, extra: str) -> None:
    import gzip
    import importlib.resources
    import pathlib
    import shutil
    import tempfile

    # first try to use locally bundled wheel to support air-gapped environments
    try:
        ext_module = importlib.import_module(f"duckdb_extension_{name}")
        module_path = pathlib.Path(str(importlib.resources.files(ext_module)))
        duckdb_version = con.sql("PRAGMA version;").fetchone()[0]
        extension_file_gz = module_path / "extensions" / duckdb_version / f"{name}.duckdb_extension.gz"

        if extension_file_gz.exists():
            tmpdir = pathlib.Path(tempfile.mkdtemp(prefix=f"datacontract-{name}-"))
            extension_file = tmpdir / f"{name}.duckdb_extension"
            with gzip.open(extension_file_gz, "rb") as src, open(extension_file, "wb") as dst:
                shutil.copyfileobj(src, dst)
            con.sql(f"LOAD '{extension_file}'")
            return
    except ImportError:
        pass

    try:
        con.install_extension(name)
        con.load_extension(name)
    except Exception as e:
        raise RuntimeError(
            f"Failed to install the '{name}' DuckDB extension. "
            f"Please install the extension wheel via: pip install 'datacontract-cli[{extra}]'"
        ) from e


def _sql_literal(value) -> str:
    """Escape a value for a single-quoted duckdb string literal.

    Several of these come from the contract rather than the environment —
    `endpointUrl` and the storage account derived from `location` — and a
    contract can be a URL someone else published. A quote in one of those
    would otherwise end the literal and let the rest be parsed as SQL.
    """
    return str(value).replace("'", "''") if value is not None else ""


def setup_s3_connection(con, server: Server, config: Config | None = None):
    _load_extension(con, "httpfs", "s3")
    _load_extension(con, "aws", "s3")
    configured = aws_credentials.client_kwargs(config=config)
    s3_region = configured["region_name"]
    s3_access_key_id = configured["aws_access_key_id"]
    s3_secret_access_key = configured["aws_secret_access_key"]
    s3_session_token = configured["aws_session_token"]
    s3_endpoint = "s3.amazonaws.com"
    use_ssl = "true"
    url_style = "vhost"
    if server.endpointUrl is not None:
        url_style = "path"
        s3_endpoint = server.endpointUrl.removeprefix("http://").removeprefix("https://")
        if server.endpointUrl.startswith("http://"):
            use_ssl = "false"

    if s3_access_key_id is not None:
        if s3_session_token is not None:
            # No PROVIDER: defaults to `config`, which accepts the explicit
            # KEY_ID/SECRET below. (duckdb >=1.5 rejects CREDENTIAL_CHAIN
            # combined with explicit credentials.)
            con.sql(f"""
                CREATE OR REPLACE SECRET s3_secret (
                    TYPE S3,
                    REGION '{_sql_literal(s3_region)}',
                    KEY_ID '{_sql_literal(s3_access_key_id)}',
                    SECRET '{_sql_literal(s3_secret_access_key)}',
                    SESSION_TOKEN '{_sql_literal(s3_session_token)}',
                    ENDPOINT '{_sql_literal(s3_endpoint)}',
                    USE_SSL '{_sql_literal(use_ssl)}',
                    URL_STYLE '{_sql_literal(url_style)}'
                );
            """)
        else:
            con.sql(f"""
                CREATE OR REPLACE SECRET s3_secret (
                    TYPE S3,
                    REGION '{_sql_literal(s3_region)}',
                    KEY_ID '{_sql_literal(s3_access_key_id)}',
                    SECRET '{_sql_literal(s3_secret_access_key)}',
                    ENDPOINT '{_sql_literal(s3_endpoint)}',
                    USE_SSL '{_sql_literal(use_ssl)}',
                    URL_STYLE '{_sql_literal(url_style)}'
                );
            """)
    else:
        _create_s3_secret_from_aws_session(con, s3_region, s3_endpoint, use_ssl, url_style)


def _create_s3_secret_from_aws_session(con, region, endpoint, use_ssl, url_style):
    """Hand duckdb the credentials boto3 resolves, when no explicit key is set.

    duckdb's own ``PROVIDER credential_chain`` cannot read an SSO cache, so an
    ``aws sso login`` session that works for Athena and Redshift would otherwise
    fail here with a bare 403. Nothing resolvable leaves the connection without
    a secret, which is what public buckets need.
    """
    credentials = resolve_aws_credentials()
    if credentials is None:
        return

    region = region or credentials.region
    token_clause = f"SESSION_TOKEN '{credentials.session_token}'," if credentials.session_token else ""
    region_clause = f"REGION '{_sql_literal(region)}'," if region else ""
    con.sql(f"""
        CREATE OR REPLACE SECRET s3_secret (
            TYPE S3,
            {region_clause}
            KEY_ID '{credentials.access_key_id}',
            SECRET '{credentials.secret_access_key}',
            {token_clause}
            ENDPOINT '{_sql_literal(endpoint)}',
            USE_SSL '{_sql_literal(use_ssl)}',
            URL_STYLE '{_sql_literal(url_style)}'
        );
    """)


def setup_gcs_connection(con, server: Server, config: Config):
    _load_extension(con, "httpfs", "gcs")
    key_id = config.get_gcs_key_id(required=True)
    secret = config.get_gcs_secret(required=True)

    con.sql(f"""
    CREATE SECRET gcs_secret (
        TYPE GCS,
        KEY_ID '{_sql_literal(key_id)}',
        SECRET '{_sql_literal(secret)}'
    );
    """)


def setup_azure_connection(con, server: Server, config: Config):
    tenant_id = config.get_azure_tenant_id(required=True)
    client_id = config.get_azure_client_id(required=True)
    client_secret = config.get_azure_client_secret(required=True)
    storage_account = (
        to_azure_storage_account(server.location) if server.type == "azure" and "://" in server.location else None
    )

    _load_extension(con, "azure", "azure")

    if storage_account is not None:
        con.sql(f"""
        CREATE SECRET azure_spn (
            TYPE AZURE,
            PROVIDER SERVICE_PRINCIPAL,
            TENANT_ID '{_sql_literal(tenant_id)}',
            CLIENT_ID '{_sql_literal(client_id)}',
            CLIENT_SECRET '{_sql_literal(client_secret)}',
            ACCOUNT_NAME '{_sql_literal(storage_account)}'
        );
        """)
    else:
        con.sql(f"""
        CREATE SECRET azure_spn (
            TYPE AZURE,
            PROVIDER SERVICE_PRINCIPAL,
            TENANT_ID '{_sql_literal(tenant_id)}',
            CLIENT_ID '{_sql_literal(client_id)}',
            CLIENT_SECRET '{_sql_literal(client_secret)}'
        );
        """)


def to_azure_storage_account(location: str) -> str | None:
    """
    Converts a storage location string to extract the storage account name.
    ODCS v3.0 has no explicit field for the storage account. It uses the location field, which is a URI.
    This function parses a storage location string to identify and return the
    storage account name. It handles two primary patterns:
    1. Protocol://containerName@storageAccountName
    2. Protocol://storageAccountName
    :param location: The storage location string to parse, typically following
                     the format protocol://containerName@storageAccountName. or
                     protocol://storageAccountName.
    :return: The extracted storage account name if found, otherwise None
    """
    # to catch protocol://containerName@storageAccountName. pattern from location
    match = re.search(r"(?<=@)([^.]*)", location, re.IGNORECASE)
    if match:
        return match.group()
    else:
        # to catch protocol://storageAccountName. pattern from location
        match = re.search(r"(?<=//)(?!@)([^.]*)", location, re.IGNORECASE)
    return match.group() if match else None
