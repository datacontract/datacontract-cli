from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from datacontract.cli import OrderedCommandsWithMigrationHints, debug_option, enable_debug_logging
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
    result = DataContract.import_from_source(format="avro", source=source, schema=schema, owner=owner, id=id)
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
        format="dbt", source=source, schema=schema, dbt_model=model, owner=owner, id=id
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
        format="glue", source=database, schema=schema, glue_table=table, owner=owner, id=id
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


@import_app.command(
    name="unity",
    epilog="Example: datacontract import unity --table catalog.schema.my_table --output datacontract.yaml",
)
def import_unity(
    source: Annotated[
        Optional[str],
        typer.Option(
            help="Path to a Unity Catalog TableInfo JSON file. If omitted, imports from the Unity API using --table."
        ),
    ] = None,
    table: Annotated[
        Optional[List[str]],
        typer.Option(help="Full name of a table in the Unity Catalog (repeat for multiple tables)."),
    ] = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from Databricks Unity Catalog."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        format="unity", source=source, schema=schema, unity_table_full_name=table, owner=owner, id=id
    )
    _write_result(result, output)


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
    result = DataContract.import_from_source(format="jsonschema", source=source, schema=schema, owner=owner, id=id)
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
    result = DataContract.import_from_source(format="json", source=source, schema=schema, owner=owner, id=id)
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
    result = DataContract.import_from_source(format="odcs", source=source, schema=schema, owner=owner, id=id)
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
    result = DataContract.import_from_source(format="parquet", source=source, schema=schema, owner=owner, id=id)
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
    result = DataContract.import_from_source(format="csv", source=source, schema=schema, owner=owner, id=id)
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
    result = DataContract.import_from_source(format="protobuf", source=source, schema=schema, owner=owner, id=id)
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
    result = DataContract.import_from_source(format="spark", source=tables, schema=schema, owner=owner, id=id)
    _write_result(result, output)


@import_app.command(
    name="iceberg",
    epilog="Example: datacontract import iceberg --source schema.json --table orders --output datacontract.yaml",
)
def import_iceberg(
    source: Annotated[Optional[str], typer.Option(help="Path to the Iceberg schema JSON file.")] = None,
    table: Annotated[
        Optional[str],
        typer.Option(help="Table name to assign to the model created from the Iceberg schema."),
    ] = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from an Iceberg schema."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        format="iceberg", source=source, schema=schema, iceberg_table=table, owner=owner, id=id
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
    result = DataContract.import_from_source(format="excel", source=source, schema=schema, owner=owner, id=id)
    _write_result(result, output)
