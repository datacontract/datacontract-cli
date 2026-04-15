from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from datacontract.cli import OrderedCommands, debug_option, enable_debug_logging
from datacontract.data_contract import DataContract
from datacontract.export.exporter import ExportFormat

console = Console()

export_app = typer.Typer(cls=OrderedCommands, no_args_is_help=True)

# ---------------------------------------------------------------------------
# Shared option type aliases
# ---------------------------------------------------------------------------
location_arg = Annotated[str, typer.Argument(help="The location (url or path) of the data contract yaml.")]
output_option = Annotated[
    Optional[Path],
    typer.Option(
        help="Specify the file path where the exported data will be saved. If no path is provided, the output will be printed to stdout."
    ),
]
server_option = Annotated[Optional[str], typer.Option(help="The server name to export.")]
schema_name_option = Annotated[
    str, typer.Option(help="The name of the schema to export, e.g., `orders`, or `all` for all schemas (default).")
]
schema_option = Annotated[Optional[str], typer.Option(help="The location (url or path) of the ODCS JSON Schema")]


def _export(
    export_format: ExportFormat,
    location: str,
    output: Optional[Path],
    server: Optional[str],
    schema_name: str,
    schema: Optional[str],
    sql_server_type: str = "auto",
    rdf_base: Optional[str] = None,
    engine: Optional[str] = None,
    template: Optional[Path] = None,
):
    result = DataContract(data_contract_file=location, schema_location=schema, server=server).export(
        export_format=export_format,
        schema_name=schema_name,
        server=server,
        rdf_base=rdf_base,
        sql_server_type=sql_server_type,
        engine=engine,
        template=template,
    )
    if output is None:
        console.print(result, markup=False, soft_wrap=True)
    else:
        if isinstance(result, bytes):
            with output.open(mode="wb") as f:
                f.write(result)
        else:
            with output.open(mode="w", encoding="utf-8") as f:
                f.write(result)
        console.print(f"Written result to {output}")


# ---------------------------------------------------------------------------
# Export subcommands
# ---------------------------------------------------------------------------


@export_app.command(name="sql")
def export_sql(
    location: location_arg = "datacontract.yaml",
    server_type: Annotated[
        Optional[str],
        typer.Option(
            help="The server type to determine the SQL dialect. Accepted values: auto, snowflake, postgres, mysql, databricks, sqlserver, bigquery, trino, oracle."
        ),
    ] = "auto",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to SQL DDL."""
    enable_debug_logging(debug)
    _export(ExportFormat.sql, location, output, server, schema_name, schema, sql_server_type=server_type)


@export_app.command(name="sql-query")
def export_sql_query(
    location: location_arg = "datacontract.yaml",
    server_type: Annotated[
        Optional[str],
        typer.Option(
            help="The server type to determine the SQL dialect. Accepted values: auto, snowflake, postgres, mysql, databricks, sqlserver, bigquery, trino, oracle."
        ),
    ] = "auto",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to a SQL query."""
    enable_debug_logging(debug)
    _export(ExportFormat.sql_query, location, output, server, schema_name, schema, sql_server_type=server_type)


@export_app.command(name="dbt-models")
def export_dbt_models(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to dbt model schema YAML."""
    enable_debug_logging(debug)
    _export(ExportFormat.dbt_models, location, output, server, schema_name, schema)


@export_app.command(name="dbt-sources")
def export_dbt_sources(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to dbt sources YAML."""
    enable_debug_logging(debug)
    _export(ExportFormat.dbt_sources, location, output, server, schema_name, schema)


@export_app.command(name="dbt-staging-sql")
def export_dbt_staging_sql(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to a dbt staging SQL file."""
    enable_debug_logging(debug)
    _export(ExportFormat.dbt_staging_sql, location, output, server, schema_name, schema)


@export_app.command(name="avro")
def export_avro(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to Avro schema."""
    enable_debug_logging(debug)
    _export(ExportFormat.avro, location, output, server, schema_name, schema)


@export_app.command(name="avro-idl")
def export_avro_idl(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to Avro IDL."""
    enable_debug_logging(debug)
    _export(ExportFormat.avro_idl, location, output, server, schema_name, schema)


@export_app.command(name="jsonschema")
def export_jsonschema(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to JSON Schema."""
    enable_debug_logging(debug)
    _export(ExportFormat.jsonschema, location, output, server, schema_name, schema)


@export_app.command(name="pydantic-model")
def export_pydantic_model(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to a Pydantic model."""
    enable_debug_logging(debug)
    _export(ExportFormat.pydantic_model, location, output, server, schema_name, schema)


@export_app.command(name="protobuf")
def export_protobuf(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to Protobuf schema."""
    enable_debug_logging(debug)
    _export(ExportFormat.protobuf, location, output, server, schema_name, schema)


@export_app.command(name="odcs")
def export_odcs(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to ODCS format."""
    enable_debug_logging(debug)
    _export(ExportFormat.odcs, location, output, server, schema_name, schema)


@export_app.command(name="rdf")
def export_rdf(
    location: location_arg = "datacontract.yaml",
    base: Annotated[
        Optional[str],
        typer.Option(help="The base URI used to generate the RDF graph."),
    ] = None,
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to RDF."""
    enable_debug_logging(debug)
    _export(ExportFormat.rdf, location, output, server, schema_name, schema, rdf_base=base)


@export_app.command(name="html")
def export_html(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to HTML."""
    enable_debug_logging(debug)
    _export(ExportFormat.html, location, output, server, schema_name, schema)


@export_app.command(name="markdown")
def export_markdown(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to Markdown."""
    enable_debug_logging(debug)
    _export(ExportFormat.markdown, location, output, server, schema_name, schema)


@export_app.command(name="mermaid")
def export_mermaid(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to Mermaid diagram."""
    enable_debug_logging(debug)
    _export(ExportFormat.mermaid, location, output, server, schema_name, schema)


@export_app.command(name="bigquery")
def export_bigquery(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to BigQuery schema."""
    enable_debug_logging(debug)
    _export(ExportFormat.bigquery, location, output, server, schema_name, schema)


@export_app.command(name="dbml")
def export_dbml(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to DBML."""
    enable_debug_logging(debug)
    _export(ExportFormat.dbml, location, output, server, schema_name, schema)


@export_app.command(name="go")
def export_go(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to Go structs."""
    enable_debug_logging(debug)
    _export(ExportFormat.go, location, output, server, schema_name, schema)


@export_app.command(name="spark")
def export_spark(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to Spark schema."""
    enable_debug_logging(debug)
    _export(ExportFormat.spark, location, output, server, schema_name, schema)


@export_app.command(name="sqlalchemy")
def export_sqlalchemy(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to SQLAlchemy models."""
    enable_debug_logging(debug)
    _export(ExportFormat.sqlalchemy, location, output, server, schema_name, schema)


@export_app.command(name="iceberg")
def export_iceberg(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to Iceberg schema."""
    enable_debug_logging(debug)
    _export(ExportFormat.iceberg, location, output, server, schema_name, schema)


@export_app.command(name="sodacl")
def export_sodacl(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to SodaCL checks."""
    enable_debug_logging(debug)
    _export(ExportFormat.sodacl, location, output, server, schema_name, schema)


@export_app.command(name="great-expectations")
def export_great_expectations(
    location: location_arg = "datacontract.yaml",
    engine: Annotated[
        Optional[str],
        typer.Option(help="The engine used for the Great Expectations run."),
    ] = None,
    server_type: Annotated[
        Optional[str],
        typer.Option(
            help="The server type to determine the SQL dialect (when using --engine sql). Accepted values: auto, snowflake, postgres, mysql, databricks, sqlserver, bigquery, trino, oracle."
        ),
    ] = "auto",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to Great Expectations suite."""
    enable_debug_logging(debug)
    _export(ExportFormat.great_expectations, location, output, server, schema_name, schema, engine=engine, sql_server_type=server_type)


@export_app.command(name="data-caterer")
def export_data_caterer(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to Data Caterer format."""
    enable_debug_logging(debug)
    _export(ExportFormat.data_caterer, location, output, server, schema_name, schema)


@export_app.command(name="dcs")
def export_dcs(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to DCS format."""
    enable_debug_logging(debug)
    _export(ExportFormat.dcs, location, output, server, schema_name, schema)


@export_app.command(name="dqx")
def export_dqx(
    location: location_arg = "datacontract.yaml",
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to DQX format."""
    enable_debug_logging(debug)
    _export(ExportFormat.dqx, location, output, server, schema_name, schema)


@export_app.command(name="excel")
def export_excel(
    location: location_arg = "datacontract.yaml",
    template: Annotated[
        Optional[Path],
        typer.Option(help="Path or URL to a custom Excel template."),
    ] = None,
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to Excel."""
    enable_debug_logging(debug)
    if output is None:
        console.print("Error: Excel export requires --output.")
        raise typer.Exit(code=1)
    _export(ExportFormat.excel, location, output, server, schema_name, schema, template=template)


@export_app.command(name="custom")
def export_custom(
    location: location_arg = "datacontract.yaml",
    template: Annotated[
        Optional[Path],
        typer.Option(help="Path to a Jinja template for custom export."),
    ] = None,
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract using a custom Jinja template."""
    enable_debug_logging(debug)
    _export(ExportFormat.custom, location, output, server, schema_name, schema, template=template)
