import os
from typing import Any, Dict

import duckdb

from datacontract.export.duckdb_type_converter import convert_to_duckdb_csv_type, convert_to_duckdb_json_type
from datacontract.model.data_contract_specification import DataContractSpecification, Field, Model, Server
from datacontract.model.run import Run


def get_duckdb_connection(
    data_contract: DataContractSpecification,
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
    for model_name, model in data_contract.models.items():
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
            columns = to_json_types(model)
            if columns is None:
                con.sql(f"""
                        CREATE VIEW "{model_name}" AS SELECT * FROM read_json_auto('{model_path}', format='{json_format}', hive_partitioning=1);
                        """)
            else:
                con.sql(
                    f"""CREATE VIEW "{model_name}" AS SELECT * FROM read_json_auto('{model_path}', format='{json_format}', columns={columns}, hive_partitioning=1);"""
                )
                add_nested_views(con, model_name, model.fields)
        elif server.format == "parquet":
            con.sql(f"""
                        CREATE VIEW "{model_name}" AS SELECT * FROM read_parquet('{model_path}', hive_partitioning=1);
                        """)
        elif server.format == "csv":
            columns = to_csv_types(model)
            run.log_info("Using columns: " + str(columns))
            if columns is None:
                con.sql(
                    f"""CREATE VIEW "{model_name}" AS SELECT * FROM read_csv('{model_path}', hive_partitioning=1);"""
                )
            else:
                con.sql(
                    f"""CREATE VIEW "{model_name}" AS SELECT * FROM read_csv('{model_path}', hive_partitioning=1, columns={columns});"""
                )
        elif server.format == "delta":
            con.sql("update extensions;")  # Make sure we have the latest delta extension
            con.sql(f"""CREATE VIEW "{model_name}" AS SELECT * FROM delta_scan('{model_path}');""")
    return con


def to_csv_types(model) -> dict[Any, str | None] | None:
    if model is None:
        return None
    columns = {}
    # ['SQLNULL', 'BOOLEAN', 'BIGINT', 'DOUBLE', 'TIME', 'DATE', 'TIMESTAMP', 'VARCHAR']
    for field_name, field in model.fields.items():
        columns[field_name] = convert_to_duckdb_csv_type(field)
    return columns


def to_json_types(model: Model) -> dict[Any, str | None] | None:
    if model is None:
        return None
    columns = {}
    for field_name, field in model.fields.items():
        columns[field_name] = convert_to_duckdb_json_type(field)
    return columns


def add_nested_views(con: duckdb.DuckDBPyConnection, model_name: str, fields: Dict[str, Field] | None):
    model_name = model_name.strip('"')
    if fields is None:
        return
    for field_name, field in fields.items():
        if field.type is None or field.type.lower() not in ["array", "object"]:
            continue
        field_type = field.type.lower()
        if field_type == "array" and field.items is None:
            continue
        elif field_type == "object" and field.fields is None:
            continue

        nested_model_name = f"{model_name}__{field_name}"
        max_depth = 2 if field_type == "array" else 1

        ## if parent field is not required, the nested objects may respolve
        ## to a row of NULLs -- but if the objects themselves have required
        ## fields, this will fail the check.
        where = "" if field.required else f" WHERE {field_name} IS NOT NULL"
        con.sql(f"""
            CREATE VIEW IF NOT EXISTS "{nested_model_name}" AS
            SELECT unnest({field_name}, max_depth := {max_depth}) as {field_name} FROM "{model_name}" {where}
            """)
        if field_type == "array":
            add_nested_views(con, nested_model_name, field.items.fields)
        elif field_type == "object":
            add_nested_views(con, nested_model_name, field.fields)


def setup_s3_connection(con, server):
    s3_region = os.getenv("DATACONTRACT_S3_REGION")
    s3_access_key_id = os.getenv("DATACONTRACT_S3_ACCESS_KEY_ID")
    s3_secret_access_key = os.getenv("DATACONTRACT_S3_SECRET_ACCESS_KEY")
    s3_session_token = os.getenv("DATACONTRACT_S3_SESSION_TOKEN")
    s3_endpoint = "s3.amazonaws.com"
    use_ssl = "true"
    url_style = "vhost"
    if server.endpointUrl is not None:
        s3_endpoint = server.endpointUrl.removeprefix("http://").removeprefix("https://")
        if server.endpointUrl.startswith("http://"):
            use_ssl = "false"
            url_style = "path"

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

    #     con.sql(f"""
    #                 SET s3_region = '{s3_region}';
    #                 SET s3_access_key_id = '{s3_access_key_id}';
    #                 SET s3_secret_access_key = '{s3_secret_access_key}';
    #                 """)
    # else:
    #     con.sql("""
    #                 RESET s3_region;
    #                 RESET s3_access_key_id;
    #                 RESET s3_secret_access_key;
    #     """)
    # con.sql("RESET s3_session_token")
    # print(con.sql("SELECT * FROM duckdb_settings() WHERE name like 's3%'"))


def setup_gcs_connection(con, server):
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


def setup_azure_connection(con, server):
    tenant_id = os.getenv("DATACONTRACT_AZURE_TENANT_ID")
    client_id = os.getenv("DATACONTRACT_AZURE_CLIENT_ID")
    client_secret = os.getenv("DATACONTRACT_AZURE_CLIENT_SECRET")
    storage_account = server.storageAccount

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
