"""Create a data contract from a live ClickHouse database.

Reads ``system.tables`` and ``system.columns``, the catalog ``datacontract test``
reads back to verify physical types. ``system.columns.type`` is the complete
declared type (``Nullable(String)``, ``Decimal(10, 2)``, ``Array(String)``), so it
is taken verbatim and an imported contract passes on the first run.

A column is required unless its type is ``Nullable``: ClickHouse stores no NULL
in any other column. The sorting key becomes the primary key, as it is what
ClickHouse calls one.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty, Server

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_schema_object,
    create_server,
    declare_nested_types_per_level,
    property_from_type_string,
    report_unmapped_types,
)
from datacontract.model.exceptions import DataContractException

DEFAULT_PORT = 8123

_VIEW_ENGINES = {"View", "MaterializedView", "LiveView", "WindowView"}

_TABLES_QUERY = """
    SELECT name, engine, comment
    FROM system.tables
    WHERE database = '{database}' AND NOT is_temporary
"""

_COLUMNS_QUERY = """
    SELECT table, name, type, comment, is_in_primary_key
    FROM system.columns
    WHERE database = '{database}'
    ORDER BY table, position
"""

# A wrapper that changes how a value is stored, not what it is.
_WRAPPER = re.compile(r"^(?:Nullable|LowCardinality)\((.*)\)$", re.S)

_LOGICAL_TYPES = {
    "string": "string",
    "fixedstring": "string",
    "enum8": "string",
    "enum16": "string",
    "ipv4": "string",
    "ipv6": "string",
    "uuid": "string",
    "bool": "boolean",
    "date": "date",
    "date32": "date",
    "datetime": "timestamp",
    "datetime64": "timestamp",
    "float32": "number",
    "float64": "number",
    "decimal": "number",
    "decimal32": "number",
    "decimal64": "number",
    "decimal128": "number",
    "decimal256": "number",
    "json": "object",
    "tuple": "object",
    "nested": "array",
    "array": "array",
    "map": "map",
}


class ClickHouseImporter(Importer):
    def import_source(self, source: str, import_args: dict, config=None) -> OpenDataContractStandard:
        if source is None:
            raise DataContractException(
                type="source",
                name="clickhouse import source",
                reason="The host is required for the clickhouse import, e.g. --source localhost",
                engine="datacontract-cli",
            )
        return import_clickhouse(
            host=source,
            port=import_args.get("port"),
            database=import_args.get("database"),
            tables=import_args.get("clickhouse_table"),
            config=config,
        )


def import_clickhouse(
    host: str,
    database: Optional[str],
    port: Optional[int] = None,
    tables: Optional[List[str]] = None,
    config=None,
) -> OpenDataContractStandard:
    if not database:
        raise DataContractException(
            type="source",
            name="clickhouse import database",
            reason="The database is required for the clickhouse import, e.g. --database default",
            engine="datacontract-cli",
        )

    port = int(port) if port else DEFAULT_PORT
    server = create_server(name="clickhouse", server_type="clickhouse", host=host, port=port, database=database)

    connection = clickhouse_connection(server, config)
    try:
        table_rows = _fetch(connection, _TABLES_QUERY.format(database=_escape(database)))
        column_rows = _fetch(connection, _COLUMNS_QUERY.format(database=_escape(database)))
    finally:
        connection.disconnect()

    selected = _select_tables(table_rows, tables)
    if not selected:
        raise DataContractException(
            type="schema",
            result="failed",
            name="no tables found",
            reason=f"No tables found in the database '{database}'.",
            engine="datacontract-cli",
        )

    odcs = create_odcs()
    odcs.servers = [server]
    odcs.schema_ = [_create_schema(table, column_rows) for table in sorted(selected, key=lambda row: row["name"])]
    report_unmapped_types(odcs)
    return odcs


def clickhouse_connection(server: Server, config=None):
    """Connect exactly as `datacontract test` does, so both read the same options."""
    try:
        import clickhouse_connect  # noqa: F401
        import ibis  # noqa: F401
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="clickhouse extra missing",
            reason="Install the extra datacontract-cli[clickhouse] to use clickhouse",
            engine="datacontract-cli",
            original_exception=e,
        )

    from datacontract.config import Config
    from datacontract.engines.ibis.connections.connect import _connect_clickhouse

    try:
        return _connect_clickhouse(ibis, server, None, Config.resolve(config))
    except Exception as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="clickhouse connection failed",
            reason=f"Could not connect to ClickHouse at {server.host}:{server.port}: {e}",
            engine="datacontract-cli",
            original_exception=e,
        )


def _fetch(connection, query: str) -> List[Dict[str, Any]]:
    try:
        result = connection.con.query(query)
        return [dict(zip(result.column_names, row)) for row in result.result_rows]
    except Exception as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="clickhouse catalog query failed",
            reason=f"Could not read the ClickHouse catalog: {e}",
            engine="datacontract-cli",
            original_exception=e,
        )


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _select_tables(table_rows: List[Dict[str, Any]], tables: Optional[List[str]]) -> List[Dict[str, Any]]:
    if not tables:
        return table_rows
    # ClickHouse table names are case-sensitive
    return [row for row in table_rows if row["name"] in tables]


def _create_schema(table: Dict[str, Any], column_rows: List[Dict[str, Any]]) -> SchemaObject:
    table_name = table["name"]
    columns = [row for row in column_rows if row["table"] == table_name]
    primary_keys = [row["name"] for row in columns if row.get("is_in_primary_key")]
    return create_schema_object(
        name=table_name,
        physical_type="view" if table.get("engine") in _VIEW_ENGINES else "table",
        description=_clean(table.get("comment")),
        properties=[_create_property(row, primary_keys) for row in columns] or None,
    )


def _create_property(row: Dict[str, Any], primary_keys: List[str]) -> SchemaProperty:
    name, physical_type = row["name"], row["type"]
    prop = property_from_type_string(name, unwrap_clickhouse_type(physical_type))
    _apply_logical_types(prop)
    prop.physicalType = physical_type
    declare_nested_types_per_level(prop)
    prop.required = is_clickhouse_required(physical_type) or None
    if name in primary_keys:
        prop.primaryKey = True
        prop.primaryKeyPosition = primary_keys.index(name) + 1
    description = _clean(row.get("comment"))
    if description:
        prop.description = description
    return prop


def unwrap_clickhouse_type(type_string: str) -> str:
    """``LowCardinality(Nullable(String))`` -> ``String``."""
    while match := _WRAPPER.match(type_string.strip()):
        type_string = match.group(1)
    return type_string.strip()


def is_clickhouse_required(type_string: str) -> bool:
    """ClickHouse stores no NULL in a column whose type is not ``Nullable``."""
    type_string = type_string.strip()
    if match := re.match(r"^LowCardinality\((.*)\)$", type_string, re.S):
        type_string = match.group(1).strip()
    return not type_string.startswith("Nullable(")


def map_clickhouse_type(type_string: str) -> Optional[str]:
    """The ODCS logicalType of a ClickHouse type, which spells its types its own way
    (``Int32``, ``UInt64``, ``Date32``) where the generic SQL mapping does not know them."""
    base = unwrap_clickhouse_type(type_string).split("(", 1)[0].strip().lower()
    if re.fullmatch(r"u?int\d+", base):
        return "integer"
    return _LOGICAL_TYPES.get(base)


def _apply_logical_types(prop: SchemaProperty) -> None:
    """Map the property and its nested items, fields, keys and values."""
    if prop.physicalType:
        prop.logicalType = map_clickhouse_type(prop.physicalType) or prop.logicalType
    for child in prop.properties or []:
        _apply_logical_types(child)
    if prop.items:
        _apply_logical_types(prop.items)
    if prop.map:
        for side in (prop.map.key, prop.map.value):
            if side:
                _apply_logical_types(side)


def _clean(value: Optional[str]) -> Optional[str]:
    return value.strip() if value and value.strip() else None
