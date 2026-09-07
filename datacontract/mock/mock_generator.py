"""Generates mock/fake datasets from an ODCS data contract using mimesis.

For each schema (ODCS `schema[]` entry) selected for generation:

* `physicalType: table` renders SQL `INSERT` statements from the Jinja
  template in `templates/insert.sql.j2`.
* `physicalType: file` (or anything else) looks at the resolved server's
  `format` (falling back to the server `path`'s suffix) to decide whether
  to write `json`, `csv`, or `parquet`.

`relationships` (ODCS foreign keys, e.g. a property's `relationships[].to:
orders.order_id`, or a schema-level relationship) are honored: referencing
schemas are generated after the schemas they reference, and the referencing
column samples values already generated for the referenced column instead of
an unrelated random value, so the generated datasets stay joinable.
"""

import csv
import datetime
import io
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, PackageLoader
from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty, Server

from datacontract.mock import field_faker
from datacontract.mock.field_faker import FieldFaker

FILE_FORMATS = {"json", "csv", "parquet"}

logger = logging.getLogger(__name__)


@dataclass
class MockResult:
    schema_name: str
    physical_type: str
    format: str
    content: bytes | str
    suggested_filename: str


def generate_mock_data(
    data_contract: OpenDataContractStandard,
    schema_name: str = "all",
    server: Optional[str] = None,
    rows: int = 10,
    seed: Optional[int] = None,
    locale: str = "EN",
) -> list[MockResult]:
    if rows < 1:
        raise RuntimeError("`rows` must be at least 1.")

    schemas = _topological_order(_resolve_schemas(data_contract, schema_name))
    resolved_server = _resolve_server(data_contract, server)
    faker = FieldFaker(locale=locale, seed=seed)

    # schema name -> property name -> the values generated for it, so that a
    # foreign key elsewhere can sample from real, already-generated data.
    generated_values: dict[str, dict[str, list]] = {}
    warnings: list[str] = []

    results = []
    for schema_obj in schemas:
        physical_type = (schema_obj.physicalType or "table").lower()
        properties = _flat_properties(schema_obj)
        foreign_keys = _collect_foreign_keys(schema_obj)
        records, values_by_property = _generate_records(
            schema_obj.name, properties, faker, rows, foreign_keys, generated_values, warnings
        )
        generated_values[schema_obj.name] = values_by_property

        if physical_type == "file":
            file_format = _determine_file_format(resolved_server)
            content = _render_file(records, properties, file_format)
            results.append(
                MockResult(
                    schema_name=schema_obj.name,
                    physical_type=physical_type,
                    format=file_format,
                    content=content,
                    suggested_filename=f"{schema_obj.name}.{file_format}",
                )
            )
        else:
            content = _render_sql_insert(schema_obj, properties, records, resolved_server)
            results.append(
                MockResult(
                    schema_name=schema_obj.name,
                    physical_type="table",
                    format="sql",
                    content=content,
                    suggested_filename=f"{schema_obj.name}.sql",
                )
            )

    for warning in warnings:
        logger.warning(warning)

    return results


def _resolve_schemas(data_contract: OpenDataContractStandard, schema_name: str) -> list[SchemaObject]:
    if data_contract.schema_ is None or len(data_contract.schema_) == 0:
        raise RuntimeError("Mock generation requires at least one schema in the data contract.")

    if schema_name == "all":
        return list(data_contract.schema_)

    match = next((s for s in data_contract.schema_ if s.name == schema_name), None)
    if match is None:
        available = [s.name for s in data_contract.schema_]
        raise RuntimeError(f"Schema '{schema_name}' not found in the data contract. Available schemas: {available}")
    return [match]


def _resolve_server(data_contract: OpenDataContractStandard, server_name: Optional[str]) -> Optional[Server]:
    servers = data_contract.servers or []
    if not servers:
        return None
    if server_name is not None:
        match = next((s for s in servers if s.server == server_name), None)
        if match is None:
            available = [s.server for s in servers]
            raise RuntimeError(f"Server '{server_name}' not found in the data contract. Available servers: {available}")
        return match
    # No explicit server: prefer one that actually declares a file format,
    # since that is what a `physicalType: file` schema needs to pick json vs.
    # csv vs. parquet. Otherwise just use the first declared server.
    with_format = next((s for s in servers if s.format), None)
    return with_format or servers[0]


def _determine_file_format(server: Optional[Server]) -> str:
    if server is not None and server.format and server.format.lower() in FILE_FORMATS:
        return server.format.lower()
    if server is not None and server.path:
        suffix = Path(server.path).suffix.lstrip(".").lower()
        if suffix in FILE_FORMATS:
            return suffix
    return "json"


def _flat_properties(schema_obj: SchemaObject) -> list[SchemaProperty]:
    """The top-level properties of a schema; nested `properties`/`items` are not expanded."""
    return list(schema_obj.properties or [])


# ---------------------------------------------------------------------------
# Referential integrity (ODCS `relationships`)
# ---------------------------------------------------------------------------


def _as_ref(value: Any) -> Optional[tuple[str, str]]:
    """Parse a single `schema.property` relationship endpoint."""
    if isinstance(value, str) and "." in value:
        ref_schema, _, ref_property = value.partition(".")
        return ref_schema, ref_property
    return None


def _as_ref_list(value: Any) -> list[tuple[str, str]]:
    if isinstance(value, str):
        ref = _as_ref(value)
        return [ref] if ref else []
    if isinstance(value, list):
        return [ref for ref in (_as_ref(v) for v in value) if ref is not None]
    return []


def _collect_foreign_keys(schema_obj: SchemaObject) -> dict[str, tuple[str, str]]:
    """Map each property name of `schema_obj` to the `(schema, property)` it references.

    Covers the common property-level shape (`relationships: [{type: foreignKey, to:
    orders.order_id}]`, `from` implicitly being the property itself) as well as
    schema-level relationships that name both `from` and `to` explicitly (used for
    composite keys); the latter only apply to properties of `schema_obj` itself.
    """
    foreign_keys: dict[str, tuple[str, str]] = {}

    for prop in schema_obj.properties or []:
        for rel in prop.relationships or []:
            ref = _as_ref(rel.to)
            if ref is not None:
                foreign_keys[prop.name] = ref

    for rel in schema_obj.relationships or []:
        from_refs = _as_ref_list(rel.from_)
        to_refs = _as_ref_list(rel.to)
        if len(from_refs) != len(to_refs):
            continue
        for (from_schema, from_property), to_ref in zip(from_refs, to_refs):
            if from_schema == schema_obj.name:
                foreign_keys.setdefault(from_property, to_ref)

    return foreign_keys


def _topological_order(schemas: list[SchemaObject]) -> list[SchemaObject]:
    """Order schemas so a referenced schema is generated before the schema referencing it.

    Only dependencies within the selected `schemas` are considered; a foreign key
    pointing outside the selection does not affect ordering (it is handled, with a
    warning, at generation time instead). Falls back to the original relative order
    when relationships form a cycle.
    """
    by_name = {s.name: s for s in schemas}
    dependencies = {
        s.name: {
            ref_schema
            for ref_schema, _ in _collect_foreign_keys(s).values()
            if ref_schema in by_name and ref_schema != s.name
        }
        for s in schemas
    }

    ordered: list[SchemaObject] = []
    visited: set[str] = set()
    in_progress: set[str] = set()

    def visit(name: str) -> None:
        if name in visited or name in in_progress:
            return
        in_progress.add(name)
        for dependency in dependencies[name]:
            visit(dependency)
        in_progress.discard(name)
        visited.add(name)
        ordered.append(by_name[name])

    for schema_obj in schemas:
        visit(schema_obj.name)

    return ordered


def _generate_records(
    schema_name: str,
    properties: list[SchemaProperty],
    faker: FieldFaker,
    rows: int,
    foreign_keys: dict[str, tuple[str, str]],
    generated_values: dict[str, dict[str, list]],
    warnings: list[str],
) -> tuple[list[dict[str, Any]], dict[str, list]]:
    column_by_property_name = {prop.name: (prop.physicalName or prop.name) for prop in properties}
    records: list[dict[str, Any]] = []

    for row_index in range(rows):
        record = {}
        for prop in properties:
            column_name = column_by_property_name[prop.name]
            reference = foreign_keys.get(prop.name)
            if reference is None:
                record[column_name] = faker.value_for(prop, row_index)
                continue

            ref_schema, ref_property = reference
            if ref_schema == schema_name:
                # Self-reference (e.g. a manager_id pointing at the same employees
                # table): sample from the rows generated so far in this batch.
                ref_column = column_by_property_name.get(ref_property)
                pool = [r[ref_column] for r in records] if ref_column else []
            else:
                pool = generated_values.get(ref_schema, {}).get(ref_property, [])

            if pool:
                record[column_name] = faker.fk_value(pool)
            elif ref_schema == schema_name and not prop.required:
                # No prior row to reference yet (e.g. the first row of a
                # self-referencing hierarchy) and the column tolerates it: leave it unset.
                record[column_name] = None
            else:
                warning = (
                    f"Schema '{schema_name}': relationship '{prop.name}' -> '{ref_schema}.{ref_property}' has no "
                    "generated values to reference (schema not included in this run, or generated with 0 rows); "
                    "generating an unconstrained value instead."
                )
                if warning not in warnings:
                    warnings.append(warning)
                record[column_name] = faker.value_for(prop, row_index)
        records.append(record)

    values_by_property = {
        prop.name: [record[column_by_property_name[prop.name]] for record in records] for prop in properties
    }
    return records, values_by_property


# ---------------------------------------------------------------------------
# SQL DML (Jinja template)
# ---------------------------------------------------------------------------


# Normalizes the server `type` declared in the data contract to the small set of
# dialects the template branches on; anything not listed here (mysql, snowflake,
# databricks, trino, clickhouse, local, ...) needs no special identity handling
# because those engines accept explicit values for auto-increment columns as-is.
_SQL_DIALECTS = {
    "sqlserver": "sqlserver",
    "mssql": "sqlserver",
    "azuresql": "sqlserver",
    "postgres": "postgres",
    "postgresql": "postgres",
    "oracle": "oracle",
}


def _render_sql_insert(
    schema_obj: SchemaObject,
    properties: list[SchemaProperty],
    records: list[dict[str, Any]],
    server: Optional[Server] = None,
) -> str:
    env = Environment(
        loader=PackageLoader("datacontract", "templates/mock"),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("insert.sql.j2")

    table_name = schema_obj.physicalName or schema_obj.name
    columns = [prop.physicalName or prop.name for prop in properties]
    rows = [[_to_sql_literal(record[column]) for column in columns] for record in records]
    identity_columns = [prop.physicalName or prop.name for prop in properties if field_faker.is_identity_column(prop)]
    dialect = _SQL_DIALECTS.get((server.type or "").lower()) if server is not None and server.type else None

    return template.render(
        table_name=table_name,
        columns=columns,
        rows=rows,
        dialect=dialect,
        identity_columns=identity_columns,
    )


def _to_sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return f"'{value.isoformat()}'"
    return "'{}'".format(str(value).replace("'", "''"))


# ---------------------------------------------------------------------------
# File formats (json, csv, parquet)
# ---------------------------------------------------------------------------


def _render_file(records: list[dict[str, Any]], properties: list[SchemaProperty], file_format: str) -> bytes | str:
    if file_format == "json":
        return json.dumps(records, indent=2, default=_json_default, ensure_ascii=False) + "\n"
    if file_format == "csv":
        return _render_csv(records, properties)
    if file_format == "parquet":
        return _render_parquet(records, properties)
    raise RuntimeError(f"Unsupported mock file format: {file_format}. Supported formats: {sorted(FILE_FORMATS)}")


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return str(value)


def _render_csv(records: list[dict[str, Any]], properties: list[SchemaProperty]) -> str:
    fieldnames = [prop.physicalName or prop.name for prop in properties]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for record in records:
        writer.writerow({name: _to_csv_value(record[name]) for name in fieldnames})
    return buffer.getvalue()


def _to_csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return value


def _render_parquet(records: list[dict[str, Any]], properties: list[SchemaProperty]) -> bytes:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as e:
        raise RuntimeError(
            "Generating parquet mock data requires pyarrow. Install it with `pip install datacontract-cli[parquet]`."
        ) from e

    fieldnames = [prop.physicalName or prop.name for prop in properties]
    columns = {name: [record[name] for record in records] for name in fieldnames}
    table = pa.table(columns)
    buffer = io.BytesIO()
    pq.write_table(table, buffer)
    return buffer.getvalue()
