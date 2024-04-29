import os

import duckdb
from datacontract.export.csv_type_converter import convert_to_duckdb_csv_type

from deltalake import DeltaTable

from datacontract.model.run import Run


def get_duckdb_connection(data_contract, server, run: Run):
    con = duckdb.connect(database=":memory:")
    path: str = ""
    if server.type == "local":
        path = server.path
    if server.type == "s3":
        path = server.location
        setup_s3_connection(con, server)
    if server.type == "azure":
        path = server.location
        setup_azure_connection(con, server)
    for model_name, model in data_contract.models.items():
        model_path = path
        if "{model}" in model_path:
            model_path = model_path.format(model=model_name)
        run.log_info(f"Creating table {model_name} for {model_path}")

        if server.format == "json":
            format = "auto"
            if server.delimiter == "new_line":
                format = "newline_delimited"
            elif server.delimiter == "array":
                format = "array"
            con.sql(f"""
                        CREATE VIEW "{model_name}" AS SELECT * FROM read_json_auto('{model_path}', format='{format}', hive_partitioning=1);
                        """)
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
            if server.type == "azure":
                raise NotImplementedError("Support for Delta Tables on Azure Storage is not implemented yet")

            storage_options = {
                "AWS_ENDPOINT_URL": server.endpointUrl,
                "AWS_ACCESS_KEY_ID": os.getenv("DATACONTRACT_S3_ACCESS_KEY_ID"),
                "AWS_SECRET_ACCESS_KEY": os.getenv("DATACONTRACT_S3_SECRET_ACCESS_KEY"),
                "AWS_REGION": os.getenv("DATACONTRACT_S3_REGION", "us-east-1"),
                "AWS_ALLOW_HTTP": "True" if server.endpointUrl.startswith("http://") else "False",
            }

            delta_table_arrow = DeltaTable(model_path, storage_options=storage_options).to_pyarrow_dataset()

            con.register(model_name, delta_table_arrow)
    return con


def to_csv_types(model) -> dict:
    if model is None:
        return None
    columns = {}
    # ['SQLNULL', 'BOOLEAN', 'BIGINT', 'DOUBLE', 'TIME', 'DATE', 'TIMESTAMP', 'VARCHAR']
    for field_name, field in model.fields.items():
        columns[field_name] = convert_to_duckdb_csv_type(field)
    return columns


def setup_s3_connection(con, server):
    s3_region = os.getenv("DATACONTRACT_S3_REGION")
    s3_access_key_id = os.getenv("DATACONTRACT_S3_ACCESS_KEY_ID")
    s3_secret_access_key = os.getenv("DATACONTRACT_S3_SECRET_ACCESS_KEY")
    # con.install_extension("httpfs")
    # con.load_extension("httpfs")
    if server.endpointUrl is not None:
        s3_endpoint = server.endpointUrl.removeprefix("http://").removeprefix("https://")
        if server.endpointUrl.startswith("http://"):
            con.sql("SET s3_use_ssl = 0; SET s3_url_style = 'path';")
        con.sql(f"""
                SET s3_endpoint = '{s3_endpoint}';
                """)
    if s3_access_key_id is not None:
        con.sql(f"""
                    SET s3_region = '{s3_region}';
                    SET s3_access_key_id = '{s3_access_key_id}';
                    SET s3_secret_access_key = '{s3_secret_access_key}';
                    """)


def setup_azure_connection(con, server):
    tenant_id = os.getenv("DATACONTRACT_AZURE_TENANT_ID")
    client_id = os.getenv("DATACONTRACT_AZURE_CLIENT_ID")
    client_secret = os.getenv("DATACONTRACT_AZURE_CLIENT_SECRET")

    if tenant_id is None:
        raise ValueError("Error: Environment variable DATACONTRACT_AZURE_TENANT_ID is not set")
    if client_id is None:
        raise ValueError("Error: Environment variable DATACONTRACT_AZURE_CLIENT_ID is not set")
    if client_secret is None:
        raise ValueError("Error: Environment variable DATACONTRACT_AZURE_CLIENT_SECRET is not set")

    con.install_extension("azure")
    con.load_extension("azure")

    con.sql(f"""
    CREATE SECRET azure_spn (
        TYPE AZURE,
        PROVIDER SERVICE_PRINCIPAL,
        TENANT_ID '{tenant_id}',
        CLIENT_ID '{client_id}',
        CLIENT_SECRET '{client_secret}'
    );
    """)
