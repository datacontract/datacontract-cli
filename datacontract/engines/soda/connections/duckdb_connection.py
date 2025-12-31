import os
import re
from typing import Any, List, Optional

import duckdb
from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty, Server

from datacontract.export.duckdb_type_converter import convert_to_duckdb_csv_type, convert_to_duckdb_json_type
from datacontract.export.sql_type_converter import convert_to_duckdb
from datacontract.model.run import Run


def get_duckdb_connection(
    data_contract: OpenDataContractStandard,
    server: Server,
    run: Run,
    duckdb_connection: duckdb.DuckDBPyConnection | None = None,
) -> duckdb.DuckDBPyConnection:
    if duckdb_connection is None:
        con = duckdb.connect(database=":memory:")
    else:
        con = duckdb_connection

    path: str = ""
    if server.type == "local":
        path = server.path
    if server.type == "s3":
        path = server.location
        setup_s3_connection(con, server)
    if server.type == "gcs":
        path = server.location
        setup_gcs_connection(con, server)
    if server.type == "azure":
        path = server.location
        setup_azure_connection(con, server)

    if data_contract.schema_:
        for schema_obj in data_contract.schema_:
            model_name = schema_obj.name
            model_path = path
            if "{model}" in model_path:
                model_path = model_path.format(model=model_name)
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
            elif server.format == "parquet":
                create_view_with_schema_union(con, schema_obj, model_path, "read_parquet", to_parquet_types)
            elif server.format == "csv":
                create_view_with_schema_union(con, schema_obj, model_path, "read_csv", to_csv_types)
            elif server.format == "delta":
                con.sql("update extensions;")  # Make sure we have the latest delta extension
                con.sql(f"""CREATE VIEW "{model_name}" AS SELECT * FROM delta_scan('{model_path}');""")
            table_info = con.sql(f"PRAGMA table_info('{model_name}');").fetchdf()
            if table_info is not None and not table_info.empty:
                run.log_info(f"DuckDB Table Info: {table_info.to_string(index=False)}")
    return con


def create_view_with_schema_union(con, schema_obj: SchemaObject, model_path: str, read_function: str, type_converter):
    """Create a view by unioning empty schema table with data files using union_by_name"""
    converted_types = type_converter(schema_obj)
    model_name = schema_obj.name
    if converted_types:
        # Create empty table with contract schema
        columns_def = [f'"{col_name}" {col_type}' for col_name, col_type in converted_types.items()]
        create_empty_table = f"""CREATE TABLE "{model_name}_schema" ({', '.join(columns_def)});"""
        con.sql(create_empty_table)

        # Create view as UNION of empty schema table and data
        create_view_sql = f"""CREATE VIEW "{model_name}" AS
            SELECT * FROM "{model_name}_schema"
            UNION ALL BY NAME
            SELECT * FROM {read_function}('{model_path}', union_by_name=true, hive_partitioning=1);"""
        con.sql(create_view_sql)
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
            columns[prop.name] = convert_to_duckdb_csv_type(prop)
    return columns

def to_parquet_types(schema_obj: SchemaObject) -> dict[Any, str | None] | None:
    """Get proper SQL types for Parquet (preserves decimals, etc.)"""
    if schema_obj is None:
        return None
    columns = {}
    if schema_obj.properties:
        for prop in schema_obj.properties:
            columns[prop.name] = convert_to_duckdb(prop)
    return columns

def to_json_types(schema_obj: SchemaObject) -> dict[Any, str | None] | None:
    if schema_obj is None:
        return None
    columns = {}
    if schema_obj.properties:
        for prop in schema_obj.properties:
            columns[prop.name] = convert_to_duckdb_json_type(prop)
    return columns


def _get_type(prop: SchemaProperty) -> Optional[str]:
    """Get the type from a schema property. Prefers physicalType for accurate type checking."""
    if prop.physicalType:
        return prop.physicalType
    if prop.logicalType:
        return prop.logicalType
    return None


def add_nested_views(con: duckdb.DuckDBPyConnection, model_name: str, properties: List[SchemaProperty] | None):
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

        nested_model_name = f"{model_name}__{prop.name}"
        max_depth = 2 if field_type == "array" else 1

        ## if parent field is not required, the nested objects may resolve
        ## to a row of NULLs -- but if the objects themselves have required
        ## fields, this will fail the check.
        where = "" if prop.required else f" WHERE {prop.name} IS NOT NULL"
        con.sql(f"""
            CREATE VIEW IF NOT EXISTS "{nested_model_name}" AS
            SELECT unnest({prop.name}, max_depth := {max_depth}) as {prop.name} FROM "{model_name}" {where}
            """)
        if field_type == "array":
            add_nested_views(con, nested_model_name, prop.items.properties if prop.items else None)
        elif field_type == "object":
            add_nested_views(con, nested_model_name, prop.properties)


def setup_s3_connection(con, server: Server):
    s3_region = os.getenv("DATACONTRACT_S3_REGION")
    s3_access_key_id = os.getenv("DATACONTRACT_S3_ACCESS_KEY_ID")
    s3_secret_access_key = os.getenv("DATACONTRACT_S3_SECRET_ACCESS_KEY")
    s3_session_token = os.getenv("DATACONTRACT_S3_SESSION_TOKEN")
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
            con.sql(f"""
                CREATE OR REPLACE SECRET s3_secret (
                    TYPE S3,
                    PROVIDER CREDENTIAL_CHAIN,
                    REGION '{s3_region}',
                    KEY_ID '{s3_access_key_id}',
                    SECRET '{s3_secret_access_key}',
                    SESSION_TOKEN '{s3_session_token}',
                    ENDPOINT '{s3_endpoint}',
                    USE_SSL '{use_ssl}',
                    URL_STYLE '{url_style}'
                );
            """)
        else:
            con.sql(f"""
                CREATE OR REPLACE SECRET s3_secret (
                    TYPE S3,
                    PROVIDER CREDENTIAL_CHAIN,
                    REGION '{s3_region}',
                    KEY_ID '{s3_access_key_id}',
                    SECRET '{s3_secret_access_key}',
                    ENDPOINT '{s3_endpoint}',
                    USE_SSL '{use_ssl}',
                    URL_STYLE '{url_style}'
                );
            """)


def setup_gcs_connection(con, server: Server):
    key_id = os.getenv("DATACONTRACT_GCS_KEY_ID")
    secret = os.getenv("DATACONTRACT_GCS_SECRET")

    if key_id is None:
        raise ValueError("Error: Environment variable DATACONTRACT_GCS_KEY_ID is not set")
    if secret is None:
        raise ValueError("Error: Environment variable DATACONTRACT_GCS_SECRET is not set")

    con.sql(f"""
    CREATE SECRET gcs_secret (
        TYPE GCS,
        KEY_ID '{key_id}',
        SECRET '{secret}'
    );
    """)


def setup_azure_connection(con, server: Server):
    tenant_id = os.getenv("DATACONTRACT_AZURE_TENANT_ID")
    client_id = os.getenv("DATACONTRACT_AZURE_CLIENT_ID")
    client_secret = os.getenv("DATACONTRACT_AZURE_CLIENT_SECRET")
    storage_account = (
        to_azure_storage_account(server.location) if server.type == "azure" and "://" in server.location
            else None
        )

    if tenant_id is None:
        raise ValueError("Error: Environment variable DATACONTRACT_AZURE_TENANT_ID is not set")
    if client_id is None:
        raise ValueError("Error: Environment variable DATACONTRACT_AZURE_CLIENT_ID is not set")
    if client_secret is None:
        raise ValueError("Error: Environment variable DATACONTRACT_AZURE_CLIENT_SECRET is not set")

    con.install_extension("azure")
    con.load_extension("azure")

    if storage_account is not None:
        con.sql(f"""
        CREATE SECRET azure_spn (
            TYPE AZURE,
            PROVIDER SERVICE_PRINCIPAL,
            TENANT_ID '{tenant_id}',
            CLIENT_ID '{client_id}',
            CLIENT_SECRET '{client_secret}',
            ACCOUNT_NAME '{storage_account}'
        );
        """)
    else:
        con.sql(f"""
        CREATE SECRET azure_spn (
            TYPE AZURE,
            PROVIDER SERVICE_PRINCIPAL,
            TENANT_ID '{tenant_id}',
            CLIENT_ID '{client_id}',
            CLIENT_SECRET '{client_secret}'
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
