import io
import os
import uuid

import duckdb

from datacontract.export.csv_type_converter import convert_to_duckdb_csv_type
from datacontract.model.run import Check, ResultEnum, Run


def get_duckdb_connection(data_contract, server, run: Run):
    con = duckdb.connect(database=":memory:")
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

            # Start with the required parameter.
            params = ["hive_partitioning=1"]

            # Define a mapping for CSV parameters: server attribute -> read_csv parameter name.
            param_mapping = {
                "delimiter": "delim",  # Map server.delimiter to 'delim'
                "header": "header",
                "escape": "escape",
                "allVarchar": "all_varchar",
                "allowQuotedNulls": "allow_quoted_nulls",
                "dateformat": "dateformat",
                "decimalSeparator": "decimal_separator",
                "newLine": "new_line",
                "timestampformat": "timestampformat",
                "quote": "quote",
            }
            for server_attr, read_csv_param in param_mapping.items():
                value = getattr(server, server_attr, None)
                if value is not None:
                    # Wrap string values in quotes.
                    if isinstance(value, str):
                        params.append(f"{read_csv_param}='{value}'")
                    else:
                        params.append(f"{read_csv_param}={value}")

            # Sniff out columns, if available:
            has_header = getattr(server, "header", True)
            if columns is not None and (has_header or has_header is None):
                csv_columns = sniff_csv_header(model_path, server)
                difference = set(csv_columns) - set(columns.keys())
                same_order = list(columns.keys()) == csv_columns[: len(columns)]
                if not same_order:
                    run.checks.append(
                        Check(
                            id=str(uuid.uuid4()),
                            model=model_name,
                            category="schema",
                            type="fields_are_same",
                            name="Column order mismatch",
                            result=ResultEnum.warning,
                            reason=f"Order of columns in {model_path} does not match the model.",
                            details=f"Expected: {'|'.join(columns.keys())}\nActual:   {'|'.join(csv_columns)}",
                            engine="datacontract",
                        )
                    )
                if len(difference) > 0:
                    run.checks.append(
                        Check(
                            id=str(uuid.uuid4()),
                            model=model_name,
                            category="schema",
                            type="fields_are_same",
                            name="Dataset contained unexpected fields",
                            result=ResultEnum.warning,
                            reason=f"{model_path} contained unexpected fields: {', '.join(difference)}",
                            engine="datacontract",
                        )
                    )
                columns = {k: columns.get(k, "VARCHAR") for k in csv_columns}

            # Add columns if they exist.
            if columns is not None:
                params.append(f"columns={columns}")

            # Build the parameter string.
            params_str = ", ".join(params)

            # Create the view with the assembled parameters.
            con.sql(f"""
                CREATE VIEW "{model_name}" AS
                SELECT * FROM read_csv('{model_path}', {params_str});
            """)

        elif server.format == "delta":
            con.sql("update extensions;")  # Make sure we have the latest delta extension
            con.sql(f"""CREATE VIEW "{model_name}" AS SELECT * FROM delta_scan('{model_path}');""")
    return con


def to_csv_types(model) -> dict:
    if model is None:
        return None
    columns = {}
    # ['SQLNULL', 'BOOLEAN', 'BIGINT', 'DOUBLE', 'TIME', 'DATE', 'TIMESTAMP', 'VARCHAR']
    for field_name, field in model.fields.items():
        columns[field_name] = convert_to_duckdb_csv_type(field)
    return columns


def sniff_csv_header(model_path, server):
    # Define a mapping for CSV parameters: server attribute -> duckdb.read_csv parameter name.
    # Note! The parameter names in the python calls (read_csv, read_csv_auto, and from_csv_auto)
    #       are different from those used in the SQL statements.
    param_mapping = {
        "delimiter": "delimiter",
        "header": "header",
        "escape": "escapechar",
        "decimal_separator": "decimal",
        "quote": "quotechar",
    }
    # Remainder params are left out, as we do not care about parsing datatype for just the header.
    with open(model_path, "rb") as model_file:
        header_line = model_file.readline()
    csv_params = {v: getattr(server, k) for (k, v) in param_mapping.items() if getattr(server, k, None) is not None}
    # from_csv_auto
    return duckdb.from_csv_auto(io.BytesIO(header_line), **csv_params).columns


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
