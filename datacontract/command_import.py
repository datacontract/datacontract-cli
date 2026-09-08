from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from datacontract.cli import OrderedCommandsWithMigrationHints, debug_option, enable_debug_logging
from datacontract.config import cli_config
from datacontract.data_contract import DataContract
from datacontract.imports.sql_importer import SqlDialect

console = Console()

import_app = typer.Typer(cls=OrderedCommandsWithMigrationHints, no_args_is_help=True)

# ---------------------------------------------------------------------------
# Shared option type aliases
# ---------------------------------------------------------------------------
output_option = Annotated[
    Optional[Path],
    typer.Option(
        help="File path where the Data Contract will be saved. If not provided, it will be printed to stdout."
    ),
]
database_option = Annotated[
    Optional[str],
    typer.Option("--database", help="The database name."),
]
schema_option = Annotated[
    Optional[str],
    typer.Option("--json-schema", help="The location (url or path) of the ODCS JSON Schema"),
]
owner_option = Annotated[
    Optional[str], typer.Option(help="The owner or team responsible for managing the data contract.")
]
id_option = Annotated[Optional[str], typer.Option(help="The identifier for the data contract.")]


def _write_result(result, output: Optional[Path]):
    if output is None:
        console.print(result.to_yaml(), markup=False, soft_wrap=True)
    else:
        with output.open(mode="w", encoding="utf-8") as f:
            f.write(result.to_yaml())
        console.print(f"Written result to {output}")


# ---------------------------------------------------------------------------
# Import subcommands
# ---------------------------------------------------------------------------


@import_app.command(
    name="sql",
    epilog="Example: datacontract import sql --source ddl.sql --dialect postgres --output datacontract.yaml",
)
def import_sql(
    source: Annotated[Optional[str], typer.Option(help="Path to the SQL DDL file.")] = None,
    dialect: Annotated[
        Optional[SqlDialect],
        typer.Option(help="The SQL dialect."),
    ] = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a SQL DDL file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(),
        format="sql",
        source=source,
        schema=schema,
        dialect=dialect.value if dialect is not None else None,
        owner=owner,
        id=id,
    )
    _write_result(result, output)


@import_app.command(
    name="avro",
    epilog="Example: datacontract import avro --source schema.avsc --output datacontract.yaml",
)
def import_avro(
    source: Annotated[Optional[str], typer.Option(help="Path to the Avro schema file.")] = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from an Avro schema file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(), format="avro", source=source, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(
    name="dbt",
    epilog="Example: datacontract import dbt --source manifest.json --output datacontract.yaml",
)
def import_dbt(
    source: Annotated[Optional[str], typer.Option(help="Path to the dbt manifest.json file.")] = None,
    model: Annotated[
        Optional[List[str]],
        typer.Option(
            help="List of models names to import from the dbt manifest file (repeat for multiple models names, leave empty for all models in the dataset)."
        ),
    ] = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a dbt manifest file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(), format="dbt", source=source, schema=schema, dbt_model=model, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(
    name="dbml",
    epilog="Example: datacontract import dbml --source schema.dbml --output datacontract.yaml",
)
def import_dbml(
    source: Annotated[Optional[str], typer.Option(help="Path to the DBML file.")] = None,
    schema: Annotated[
        Optional[List[str]],
        typer.Option(
            "--dbml-schema",
            help="List of schema names to import from the DBML file (repeat for multiple schema names, leave empty for all tables in the file).",
        ),
    ] = None,
    table: Annotated[
        Optional[List[str]],
        typer.Option(
            "--dbml-table",
            help="List of table names to import from the DBML file (repeat for multiple table names, leave empty for all tables in the file).",
        ),
    ] = None,
    output: output_option = None,
    odcs_schema: Annotated[
        Optional[str], typer.Option("--json-schema", help="The location (url or path) of the ODCS JSON Schema")
    ] = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a DBML file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(),
        format="dbml",
        source=source,
        schema=odcs_schema,
        dbml_schema=schema,
        dbml_table=table,
        owner=owner,
        id=id,
    )
    _write_result(result, output)


@import_app.command(
    name="glue",
    epilog="Example: datacontract import glue --database my_database --table orders --output datacontract.yaml",
)
def import_glue(
    database: Annotated[Optional[str], typer.Option(help="Name of the AWS Glue database.")] = None,
    table: Annotated[
        Optional[List[str]],
        typer.Option(
            help="List of table ids to import from the Glue Database (repeat for multiple table ids, leave empty for all tables in the dataset)."
        ),
    ] = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from AWS Glue."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(), format="glue", source=database, schema=schema, glue_table=table, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(
    name="bigquery",
    epilog="Example: datacontract import bigquery --project my-project --dataset my_dataset --output datacontract.yaml",
)
def import_bigquery(
    source: Annotated[
        Optional[str],
        typer.Option(
            help="Path to a BigQuery schema JSON file. If omitted, imports from the BigQuery API using --project/--dataset/--table."
        ),
    ] = None,
    project: Annotated[Optional[str], typer.Option(help="The BigQuery project id.")] = None,
    dataset: Annotated[Optional[str], typer.Option(help="The BigQuery dataset id.")] = None,
    table: Annotated[
        Optional[List[str]],
        typer.Option(
            help="List of table ids to import from the BigQuery API (repeat for multiple table ids, leave empty for all tables in the dataset)."
        ),
    ] = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from BigQuery."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(),
        format="bigquery",
        source=source,
        schema=schema,
        bigquery_project=project,
        bigquery_dataset=dataset,
        bigquery_table=table,
        owner=owner,
        id=id,
    )
    _write_result(result, output)


databricks_source_option = Annotated[
    Optional[str],
    typer.Option(
        help="Path to a Unity Catalog TableInfo JSON file. If omitted, imports from the Unity API using --table."
    ),
]
databricks_table_option = Annotated[
    Optional[List[str]],
    typer.Option(help="Full name of a table in the Unity Catalog (repeat for multiple tables)."),
]


@import_app.command(
    name="databricks",
    epilog="Example: datacontract import databricks --table catalog.schema.my_table --output datacontract.yaml",
)
def import_databricks(
    source: databricks_source_option = None,
    table: databricks_table_option = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from Databricks Unity Catalog."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(),
        format="databricks",
        source=source,
        schema=schema,
        unity_table_full_name=table,
        owner=owner,
        id=id,
    )
    _write_result(result, output)


# `unity` predates the `databricks` name and stays working; hidden so the help
# lists one name for one importer.
@import_app.command(
    name="unity",
    hidden=True,
    epilog="Example: datacontract import databricks --table catalog.schema.my_table --output datacontract.yaml",
)
def import_unity(
    source: databricks_source_option = None,
    table: databricks_table_option = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from Databricks Unity Catalog (alias of `import databricks`)."""
    import_databricks(source=source, table=table, output=output, schema=schema, owner=owner, id=id, debug=debug)


@import_app.command(
    name="jsonschema",
    epilog="Example: datacontract import jsonschema --source schema.json --output datacontract.yaml",
)
def import_jsonschema(
    source: Annotated[Optional[str], typer.Option(help="Path to the JSON Schema file.")] = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a JSON Schema file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(), format="jsonschema", source=source, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(
    name="json",
    epilog="Example: datacontract import json --source data.json --output datacontract.yaml",
)
def import_json(
    source: Annotated[Optional[str], typer.Option(help="Path to the JSON data file.")] = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a JSON file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(), format="json", source=source, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(
    name="odcs",
    epilog="Example: datacontract import odcs --source odcs-contract.yaml --output datacontract.yaml",
)
def import_odcs(
    source: Annotated[Optional[str], typer.Option(help="Path to the ODCS data contract file.")] = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from an ODCS file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(), format="odcs", source=source, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(
    name="parquet",
    epilog="Example: datacontract import parquet --source data.parquet --output datacontract.yaml",
)
def import_parquet(
    source: Annotated[Optional[str], typer.Option(help="Path to the Parquet file.")] = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a Parquet file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(), format="parquet", source=source, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(
    name="csv",
    epilog="Example: datacontract import csv --source data.csv --output datacontract.yaml",
)
def import_csv(
    source: Annotated[Optional[str], typer.Option(help="Path to the CSV file.")] = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a CSV file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(), format="csv", source=source, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(
    name="protobuf",
    epilog="Example: datacontract import protobuf --source schema.proto --output datacontract.yaml",
)
def import_protobuf(
    source: Annotated[Optional[str], typer.Option(help="Path to the Protobuf .proto file.")] = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a Protobuf schema file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(), format="protobuf", source=source, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(
    name="pydantic-model",
    epilog="Example: datacontract import pydantic-model --source models.py --output datacontract.yaml",
)
def import_pydantic_model(
    source: Annotated[Optional[str], typer.Option(help="Path to the Python file defining the Pydantic models.")] = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from Pydantic models."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(), format="pydantic-model", source=source, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(
    name="spark",
    epilog="Example: datacontract import spark --tables orders,customers --output datacontract.yaml",
)
def import_spark(
    tables: Annotated[
        Optional[str],
        typer.Option(help="Comma-separated list of Spark table names to import from the current Spark session."),
    ] = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a Spark schema."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(), format="spark", source=tables, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(
    name="iceberg",
    epilog="Examples: datacontract import iceberg --source schema.json --table orders --output datacontract.yaml; "
    "datacontract import iceberg --catalog-url https://polaris.example.com/api/catalog --namespace sales --table orders",
)
def import_iceberg(
    source: Annotated[
        Optional[str], typer.Option(help="Path to the Iceberg schema JSON file. Omit to read from a REST catalog.")
    ] = None,
    table: Annotated[
        Optional[str],
        typer.Option(
            help="Table name to assign to the model created from the Iceberg schema, or the table to load from the catalog."
        ),
    ] = None,
    catalog_url: Annotated[
        Optional[str],
        typer.Option(help="REST catalog endpoint to load the table from (DATACONTRACT_ICEBERG_CATALOG_URL)."),
    ] = None,
    catalog: Annotated[Optional[str], typer.Option(help="Name of the catalog (DATACONTRACT_ICEBERG_CATALOG).")] = None,
    namespace: Annotated[
        Optional[str], typer.Option(help="Namespace of the table in the catalog (DATACONTRACT_ICEBERG_NAMESPACE).")
    ] = None,
    warehouse: Annotated[
        Optional[str], typer.Option(help="Warehouse passed to the catalog (DATACONTRACT_ICEBERG_WAREHOUSE).")
    ] = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from an Iceberg schema file or a REST catalog."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(),
        format="iceberg",
        source=source,
        schema=schema,
        iceberg_table=table,
        iceberg_catalog_url=catalog_url,
        iceberg_catalog=catalog,
        iceberg_namespace=namespace,
        iceberg_warehouse=warehouse,
        owner=owner,
        id=id,
    )
    _write_result(result, output)


@import_app.command(
    name="excel",
    epilog="Example: datacontract import excel --source datacontract.xlsx --output datacontract.yaml",
)
def import_excel(
    source: Annotated[Optional[str], typer.Option(help="Path to the Excel file.")] = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from an Excel file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(), format="excel", source=source, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(
    name="powerbi",
    epilog="Example: datacontract import powerbi --source SemanticModel.pbit --output datacontract.yaml",
)
def import_powerbi(
    source: Annotated[
        Optional[str], typer.Option(help="Path to a Power BI .pbit, .bim, or .json semantic model file.")
    ] = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a Power BI semantic model (.pbit, .bim, or .json) file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(), format="powerbi", source=source, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(
    name="snowflake",
    epilog="Example: datacontract import snowflake --source account --database DEMO_DB --schema PUBLIC --output datacontract.yaml",
)
def import_snowflake(
    source: Annotated[Optional[str], typer.Option(help="Snowflake account name.")] = None,
    output: output_option = None,
    database: database_option = None,
    schema: Annotated[Optional[str], typer.Option("--schema", help="Snowflake schema name.")] = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a Snowflake workspace."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(), format="snowflake", source=source, database=database, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(
    name="redshift",
    epilog="Example: datacontract import redshift --source my-cluster.abc123.us-east-1.redshift.amazonaws.com --database dev --schema public --output datacontract.yaml",
)
def import_redshift(
    source: Annotated[
        Optional[str], typer.Option(help="The Redshift endpoint host of the cluster or serverless workgroup.")
    ] = None,
    port: Annotated[Optional[int], typer.Option(help="The Redshift port (default 5439).")] = None,
    database: database_option = None,
    schema: Annotated[Optional[str], typer.Option("--schema", help="The Redshift schema name.")] = None,
    table: Annotated[
        Optional[List[str]],
        typer.Option(help="Name of a table to import (repeat for multiple tables, omit for all tables in the schema)."),
    ] = None,
    output: output_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from an Amazon Redshift schema."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(),
        format="redshift",
        source=source,
        port=port,
        database=database,
        schema=schema,
        redshift_table=table,
        owner=owner,
        id=id,
    )
    _write_result(result, output)


@import_app.command(
    name="postgres",
    epilog="Example: datacontract import postgres --source localhost --database postgres --schema public --output datacontract.yaml",
)
def import_postgres(
    source: Annotated[Optional[str], typer.Option(help="The host of the Postgres server.")] = None,
    port: Annotated[Optional[int], typer.Option(help="The Postgres port (default 5432).")] = None,
    database: database_option = None,
    schema: Annotated[
        Optional[str], typer.Option("--schema", help="The Postgres schema name (default public).")
    ] = None,
    table: Annotated[
        Optional[List[str]],
        typer.Option(help="Name of a table to import (repeat for multiple tables, omit for all tables in the schema)."),
    ] = None,
    output: output_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a Postgres schema."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(),
        format="postgres",
        source=source,
        port=port,
        database=database,
        schema=schema,
        postgres_table=table,
        owner=owner,
        id=id,
    )
    _write_result(result, output)


@import_app.command(
    name="gcs",
    epilog="Example: datacontract import gcs --source s3://my-bucket/orders/*.json --output datacontract.yaml",
)
def import_gcs(
    source: Annotated[
        Optional[str],
        typer.Option(help="The location of the files. duckdb reads GCS over the S3-compatible endpoint, so use s3://."),
    ] = None,
    format: Annotated[
        Optional[str], typer.Option(help="File format: json, csv, parquet or delta (inferred from the suffix).")
    ] = None,
    delimiter: Annotated[
        Optional[str], typer.Option(help="For JSON: new_line, array or none. Detected automatically when omitted.")
    ] = None,
    output: output_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from files in Google Cloud Storage."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(), format="gcs", source=source, file_format=format, delimiter=delimiter, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(
    name="adls",
    epilog="Example: datacontract import adls --source abfss://my-container/orders/*.json --output datacontract.yaml",
)
def import_adls(
    source: Annotated[
        Optional[str], typer.Option(help="The location of the files, e.g. abfss://my-container/orders/*.json.")
    ] = None,
    format: Annotated[
        Optional[str], typer.Option(help="File format: json, csv, parquet or delta (inferred from the suffix).")
    ] = None,
    delimiter: Annotated[
        Optional[str], typer.Option(help="For JSON: new_line, array or none. Detected automatically when omitted.")
    ] = None,
    output: output_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from files in Azure Blob Storage / ADLS."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(), format="adls", source=source, file_format=format, delimiter=delimiter, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(
    name="trino",
    epilog="Example: datacontract import trino --source localhost --catalog my_catalog --schema my_schema --output datacontract.yaml",
)
def import_trino(
    source: Annotated[Optional[str], typer.Option(help="The host of the Trino coordinator.")] = None,
    port: Annotated[Optional[int], typer.Option(help="The Trino port (default 8080).")] = None,
    catalog: Annotated[Optional[str], typer.Option(help="The Trino catalog.")] = None,
    schema: Annotated[Optional[str], typer.Option("--schema", help="The Trino schema.")] = None,
    table: Annotated[
        Optional[List[str]],
        typer.Option(help="Name of a table to import (repeat for multiple tables, omit for all tables)."),
    ] = None,
    output: output_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a Trino catalog."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(),
        format="trino",
        source=source,
        port=port,
        catalog=catalog,
        schema=schema,
        trino_table=table,
        owner=owner,
        id=id,
    )
    _write_result(result, output)


@import_app.command(
    name="oracle",
    epilog="Example: datacontract import oracle --source localhost --service-name XEPDB1 --schema ADMIN --output datacontract.yaml",
)
def import_oracle(
    source: Annotated[Optional[str], typer.Option(help="The host of the Oracle database.")] = None,
    port: Annotated[Optional[int], typer.Option(help="The Oracle port (default 1521).")] = None,
    service_name: Annotated[Optional[str], typer.Option(help="The Oracle service name, e.g. XEPDB1.")] = None,
    schema: Annotated[
        Optional[str], typer.Option("--schema", help="The owning schema, e.g. ADMIN (Oracle upper-cases it).")
    ] = None,
    table: Annotated[
        Optional[List[str]],
        typer.Option(help="Name of a table to import (repeat for multiple tables, omit for all tables)."),
    ] = None,
    output: output_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from an Oracle database."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(),
        format="oracle",
        source=source,
        port=port,
        service_name=service_name,
        schema=schema,
        oracle_table=table,
        owner=owner,
        id=id,
    )
    _write_result(result, output)


@import_app.command(
    name="sqlserver",
    epilog="Example: datacontract import sqlserver --source localhost --database mydb --output datacontract.yaml",
)
def import_sqlserver(
    source: Annotated[Optional[str], typer.Option(help="The host of the SQL Server instance.")] = None,
    port: Annotated[Optional[int], typer.Option(help="The SQL Server port (default 1433).")] = None,
    database: database_option = None,
    schema: Annotated[Optional[str], typer.Option("--schema", help="The schema name (default dbo).")] = None,
    table: Annotated[
        Optional[List[str]],
        typer.Option(help="Name of a table to import (repeat for multiple tables, omit for all tables)."),
    ] = None,
    output: output_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a SQL Server database."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(),
        format="sqlserver",
        source=source,
        port=port,
        database=database,
        schema=schema,
        sqlserver_table=table,
        owner=owner,
        id=id,
    )
    _write_result(result, output)


@import_app.command(
    name="mysql",
    epilog="Example: datacontract import mysql --source localhost --database mydb --output datacontract.yaml",
)
def import_mysql(
    source: Annotated[Optional[str], typer.Option(help="The host of the MySQL server.")] = None,
    port: Annotated[Optional[int], typer.Option(help="The MySQL port (default 3306).")] = None,
    database: database_option = None,
    table: Annotated[
        Optional[List[str]],
        typer.Option(help="Name of a table to import (repeat for multiple tables, omit for all tables)."),
    ] = None,
    output: output_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a MySQL database."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(),
        format="mysql",
        source=source,
        port=port,
        database=database,
        mysql_table=table,
        owner=owner,
        id=id,
    )
    _write_result(result, output)


@import_app.command(
    name="s3",
    epilog="Example: datacontract import s3 --source s3://my-bucket/orders/*.json --output datacontract.yaml",
)
def import_s3(
    source: Annotated[
        Optional[str], typer.Option(help="The S3 location of the files, e.g. s3://my-bucket/orders/*.json.")
    ] = None,
    format: Annotated[
        Optional[str], typer.Option(help="File format: json, csv, parquet or delta (inferred from the suffix).")
    ] = None,
    delimiter: Annotated[
        Optional[str], typer.Option(help="For JSON: new_line, array or none. Detected automatically when omitted.")
    ] = None,
    endpoint_url: Annotated[
        Optional[str], typer.Option(help="Endpoint of an S3-compatible store, e.g. http://localhost:9000.")
    ] = None,
    output: output_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from files in S3."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(),
        format="s3",
        source=source,
        file_format=format,
        delimiter=delimiter,
        endpoint_url=endpoint_url,
        owner=owner,
        id=id,
    )
    _write_result(result, output)


@import_app.command(
    name="athena",
    epilog="Example: datacontract import athena --schema my_database --staging-dir s3://my-bucket/athena-results/ --output datacontract.yaml",
)
def import_athena(
    schema: Annotated[
        Optional[str], typer.Option("--schema", help="The Athena database name (called schema in the contract).")
    ] = None,
    staging_dir: Annotated[
        Optional[str],
        typer.Option(help="S3 location where Athena writes query results, e.g. s3://my-bucket/athena-results/."),
    ] = None,
    region: Annotated[Optional[str], typer.Option(help="The AWS region the Glue Data Catalog lives in.")] = None,
    catalog: Annotated[Optional[str], typer.Option(help="The Athena catalog (default awsdatacatalog).")] = None,
    table: Annotated[
        Optional[List[str]],
        typer.Option(help="Name of a table to import (repeat for multiple tables, omit for all tables in the schema)."),
    ] = None,
    output: output_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from an Amazon Athena database."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(),
        format="athena",
        schema=schema,
        staging_dir=staging_dir,
        region=region,
        catalog=catalog,
        athena_table=table,
        owner=owner,
        id=id,
    )
    _write_result(result, output)
