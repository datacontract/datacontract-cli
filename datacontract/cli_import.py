from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from datacontract.cli import OrderedCommands, debug_option, enable_debug_logging
from datacontract.data_contract import DataContract

console = Console()

import_app = typer.Typer(cls=OrderedCommands, no_args_is_help=True)

# ---------------------------------------------------------------------------
# Shared option type aliases
# ---------------------------------------------------------------------------
source_option = Annotated[Optional[str], typer.Option(help="The path to the file that should be imported.")]
output_option = Annotated[
    Optional[Path],
    typer.Option(
        help="Specify the file path where the Data Contract will be saved. If no path is provided, the output will be printed to stdout."
    ),
]
schema_option = Annotated[
    Optional[str],
    typer.Option("--odcs-schema", help="The location (url or path) of the ODCS JSON Schema"),
]
template_option = Annotated[Optional[str], typer.Option(help="The location (url or path) of the ODCS template")]
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


@import_app.command(name="sql")
def import_sql(
    source: source_option = None,
    dialect: Annotated[
        Optional[str],
        typer.Option(
            help="The SQL dialect. Accepted values: postgres, tsql, bigquery, snowflake, databricks, spark, duckdb."
        ),
    ] = None,
    output: output_option = None,
    schema: schema_option = None,
    template: template_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a SQL DDL file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        format="sql", source=source, template=template, schema=schema, dialect=dialect, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(name="avro")
def import_avro(
    source: source_option = None,
    output: output_option = None,
    schema: schema_option = None,
    template: template_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from an Avro schema file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        format="avro", source=source, template=template, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(name="dbt")
def import_dbt(
    source: source_option = None,
    model: Annotated[
        Optional[List[str]],
        typer.Option(
            help="List of models names to import from the dbt manifest file (repeat for multiple models names, leave empty for all models in the dataset)."
        ),
    ] = None,
    output: output_option = None,
    schema: schema_option = None,
    template: template_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a dbt manifest file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        format="dbt", source=source, template=template, schema=schema, dbt_model=model, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(name="dbml")
def import_dbml(
    source: source_option = None,
    schema: Annotated[
        Optional[List[str]],
        typer.Option(
            help="List of schema names to import from the DBML file (repeat for multiple schema names, leave empty for all tables in the file)."
        ),
    ] = None,
    table: Annotated[
        Optional[List[str]],
        typer.Option(
            help="List of table names to import from the DBML file (repeat for multiple table names, leave empty for all tables in the file)."
        ),
    ] = None,
    output: output_option = None,
    odcs_schema: Annotated[
        Optional[str], typer.Option("--odcs-schema", help="The location (url or path) of the ODCS JSON Schema")
    ] = None,
    template: template_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a DBML file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        format="dbml",
        source=source,
        template=template,
        schema=odcs_schema,
        dbml_schema=schema,
        dbml_table=table,
        owner=owner,
        id=id,
    )
    _write_result(result, output)


@import_app.command(name="glue")
def import_glue(
    source: source_option = None,
    table: Annotated[
        Optional[List[str]],
        typer.Option(
            help="List of table ids to import from the Glue Database (repeat for multiple table ids, leave empty for all tables in the dataset)."
        ),
    ] = None,
    output: output_option = None,
    schema: schema_option = None,
    template: template_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from AWS Glue."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        format="glue", source=source, template=template, schema=schema, glue_table=table, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(name="bigquery")
def import_bigquery(
    source: source_option = None,
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
    template: template_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from BigQuery."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        format="bigquery",
        source=source,
        template=template,
        schema=schema,
        bigquery_project=project,
        bigquery_dataset=dataset,
        bigquery_table=table,
        owner=owner,
        id=id,
    )
    _write_result(result, output)


@import_app.command(name="unity")
def import_unity(
    source: source_option = None,
    table: Annotated[Optional[List[str]], typer.Option(help="Full name of a table in the Unity Catalog")] = None,
    output: output_option = None,
    schema: schema_option = None,
    template: template_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from Databricks Unity Catalog."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        format="unity", source=source, template=template, schema=schema, unity_table_full_name=table, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(name="jsonschema")
def import_jsonschema(
    source: source_option = None,
    output: output_option = None,
    schema: schema_option = None,
    template: template_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a JSON Schema file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        format="jsonschema", source=source, template=template, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(name="json")
def import_json(
    source: source_option = None,
    output: output_option = None,
    schema: schema_option = None,
    template: template_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a JSON file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        format="json", source=source, template=template, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(name="odcs")
def import_odcs(
    source: source_option = None,
    output: output_option = None,
    schema: schema_option = None,
    template: template_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from an ODCS file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        format="odcs", source=source, template=template, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(name="parquet")
def import_parquet(
    source: source_option = None,
    output: output_option = None,
    schema: schema_option = None,
    template: template_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a Parquet file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        format="parquet", source=source, template=template, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(name="csv")
def import_csv(
    source: source_option = None,
    output: output_option = None,
    schema: schema_option = None,
    template: template_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a CSV file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        format="csv", source=source, template=template, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(name="protobuf")
def import_protobuf(
    source: source_option = None,
    output: output_option = None,
    schema: schema_option = None,
    template: template_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a Protobuf schema file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        format="protobuf", source=source, template=template, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(name="spark")
def import_spark(
    source: source_option = None,
    output: output_option = None,
    schema: schema_option = None,
    template: template_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a Spark schema."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        format="spark", source=source, template=template, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(name="iceberg")
def import_iceberg(
    source: source_option = None,
    table: Annotated[
        Optional[str],
        typer.Option(help="Table name to assign to the model created from the Iceberg schema."),
    ] = None,
    output: output_option = None,
    schema: schema_option = None,
    template: template_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from an Iceberg schema."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        format="iceberg", source=source, template=template, schema=schema, iceberg_table=table, owner=owner, id=id
    )
    _write_result(result, output)


@import_app.command(name="excel")
def import_excel(
    source: source_option = None,
    output: output_option = None,
    schema: schema_option = None,
    template: template_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from an Excel file."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        format="excel", source=source, template=template, schema=schema, owner=owner, id=id
    )
    _write_result(result, output)
