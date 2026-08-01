"""Create a data contract from a live SQL Server schema.

Reads ``information_schema``, the same catalog ``datacontract test`` reads back
to verify physical types, so an imported contract passes on the first run
without hand-editing. The connection is opened with the shared SQL Server
helper, so the import supports every authentication mode the test path does —
SQL logins, Windows integrated auth, the Entra ID modes and ``az login``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from open_data_contract_standard.model import (
    CustomProperty,
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
)

from datacontract.config import getenv
from datacontract.engines.ibis.native_type import reconstruct_native_type
from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import create_odcs, create_property, create_schema_object, create_server
from datacontract.imports.sql_importer import map_type_from_sql
from datacontract.model.exceptions import DataContractException

DEFAULT_PORT = 1433
DEFAULT_SCHEMA = "dbo"
DEFAULT_DRIVER = "ODBC Driver 18 for SQL Server"

_TABLES_QUERY = """
    SELECT table_name, table_type
    FROM information_schema.tables
    WHERE table_schema = '{schema}'
"""

# SQL Server reports the type in parts (base type plus length / precision /
# scale). reconstruct_native_type() reassembles them exactly as the test path
# reads them back, including the -1 that means MAX, so an imported physicalType
# matches on the first `datacontract test`.
_COLUMNS_QUERY = """
    SELECT table_name, column_name, data_type, character_maximum_length,
           numeric_precision, numeric_scale, is_nullable
    FROM information_schema.columns
    WHERE table_schema = '{schema}'
    ORDER BY table_name, ordinal_position
"""

_PRIMARY_KEYS_QUERY = """
    SELECT kcu.table_name, kcu.column_name, kcu.ordinal_position
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
     AND tc.table_schema = kcu.table_schema
    WHERE tc.constraint_type = 'PRIMARY KEY'
      AND tc.table_schema = '{schema}'
    ORDER BY kcu.table_name, kcu.ordinal_position
"""


class SqlServerImporter(Importer):
    def import_source(self, source: str, import_args: dict) -> OpenDataContractStandard:
        if source is None:
            raise DataContractException(
                type="source",
                name="sqlserver import source",
                reason="The host is required for the sqlserver import, e.g. --source localhost",
                engine="datacontract",
            )
        return import_sqlserver(
            host=source,
            port=import_args.get("port"),
            database=import_args.get("database"),
            schema=import_args.get("schema"),
            tables=import_args.get("sqlserver_table"),
        )


def import_sqlserver(
    host: str,
    database: Optional[str],
    schema: Optional[str] = None,
    port: Optional[int] = None,
    tables: Optional[List[str]] = None,
) -> OpenDataContractStandard:
    if not database:
        raise DataContractException(
            type="source",
            name="sqlserver import database",
            reason="The database is required for the sqlserver import, e.g. --database mydb",
            engine="datacontract",
        )

    port = int(port) if port else DEFAULT_PORT
    schema = schema or DEFAULT_SCHEMA
    driver = getenv("DATACONTRACT_SQLSERVER_DRIVER", DEFAULT_DRIVER)
    server = create_server(
        name="production",
        server_type="sqlserver",
        host=host,
        port=port,
        database=database,
        schema=schema,
    )
    # the driver is a custom property, which is how the test path reads it back
    server.customProperties = [CustomProperty(property="driver", value=driver)]

    connection = sqlserver_connection(server)
    try:
        table_rows = _fetch(connection, _TABLES_QUERY.format(schema=_escape(schema)))
        column_rows = _fetch(connection, _COLUMNS_QUERY.format(schema=_escape(schema)))
        # A login without access to the constraint views still gets a usable
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
            reason=f"No tables found in schema '{schema}' of database '{database}'.",
            engine="datacontract",
        )

    odcs = create_odcs()
    odcs.servers = [server]
    odcs.schema_ = [
        _create_schema(table, column_rows, primary_key_rows)
        for table in sorted(selected, key=lambda row: row["table_name"].lower())
    ]
    return odcs


def sqlserver_connection(server: Server):
    """Connect exactly as `datacontract test` does, so both support the same auth modes."""
    try:
        import ibis  # noqa: F401
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="sqlserver extra missing",
            reason="Install the extra datacontract-cli[sqlserver] to use sqlserver",
            engine="datacontract",
            original_exception=e,
        )

    from datacontract.engines.ibis.connections.connect import _connect_sqlserver

    try:
        return _connect_sqlserver(ibis, server)
    except Exception as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="sqlserver connection failed",
            reason=f"Could not connect to SQL Server at {server.host}:{server.port}: {e}",
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
            name="sqlserver catalog query failed",
            reason=f"Could not read the SQL Server catalog: {e}",
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
        physical_type="view" if (table.get("table_type") or "").upper() == "VIEW" else "table",
        properties=properties or None,
    )


def _create_property(row: Dict[str, Any], primary_keys: Dict[str, int]) -> SchemaProperty:
    name = row["column_name"]
    max_length = row.get("character_maximum_length")
    precision = row.get("numeric_precision")
    scale = row.get("numeric_scale")
    physical_type = reconstruct_native_type(row.get("data_type"), max_length, precision, scale)
    logical_type, format = map_type_from_sql(physical_type)
    # Precision/scale describe the declared type of decimals only; integers also
    # report a numeric_precision, which is not part of the type.
    is_decimal = physical_type is not None and physical_type.lower().startswith(("decimal", "numeric"))

    return create_property(
        name=name,
        logical_type=logical_type,
        physical_type=physical_type,
        required=row.get("is_nullable") == "NO" or None,
        primary_key=name in primary_keys or None,
        primary_key_position=primary_keys.get(name),
        # -1 is the MAX length, which is not a bound the contract can check.
        max_length=max_length if max_length is not None and max_length >= 0 else None,
        precision=precision if is_decimal else None,
        scale=scale if is_decimal else None,
        format=format,
    )
