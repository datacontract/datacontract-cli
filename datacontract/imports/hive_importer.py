"""Create a data contract from a live Hive database.

Reads ``DESCRIBE FORMATTED`` for each table. Like the ``DESCRIBE`` that
``datacontract test`` reads back to verify physical types, it reports the
complete declared type (``varchar(10)``, ``decimal(10,2)``,
``struct<city:string>``), so it is taken verbatim and an imported contract passes
on the first run. It also carries the table comment and whether it is a view.
"""

from __future__ import annotations

from typing import List, Optional

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty, Server

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_schema_object,
    create_server,
    property_from_type_string,
    report_unmapped_types,
)
from datacontract.model.exceptions import DataContractException

DEFAULT_PORT = 10000


class HiveImporter(Importer):
    def import_source(self, source: str, import_args: dict, config=None) -> OpenDataContractStandard:
        if source is None:
            raise DataContractException(
                type="source",
                name="hive import source",
                reason="The host is required for the hive import, e.g. --source localhost",
                engine="datacontract-cli",
            )
        return import_hive(
            host=source,
            port=import_args.get("port"),
            database=import_args.get("database"),
            tables=import_args.get("hive_table"),
            config=config,
        )


def import_hive(
    host: str,
    database: Optional[str],
    port: Optional[int] = None,
    tables: Optional[List[str]] = None,
    config=None,
) -> OpenDataContractStandard:
    if not database:
        raise DataContractException(
            type="source",
            name="hive import database",
            reason="The database is required for the hive import, e.g. --database default",
            engine="datacontract-cli",
        )

    port = int(port) if port else DEFAULT_PORT
    server = create_server(name="hive", server_type="hive", host=host, port=port, database=database)

    connection = hive_connection(server, config)
    try:
        table_names = [row[0] for row in _fetch(connection, f"SHOW TABLES IN {_identifier(database)}")]
        selected = _select_tables(table_names, tables)
        if not selected:
            raise DataContractException(
                type="schema",
                result="failed",
                name="no tables found",
                reason=f"No tables found in the database '{database}'.",
                engine="datacontract-cli",
            )
        schema_objects = [
            _create_schema(
                table, _fetch(connection, f"DESCRIBE FORMATTED {_identifier(database)}.{_identifier(table)}")
            )
            for table in sorted(selected)
        ]
    finally:
        connection.disconnect()

    odcs = create_odcs()
    odcs.servers = [server]
    odcs.schema_ = schema_objects
    report_unmapped_types(odcs)
    return odcs


def hive_connection(server: Server, config=None):
    """Connect exactly as `datacontract test` does, so both read the same options."""
    try:
        import ibis  # noqa: F401
        import impala  # noqa: F401
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="hive extra missing",
            reason="Install the extra datacontract-cli[hive] to use hive",
            engine="datacontract-cli",
            original_exception=e,
        )

    from datacontract.config import Config
    from datacontract.engines.ibis.connections.connect import _connect_hive

    try:
        return _connect_hive(ibis, server, Config.resolve(config))
    except Exception as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="hive connection failed",
            reason=f"Could not connect to Hive at {server.host}:{server.port}: {e}",
            engine="datacontract-cli",
            original_exception=e,
        )


def _fetch(connection, statement: str) -> list:
    try:
        cursor = connection.raw_sql(statement)
        try:
            return cursor.fetchall()
        finally:
            cursor.close()
    except Exception as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="hive catalog query failed",
            reason=f"Could not read the Hive catalog: {e}",
            engine="datacontract-cli",
            original_exception=e,
        )


def _identifier(value: str) -> str:
    return "`" + value.replace("`", "``") + "`"


def _select_tables(table_names: List[str], tables: Optional[List[str]]) -> List[str]:
    if not tables:
        return table_names
    # Hive lower-cases table names
    wanted = {table.lower() for table in tables}
    return [name for name in table_names if name.lower() in wanted]


def _create_schema(table: str, describe_rows: list) -> SchemaObject:
    """Read the sections of ``DESCRIBE FORMATTED``: the columns, the partition
    columns, which Hive lists only in their own section, and the table details."""
    properties = []
    section = "columns"
    table_type = description = None
    in_table_parameters = False
    for row in describe_rows:
        first = (row[0] or "").strip()
        second = row[1].strip() if len(row) > 1 and row[1] is not None else None
        third = row[2].strip() if len(row) > 2 and row[2] is not None else None
        if first.startswith("#"):
            header = first.lower()
            if header.startswith("# partition information"):
                section = "partition"
            elif header.startswith("# detailed table information"):
                section = "details"
            elif header != "# col_name":
                section = "other"
            continue
        if section in ("columns", "partition"):
            if first and second:
                properties.append(_create_property(first, second, third))
        elif section == "details":
            if first == "Table Type:":
                table_type = second
            elif first:
                in_table_parameters = first == "Table Parameters:"
            elif in_table_parameters and second == "comment" and third:
                description = third
    return create_schema_object(
        name=table,
        physical_type="view" if table_type in ("VIRTUAL_VIEW", "MATERIALIZED_VIEW") else "table",
        description=description,
        properties=properties or None,
    )


def _create_property(name: str, physical_type: str, comment: Optional[str]) -> SchemaProperty:
    prop = property_from_type_string(name, physical_type)
    if comment and comment.strip():
        prop.description = comment.strip()
    return prop
