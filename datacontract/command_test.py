import json
from enum import Enum
from pathlib import Path

import typer
from typing_extensions import Annotated

from datacontract.cli import (
    _print_logs,
    _print_publish_failure,
    app,
    console,
    debug_option,
    enable_debug_logging,
    resolve_output_format,
    validate_publish_url,
)
from datacontract.config import cli_config
from datacontract.data_contract import DataContract
from datacontract.lint.resolve import resolve_data_contract
from datacontract.output.output_format import OutputFormat
from datacontract.output.test_results_writer import write_test_result


class CheckCategory(str, Enum):
    schema = "schema"
    quality = "quality"
    servicelevel = "servicelevel"
    custom = "custom"


# ODCS section names (`properties`, `slaProperties`) accepted as user-facing
# aliases for the legacy category names. Keyed lowercase: `--checks` matching
# is case-insensitive.
CHECK_CATEGORY_ALIASES = {
    "properties": CheckCategory.schema,
    "slaproperties": CheckCategory.servicelevel,
}
CHECK_CATEGORY_OPTIONS = "properties, quality, slaProperties, custom; legacy aliases: schema, servicelevel"


class QualityDimension(str, Enum):
    """The ODCS `quality.dimension` enum (see the bundled ODCS JSON schema)."""

    accuracy = "accuracy"
    completeness = "completeness"
    conformity = "conformity"
    consistency = "consistency"
    coverage = "coverage"
    timeliness = "timeliness"
    uniqueness = "uniqueness"


def _parse_enum_csv(
    value: str | None,
    enum_cls: type[Enum],
    option: str,
    label: str,
    aliases: dict[str, Enum] | None = None,
    available: str | None = None,
) -> set[str] | None:
    """Parse a comma-separated option into a set of enum values, or None if unset.

    Matching is case-insensitive; `aliases` maps additional lowercase spellings
    to their enum value. `available` overrides the choices shown in errors.
    """
    if value is None:
        return None
    allowed = [e.value for e in enum_cls]
    raw = [v.strip() for v in value.split(",") if v.strip()]
    if not raw:
        console.print(f"[red]Empty {option} specified.[/red]")
        console.print(f"Available {label}: {available or ', '.join(allowed)}")
        raise typer.Exit(code=1)
    aliases = aliases or {}
    values = set()
    invalid = set()
    for v in raw:
        key = v.lower()
        if key in aliases:
            values.add(aliases[key].value)
        elif key in allowed:
            values.add(key)
        else:
            invalid.add(v)
    if invalid:
        console.print(f"[red]Invalid {option} specified: {', '.join(sorted(invalid))}[/red]")
        console.print(f"Available {label}: {available or ', '.join(allowed)}")
        raise typer.Exit(code=1)
    return values


def _parse_filters(value: str | None) -> dict[str, str] | None:
    """Parse the `--filters` JSON object mapping schema name to predicate, or None if unset."""
    if value is None:
        return None
    usage = 'Expected a JSON object mapping schema name to predicate, e.g., --filters \'{"orders": "order_id > 100"}\''
    try:
        filters = json.loads(value)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid --filters specified: not valid JSON ({e}).[/red]")
        console.print(usage)
        raise typer.Exit(code=1)
    if (
        not isinstance(filters, dict)
        or not filters
        or not all(isinstance(predicate, str) and predicate.strip() for predicate in filters.values())
    ):
        console.print(f"[red]Invalid --filters specified: {value!r}[/red]")
        console.print(usage)
        raise typer.Exit(code=1)
    return {schema_name: predicate.strip() for schema_name, predicate in filters.items()}


def _parse_csv(value: str | None, option: str) -> set[str] | None:
    """Parse a comma-separated option into a set of values, or None if unset."""
    if value is None:
        return None
    values = {v.strip() for v in value.split(",") if v.strip()}
    if not values:
        console.print(f"[red]Empty {option} specified.[/red]")
        raise typer.Exit(code=1)
    return values


@app.command(
    name="test",
    epilog="Example: datacontract test datacontract.yaml --server production",
)
def test(
    location: Annotated[
        str,
        typer.Argument(help="The location (url, s3 url, or local path) of the data contract yaml."),
    ] = "datacontract.yaml",
    schema: Annotated[
        str,
        typer.Option("--json-schema", help="The location (url or path) of the ODCS JSON Schema"),
    ] = None,
    server: Annotated[
        str,
        typer.Option(
            help="The server configuration to run the schema and quality tests. "
            "Use the key of the server object in the data contract yaml file "
            "to refer to a server, e.g., `production`, or `all` for all "
            "servers (default)."
        ),
    ] = "all",
    schema_name: Annotated[
        str,
        typer.Option(help="Which schema to test, e.g., `orders`, or `all` for all schemas (default)."),
    ] = "all",
    publish_test_results: Annotated[
        bool, typer.Option(help="Deprecated. Use publish parameter. Publish the results after the test")
    ] = False,
    publish: Annotated[str, typer.Option(help="The url to publish the results after the test.")] = None,
    output: Annotated[
        Path,
        typer.Option(
            help="Specify the file path where the test results should be written to (e.g., './test-results/TEST-datacontract.xml')."
        ),
    ] = None,
    output_format: Annotated[
        OutputFormat,
        typer.Option(help="The target format for the test results. Accepted values: json, junit."),
    ] = None,
    checks: Annotated[
        str,
        typer.Option(
            help="Comma-separated list of check categories to run "
            f"(available: {CHECK_CATEGORY_OPTIONS}). Omit to enable all."
        ),
    ] = None,
    dimension: Annotated[
        str,
        typer.Option(
            help="Comma-separated list of quality dimensions to run "
            f"(available: {', '.join(d.value for d in QualityDimension)}). "
            "Runs the quality rules declaring a matching `dimension`, plus the schema "
            "and service level checks that measure it. Omit to run everything."
        ),
    ] = None,
    quality_id: Annotated[
        str,
        typer.Option(
            help="Comma-separated list of quality rule ids to run, as defined in the `id` of the "
            "quality rule. Runs only those rules, no schema or service level checks. "
            "Fails if an id is not defined in the data contract. Omit to run everything."
        ),
    ] = None,
    tag: Annotated[
        str,
        typer.Option(
            help="Comma-separated list of tags to run. Runs the quality rules declaring a matching "
            "tag in their `tags`, no schema or service level checks. Omit to run everything."
        ),
    ] = None,
    filter: Annotated[
        str,
        typer.Option(
            help="A SQL predicate to filter the rows under test, in the dialect of the server, "
            'e.g., "ingested_at >= CURRENT_DATE - 1". Only works if a single schema is tested; '
            "for contracts with multiple schemas, combine with --schema-name or use --filters. "
            "Schema checks and custom SQL queries are not filtered."
        ),
    ] = None,
    filters: Annotated[
        str,
        typer.Option(
            help="Row filters per schema, as a JSON object mapping schema name to SQL predicate, "
            'e.g., \'{"orders": "ingested_at >= CURRENT_DATE - 1"}\'. '
            "Schema checks and custom SQL queries are not filtered."
        ),
    ] = None,
    metadata_only: Annotated[
        bool,
        typer.Option(
            help="Run only checks that read the schema (field presence and types). "
            "Checks that read row values are skipped."
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            help="Report the checks that would run, without connecting to the server or reading any data. "
            "Reported checks have the result 'skipped', or 'warning' where a check could not be planned."
        ),
    ] = False,
    include_failed_samples: Annotated[
        bool,
        typer.Option(
            help="Collect a small sample of rows that failed each missing/invalid/duplicate check "
            "(identifier + offending columns; sensitive columns omitted). Off by default."
        ),
    ] = False,
    logs: Annotated[bool, typer.Option(help="Print logs")] = False,
    ssl_verification: Annotated[
        bool,
        typer.Option(help="SSL verification when publishing the data contract."),
    ] = True,
    inline_references: Annotated[
        bool,
        typer.Option(
            help="Resolve external references (currently: authoritativeDefinitions\\[type in {definition, semantics}]) in the "
            "contract and inline the fetched content from the configured entropy-data host."
        ),
    ] = True,
    debug: debug_option = None,
):
    """
    Run schema and quality tests on configured servers.
    """
    enable_debug_logging(debug, otherwise_disable_stderr=True)
    publish = validate_publish_url(publish)

    check_categories = _parse_enum_csv(
        checks,
        CheckCategory,
        "--checks",
        "categories",
        aliases=CHECK_CATEGORY_ALIASES,
        available=CHECK_CATEGORY_OPTIONS,
    )
    dimensions = _parse_enum_csv(dimension, QualityDimension, "--dimension", "dimensions")
    quality_ids = _parse_csv(quality_id, "--quality-id")
    tags = _parse_csv(tag, "--tag")
    parsed_filters = _parse_filters(filters)
    if filter is not None and parsed_filters is not None:
        console.print("[red]Use either --filter or --filters, not both.[/red]")
        raise typer.Exit(code=1)

    output_format = resolve_output_format(output_format, output)

    console.print(f"Testing {location}")
    if server == "all":
        server = None
    run = DataContract(
        config=cli_config(),
        data_contract_file=location,
        schema_location=schema,
        publish_test_results=publish_test_results,
        publish_url=publish,
        server=server,
        schema_name=schema_name,
        ssl_verification=ssl_verification,
        check_categories=check_categories,
        dimensions=dimensions,
        quality_ids=quality_ids,
        tags=tags,
        inline_references=inline_references,
        include_failed_samples=include_failed_samples,
        filter=filter,
        filters=parsed_filters,
        metadata_only=metadata_only,
        dry_run=dry_run,
    ).test()
    if logs:
        _print_logs(run)
    try:
        data_contract = resolve_data_contract(location, schema_location=schema, config=cli_config())
    except Exception:
        data_contract = None
    try:
        write_test_result(run, console, output_format, output, data_contract)
    finally:
        # Publish messages are otherwise only logged, which is suppressed without --debug.
        if run.publish_succeeded is False:
            _print_publish_failure(run)
    if run.publish_succeeded is False:
        raise typer.Exit(code=1)
