import logging
import os

import duckdb


def get_duckdb_connection(data_contract, server):
    con = duckdb.connect(database=":memory:")
    path: str = ""
    if server.type == "local":
        path = server.path
    if server.type == "s3":
        path = server.location
    setup_s3_connection(con, server)
    for model_name in data_contract.models:
        logging.info(f"Creating table {model_name} for {path}")
        if server.format == "json":
            format = "auto"
            if server.delimiter == "new_line":
                format = "newline_delimited"
            elif server.delimiter == "array":
                format = "array"
            con.sql(f"""
                        CREATE VIEW "{model_name}" AS SELECT * FROM read_json_auto('{path}', format='{format}', hive_partitioning=1);
                        """)
        elif server.format == "parquet":
            con.sql(f"""
                        CREATE VIEW "{model_name}" AS SELECT * FROM read_parquet('{path}', hive_partitioning=1);
                        """)
        elif server.format == "csv":
            con.sql(f"""
                        CREATE VIEW "{model_name}" AS SELECT * FROM read_csv_auto('{path}', hive_partitioning=1);
                        """)
    return con


def setup_s3_connection(con, server):
    s3_region = os.getenv('DATACONTRACT_S3_REGION')
    s3_access_key_id = os.getenv('DATACONTRACT_S3_ACCESS_KEY_ID')
    s3_secret_access_key = os.getenv('DATACONTRACT_S3_SECRET_ACCESS_KEY')
    con.install_extension("httpfs")
    con.load_extension("httpfs")
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
