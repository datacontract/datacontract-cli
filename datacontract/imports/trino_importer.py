"""Create a data contract from a live Trino catalog.

Reads ``information_schema``, the same catalog ``datacontract test`` reads back
to verify physical types. Trino reports a complete type string in ``data_type``
(``varchar(36)``, ``decimal(10,2)``, ``array(varchar)``), so it is taken
verbatim and an imported contract passes on the first run.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty, Server

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import create_odcs, create_property, create_schema_object, create_server
from datacontract.imports.sql_importer import map_type_from_sql
from datacontract.model.exceptions import DataContractException

DEFAULT_PORT = 8080

_TABLES_QUERY = """
    SELECT table_name, table_type
    FROM {catalog}.information_schema.tables
    WHERE table_schema = '{schema}'
"""

_COLUMNS_QUERY = """
    SELECT table_name, column_name, data_type, is_nullable
    FROM {catalog}.information_schema.columns
    WHERE table_schema = '{schema}'
    ORDER BY table_name, ordinal_position
"""


class TrinoImporter(Importer):
    def import_source(self, source: str, import_args: dict) -> OpenDataContractStandard:
        if source is None:
            raise DataContractException(
                type="source",
                name="trino import source",
                reason="The host is required for the trino import, e.g. --source localhost",
                engine="datacontract",
            )
        return import_trino(
            host=source,
            port=import_args.get("port"),
            catalog=import_args.get("catalog"),
            schema=import_args.get("schema"),
            tables=import_args.get("trino_table"),
        )


def import_trino(
    host: str,
    catalog: Optional[str],
    schema: Optional[str] = None,
    port: Optional[int] = None,
    tables: Optional[List[str]] = None,
) -> OpenDataContractStandard:
    if not catalog:
        raise DataContractException(
            type="source",
            name="trino import catalog",
            reason="The catalog is required for the trino import, e.g. --catalog my_catalog",
            engine="datacontract",
        )
    if not schema:
        raise DataContractException(
            type="source",
            name="trino import schema",
            reason="The schema is required for the trino import, e.g. --schema my_schema",
            engine="datacontract",
        )

    port = int(port) if port else DEFAULT_PORT
    server = create_server(name="trino", server_type="trino", host=host, port=port, catalog=catalog, schema=schema)

    connection = trino_connection(server)
    try:
        table_rows = _fetch(connection, _TABLES_QUERY.format(catalog=_identifier(catalog), schema=_escape(schema)))
        column_rows = _fetch(connection, _COLUMNS_QUERY.format(catalog=_identifier(catalog), schema=_escape(schema)))
    finally:
        _close(connection)

    selected = _select_tables(table_rows, tables)
    if not selected:
        raise DataContractException(
            type="schema",
            result="failed",
            name="no tables found",
            reason=f"No tables found in schema '{schema}' of catalog '{catalog}'.",
            engine="datacontract",
        )

    odcs = create_odcs()
    odcs.servers = [server]
    odcs.schema_ = [
        _create_schema(table, column_rows) for table in sorted(selected, key=lambda row: row["table_name"].lower())
    ]
    return odcs


def trino_connection(server: Server):
    """Connect exactly as `datacontract test` does, so both support the same auth modes."""
    try:
        import ibis  # noqa: F401
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="trino extra missing",
            reason="Install the extra datacontract-cli[trino] to use trino",
            engine="datacontract",
            original_exception=e,
        )

    from datacontract.engines.ibis.connections.connect import _connect_trino

    try:
        return _connect_trino(ibis, server)
    except Exception as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="trino connection failed",
            reason=f"Could not connect to Trino at {server.host}:{server.port}: {e}",
            engine="datacontract",
            original_exception=e,
        )


def _fetch(connection, query: str) -> List[Dict[str, Any]]:
    """Run a catalog query and return its rows as dicts keyed by column name."""
    try:
        cursor = connection.raw_sql(query)
        columns = [description[0].lower() for description in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="trino catalog query failed",
            reason=f"Could not read the Trino catalog: {e}",
            engine="datacontract",
            original_exception=e,
        )


def _close(connection) -> None:
    try:
        connection.disconnect()
    except Exception:  # pragma: no cover - best effort
        pass


def _escape(value: str) -> str:
    return value.replace("'", "''")


def _identifier(value: str) -> str:
    """The catalog is an identifier, not a literal, so it is quoted rather than escaped."""
    return '"' + value.replace('"', '""') + '"'


def _select_tables(table_rows: List[Dict[str, Any]], tables: Optional[List[str]]) -> List[Dict[str, Any]]:
    if not tables:
        return table_rows
    wanted = {table.lower() for table in tables}
    return [row for row in table_rows if row["table_name"].lower() in wanted]


def _create_schema(table: Dict[str, Any], column_rows: List[Dict[str, Any]]) -> SchemaObject:
    table_name = table["table_name"]
    columns = [row for row in column_rows if row["table_name"] == table_name]
    return create_schema_object(
        name=table_name,
        physical_type="view" if "VIEW" in (table.get("table_type") or "").upper() else "table",
        properties=[_create_property(row) for row in columns] or None,
    )


def _create_property(row: Dict[str, Any]) -> SchemaProperty:
    # Trino's data_type is already the complete declared type
    physical_type = row.get("data_type")
    logical_type, format = map_type_from_sql(physical_type)
    return create_property(
        name=row["column_name"],
        logical_type=logical_type,
        physical_type=physical_type,
        required=row.get("is_nullable") in ("NO", False) or None,
        format=format,
    )
