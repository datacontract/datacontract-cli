"""Create a data contract from the tables and views in a Dremio source, space or folder.

Lists the datasets of the path from ``INFORMATION_SCHEMA."TABLES"``, and reads
the column types of each from the schema of a query's results, the same types
``datacontract test`` reads back to verify physical types. ``INFORMATION_SCHEMA``
reports a list or struct column as a bare ``ARRAY`` or ``ROW``, while a query's
results name the element and field types (``ARRAY<VARCHAR>``,
``STRUCT<city VARCHAR>``), so an imported contract passes on the first run.

Every query runs in the path given as ``--schema``, so a dataset however deep in
folders is named by its name alone, and the generated server's ``schema`` is
that path.
"""

from __future__ import annotations

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

DEFAULT_PORT = 9047

_TABLES_QUERY = """
    SELECT TABLE_NAME, TABLE_TYPE
    FROM INFORMATION_SCHEMA."TABLES"
    WHERE TABLE_SCHEMA = '{schema}'
"""


class DremioImporter(Importer):
    def import_source(self, source: str, import_args: dict, config=None) -> OpenDataContractStandard:
        if source is None:
            raise DataContractException(
                type="source",
                name="dremio import source",
                reason="The host is required for the dremio import, e.g. --source localhost",
                engine="datacontract-cli",
            )
        return import_dremio(
            host=source,
            port=import_args.get("port"),
            schema=import_args.get("schema"),
            tables=import_args.get("dremio_table"),
            config=config,
        )


def import_dremio(
    host: str,
    schema: Optional[str],
    port: Optional[int] = None,
    tables: Optional[List[str]] = None,
    config=None,
) -> OpenDataContractStandard:
    if not schema or not schema.strip():
        raise DataContractException(
            type="source",
            name="dremio import schema",
            reason="The path of the source, space or folder is required for the dremio import, "
            "e.g. --schema lake.sales.marts",
            engine="datacontract-cli",
        )

    from datacontract.engines.ibis.connections.dremio import split_path

    path = split_path(schema)
    port = int(port) if port else DEFAULT_PORT
    server = create_server(name="dremio", server_type="dremio", host=host, port=port, schema=schema.strip())

    connection = dremio_connection(server, config)
    try:
        # INFORMATION_SCHEMA writes a path's names joined by periods, unquoted.
        table_rows = _fetch(connection, _TABLES_QUERY.format(schema=_escape(".".join(path))))
        selected = _select_tables(table_rows, tables)
        if not selected:
            raise DataContractException(
                type="schema",
                result="failed",
                name="no tables found",
                reason=f"No tables or views found in '{schema}'.",
                engine="datacontract-cli",
            )
        schemas = [
            _create_schema(table, _column_types(connection, table["TABLE_NAME"]))
            for table in sorted(selected, key=lambda row: row["TABLE_NAME"].lower())
        ]
    finally:
        _close(connection)

    odcs = create_odcs()
    odcs.servers = [server]
    odcs.schema_ = schemas
    report_unmapped_types(odcs)
    return odcs


def dremio_connection(server: Server, config=None):
    """Connect exactly as `datacontract test` does, so both read the same options."""
    try:
        import ibis  # noqa: F401
        import sqlglot.dialects.dremio  # noqa: F401
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="dremio extra missing",
            reason="Install the extra datacontract-cli[dremio] to use dremio",
            engine="datacontract-cli",
            original_exception=e,
        )

    from datacontract.config import Config
    from datacontract.engines.ibis.connections.connect import _connect_dremio

    try:
        return _connect_dremio(server, None, Config.resolve(config))
    except DataContractException:
        raise
    except Exception as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="dremio connection failed",
            reason=f"Could not connect to Dremio at {server.host}:{server.port}: {e}",
            engine="datacontract-cli",
            original_exception=e,
        )


def _fetch(connection, query: str) -> List[Dict[str, Any]]:
    """Run a catalog query and return its rows as dicts keyed by column name."""
    try:
        cursor = connection.raw_sql(query)
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="dremio catalog query failed",
            reason=f"Could not read the Dremio catalog: {e}",
            engine="datacontract-cli",
            original_exception=e,
        )


def _column_types(connection, table_name: str) -> List[tuple[str, str]]:
    """The name and native type of each column, in order, from the schema of a query that returns no rows."""
    from datacontract.engines.ibis.connections.dremio import native_type

    table = '"' + table_name.replace('"', '""') + '"'
    try:
        cursor = connection.raw_sql(f"SELECT * FROM {table} LIMIT 0")
    except Exception as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="dremio column query failed",
            reason=f"Could not read the columns of '{table_name}': {e}",
            engine="datacontract-cli",
            original_exception=e,
        )
    return [(str(column["name"]), native_type(column.get("type"))) for column in cursor.schema]


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
    # Dremio resolves names regardless of case
    wanted = {table.lower() for table in tables}
    return [row for row in table_rows if row["TABLE_NAME"].lower() in wanted]


def _create_schema(table: Dict[str, Any], columns: List[tuple[str, Optional[str]]]) -> SchemaObject:
    return create_schema_object(
        name=table["TABLE_NAME"],
        physical_type="view" if "VIEW" in (table.get("TABLE_TYPE") or "").upper() else "table",
        properties=[_create_property(name, physical_type) for name, physical_type in columns] or None,
    )


def _create_property(name: str, physical_type: Optional[str]) -> SchemaProperty:
    prop = property_from_type_string(name, physical_type or "")
    if not physical_type:
        prop.physicalType = None
    return declare_nested_types_per_level(prop)
