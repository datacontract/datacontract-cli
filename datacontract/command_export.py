from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from datacontract.cli import OrderedCommandsWithMigrationHints, debug_option, enable_debug_logging
from datacontract.data_contract import DataContract
from datacontract.export.exporter import ExportFormat, SqlServerType
from datacontract.export.great_expectations_exporter import GreatExpectationsEngine

console = Console()

export_app = typer.Typer(cls=OrderedCommandsWithMigrationHints, no_args_is_help=True)

# ---------------------------------------------------------------------------
# Shared option type aliases
# ---------------------------------------------------------------------------
location_arg = Annotated[str, typer.Argument(help="The location (url or path) of the data contract yaml.")]
output_option = Annotated[
    Optional[Path],
    typer.Option(
        help="File path where the exported data will be saved. If not provided, it will be printed to stdout."
    ),
]
server_option = Annotated[Optional[str], typer.Option(help="The server name to export.")]
schema_name_option = Annotated[
    str,
    typer.Option(help="Which schema to export, e.g., `orders`, or `all` for all schemas (default)."),
]
schema_option = Annotated[
    Optional[str],
    typer.Option("--json-schema", help="The location (url or path) of the ODCS JSON Schema."),
]
dialect_option = Annotated[
    SqlServerType,
    typer.Option(
        help="The SQL dialect. Use `auto` (default) to detect the SQL dialect via the specified servers in the data contract."
    ),
]


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
    template: Optional[Path | str] = None,
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


@export_app.command(
    name="sql",
    epilog="Example: datacontract export sql datacontract.yaml --dialect postgres --output ddl.sql",
)
def export_sql(
    location: location_arg = "datacontract.yaml",
    dialect: dialect_option = SqlServerType.auto,
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to SQL DDL."""
    enable_debug_logging(debug)
    _export(ExportFormat.sql, location, output, server, schema_name, schema, sql_server_type=dialect.value)


@export_app.command(
    name="sql-query",
    epilog="Example: datacontract export sql-query datacontract.yaml --dialect snowflake --output query.sql",
)
def export_sql_query(
    location: location_arg = "datacontract.yaml",
    dialect: dialect_option = SqlServerType.auto,
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to a SQL query."""
    enable_debug_logging(debug)
    _export(ExportFormat.sql_query, location, output, server, schema_name, schema, sql_server_type=dialect.value)


@export_app.command(
    name="dbt-models",
    epilog="Example: datacontract export dbt-models datacontract.yaml --output schema.yml",
)
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


@export_app.command(
    name="dbt",
    hidden=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
def export_dbt_removed(ctx: typer.Context):
    """Removed: use `datacontract export dbt-models` instead."""
    ctx.fail(
        "`export dbt` was renamed to `export dbt-models` in v0.12.0. See https://github.com/datacontract/datacontract-cli/releases/tag/v0.12.0"
    )


@export_app.command(
    name="dbt-sources",
    epilog="Example: datacontract export dbt-sources datacontract.yaml --output sources.yml",
)
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


@export_app.command(
    name="dbt-staging-sql",
    epilog="Example: datacontract export dbt-staging-sql datacontract.yaml --output stg.sql",
)
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


@export_app.command(
    name="avro",
    epilog="Example: datacontract export avro datacontract.yaml --output schema.avsc",
)
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


@export_app.command(
    name="avro-idl",
    epilog="Example: datacontract export avro-idl datacontract.yaml --output schema.avdl",
)
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


@export_app.command(
    name="jsonschema",
    epilog="Example: datacontract export jsonschema datacontract.yaml --output schema.json",
)
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


@export_app.command(
    name="pydantic-model",
    epilog="Example: datacontract export pydantic-model datacontract.yaml --output models.py",
)
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


@export_app.command(
    name="protobuf",
    epilog="Example: datacontract export protobuf datacontract.yaml --output schema.proto",
)
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


@export_app.command(
    name="odcs",
    epilog="Example: datacontract export odcs datacontract.yaml --output odcs-contract.yaml",
)
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


@export_app.command(
    name="rdf",
    epilog="Example: datacontract export rdf datacontract.yaml --base https://example.com/ --output contract.ttl",
)
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


@export_app.command(
    name="html",
    epilog="Example: datacontract export html datacontract.yaml --output datacontract.html",
)
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


@export_app.command(
    name="markdown",
    epilog="Example: datacontract export markdown datacontract.yaml --output datacontract.md",
)
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


@export_app.command(
    name="mermaid",
    epilog="Example: datacontract export mermaid datacontract.yaml --output diagram.mmd",
)
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


@export_app.command(
    name="bigquery",
    epilog="Example: datacontract export bigquery datacontract.yaml --output schema.json",
)
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


@export_app.command(
    name="dbml",
    epilog="Example: datacontract export dbml datacontract.yaml --output schema.dbml",
)
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


@export_app.command(
    name="go",
    epilog="Example: datacontract export go datacontract.yaml --output models.go",
)
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


@export_app.command(
    name="spark",
    epilog="Example: datacontract export spark datacontract.yaml --output schema.py",
)
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


@export_app.command(
    name="sqlalchemy",
    epilog="Example: datacontract export sqlalchemy datacontract.yaml --output models.py",
)
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


@export_app.command(
    name="iceberg",
    epilog="Example: datacontract export iceberg datacontract.yaml --output schema.json",
)
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


@export_app.command(
    name="sodacl",
    epilog="Example: datacontract export sodacl datacontract.yaml --output checks.yml",
)
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


@export_app.command(
    name="great-expectations",
    epilog="Example: datacontract export great-expectations datacontract.yaml --engine sql --dialect postgres --output expectations.json",
)
def export_great_expectations(
    location: location_arg = "datacontract.yaml",
    engine: Annotated[
        Optional[GreatExpectationsEngine],
        typer.Option(help="The engine used for Great Expectations run."),
    ] = None,
    dialect: dialect_option = SqlServerType.auto,
    output: output_option = None,
    server: server_option = None,
    schema_name: schema_name_option = "all",
    schema: schema_option = None,
    debug: debug_option = None,
):
    """Export a data contract to Great Expectations suite."""
    enable_debug_logging(debug)
    _export(
        ExportFormat.great_expectations,
        location,
        output,
        server,
        schema_name,
        schema,
        engine=engine.value if engine is not None else None,
        sql_server_type=dialect.value,
    )


@export_app.command(
    name="data-caterer",
    epilog="Example: datacontract export data-caterer datacontract.yaml --output plan.yaml",
)
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


@export_app.command(
    name="dcs",
    epilog="Example: datacontract export dcs datacontract.yaml --output contract.dcs.yaml",
)
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


@export_app.command(
    name="dqx",
    epilog="Example: datacontract export dqx datacontract.yaml --output checks.yaml",
)
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


@export_app.command(
    name="excel",
    epilog="Example: datacontract export excel datacontract.yaml --output datacontract.xlsx",
)
def export_excel(
    location: location_arg = "datacontract.yaml",
    template: Annotated[
        Optional[str],
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
        console.print("❌ Error: Excel export requires an output file path.")
        console.print("💡 Hint: Use --output to specify where to save the Excel file, e.g.:")
        console.print("   datacontract export excel --output datacontract.xlsx")
        raise typer.Exit(code=1)
    _export(ExportFormat.excel, location, output, server, schema_name, schema, template=template)


@export_app.command(
    name="custom",
    epilog="Example: datacontract export custom datacontract.yaml --template template.j2 --output output.txt",
)
def export_custom(
    location: location_arg = "datacontract.yaml",
    template: Annotated[
        Optional[Path],
        typer.Option(help="Path to Jinja template."),
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
