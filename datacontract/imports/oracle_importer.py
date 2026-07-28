"""Create a data contract from a live Oracle schema.

Reads ``ALL_TAB_COLUMNS``, the same catalog ``datacontract test`` reads back to
verify physical types, and applies the same rule about which types carry a
length — Oracle reports ``DATA_LENGTH`` for every column, but it is only part of
the declared type for character and raw types. An imported contract therefore
passes on the first run without hand-editing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty, Server

from datacontract.engines.ibis.native_type import oracle_char_length, reconstruct_native_type
from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import create_odcs, create_property, create_schema_object, create_server
from datacontract.imports.sql_importer import map_type_from_sql
from datacontract.model.exceptions import DataContractException

DEFAULT_PORT = 1521

# Oracle keeps object names upper case, and the owner is what other engines call
# the schema.
_TABLES_QUERY = """
    SELECT table_name, 'table' AS object_type FROM all_tables WHERE owner = '{schema}'
    UNION ALL
    SELECT view_name AS table_name, 'view' AS object_type FROM all_views WHERE owner = '{schema}'
"""

_COLUMNS_QUERY = """
    SELECT table_name, column_name, data_type, data_length, data_precision, data_scale, nullable
    FROM all_tab_columns
    WHERE owner = '{schema}'
    ORDER BY table_name, column_id
"""

_PRIMARY_KEYS_QUERY = """
    SELECT cols.table_name, cols.column_name, cols.position
    FROM all_constraints cons
    JOIN all_cons_columns cols
      ON cons.constraint_name = cols.constraint_name
     AND cons.owner = cols.owner
    WHERE cons.constraint_type = 'P'
      AND cons.owner = '{schema}'
    ORDER BY cols.table_name, cols.position
"""


class OracleImporter(Importer):
    def import_source(self, source: str, import_args: dict) -> OpenDataContractStandard:
        if source is None:
            raise DataContractException(
                type="source",
                name="oracle import source",
                reason="The host is required for the oracle import, e.g. --source localhost",
                engine="datacontract",
            )
        return import_oracle(
            host=source,
            port=import_args.get("port"),
            service_name=import_args.get("service_name"),
            schema=import_args.get("schema"),
            tables=import_args.get("oracle_table"),
        )


def import_oracle(
    host: str,
    service_name: Optional[str],
    schema: Optional[str] = None,
    port: Optional[int] = None,
    tables: Optional[List[str]] = None,
) -> OpenDataContractStandard:
    if not service_name:
        raise DataContractException(
            type="source",
            name="oracle import service name",
            reason="The service name is required for the oracle import, e.g. --service-name XEPDB1",
            engine="datacontract",
        )
    if not schema:
        raise DataContractException(
            type="source",
            name="oracle import schema",
            reason="The schema is required for the oracle import, e.g. --schema ADMIN",
            engine="datacontract",
        )

    port = int(port) if port else DEFAULT_PORT
    # Oracle stores identifiers upper case, so a lower-case --schema would match nothing
    schema = schema.upper()
    server = create_server(
        name="oracle",
        server_type="oracle",
        host=host,
        port=port,
        schema=schema,
        service_name=service_name,
    )

    connection = oracle_connection(server)
    try:
        table_rows = _fetch(connection, _TABLES_QUERY.format(schema=_escape(schema)))
        column_rows = _fetch(connection, _COLUMNS_QUERY.format(schema=_escape(schema)))
        # A user without access to the constraint views still gets a usable
        # contract, just without primary keys.
        primary_key_rows = _fetch(connection, _PRIMARY_KEYS_QUERY.format(schema=_escape(schema)), optional=True)
    finally:
        _close(connection)

    selected = _select_tables(table_rows, tables)
    if not selected:
        raise DataContractException(
            type="schema",
            result="failed",
            name="no tables found",
            reason=f"No tables found in schema '{schema}'.",
            engine="datacontract",
        )

    odcs = create_odcs()
    odcs.servers = [server]
    odcs.schema_ = [
        _create_schema(table, column_rows, primary_key_rows)
        for table in sorted(selected, key=lambda row: row["table_name"].lower())
    ]
    return odcs


def oracle_connection(server: Server):
    """Connect exactly as `datacontract test` does, including the compatibility patch."""
    try:
        import ibis  # noqa: F401
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="oracle extra missing",
            reason="Install the extra datacontract-cli[oracle] to use oracle",
            engine="datacontract",
            original_exception=e,
        )

    from datacontract.engines.ibis.connections.connect import connect_ibis
    from datacontract.model.run import Run

    try:
        return connect_ibis(Run.create_run(), None, server)
    except Exception as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="oracle connection failed",
            reason=f"Could not connect to Oracle at {server.host}:{server.port}: {e}",
            engine="datacontract",
            original_exception=e,
        )


def _fetch(connection, query: str, optional: bool = False) -> List[Dict[str, Any]]:
    """Run a catalog query and return its rows as dicts keyed by column name."""
    try:
        cursor = connection.raw_sql(query)
        columns = [description[0].lower() for description in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        if optional:
            return []
        raise DataContractException(
            type="schema",
            result="failed",
            name="oracle catalog query failed",
            reason=f"Could not read the Oracle catalog: {e}",
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


def _as_int(value: Any) -> Optional[int]:
    """Oracle returns catalog numbers as Decimal, which YAML would serialise as a
    Python-specific tag, leaving a contract no other tool could read."""
    return int(value) if value is not None else None


def _select_tables(table_rows: List[Dict[str, Any]], tables: Optional[List[str]]) -> List[Dict[str, Any]]:
    if not tables:
        return table_rows
    wanted = {table.lower() for table in tables}
    return [row for row in table_rows if row["table_name"].lower() in wanted]


def _create_schema(
    table: Dict[str, Any],
    column_rows: List[Dict[str, Any]],
    primary_key_rows: List[Dict[str, Any]],
) -> SchemaObject:
    table_name = table["table_name"]
    primary_keys = {
        row["column_name"]: index + 1
        for index, row in enumerate(row for row in primary_key_rows if row["table_name"] == table_name)
    }
    properties = [_create_property(row, primary_keys) for row in column_rows if row["table_name"] == table_name]
    return create_schema_object(
        name=table_name,
        physical_type=table.get("object_type") or "table",
        properties=properties or None,
    )


def _create_property(row: Dict[str, Any], primary_keys: Dict[str, int]) -> SchemaProperty:
    name = row["column_name"]
    data_type = row.get("data_type")
    precision = _as_int(row.get("data_precision"))
    scale = _as_int(row.get("data_scale"))
    # the same length rule the test path applies when reading this catalog back
    char_length = _as_int(oracle_char_length(data_type, row.get("data_length")))
    physical_type = reconstruct_native_type(data_type, char_length, precision, scale)
    logical_type, format = map_type_from_sql(physical_type)
    is_decimal = physical_type is not None and physical_type.lower().startswith(("decimal", "numeric", "number"))

    return create_property(
        name=name,
        logical_type=logical_type,
        physical_type=physical_type,
        required=row.get("nullable") == "N" or None,
        primary_key=name in primary_keys or None,
        primary_key_position=primary_keys.get(name),
        max_length=char_length,
        precision=precision if is_decimal else None,
        scale=scale if is_decimal else None,
        format=format,
    )
