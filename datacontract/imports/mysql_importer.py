"""Create a data contract from a live MySQL schema.

MySQL is reached the way ``datacontract test`` reaches it: duckdb ATTACHes the
database through its ``mysql`` extension, so the import needs no extra driver
and authenticates with the same variables. The catalog itself is read with
``mysql_query``, which runs the statement on MySQL rather than through the
scanner, so ``information_schema`` is available.

``column_type`` is taken verbatim as the physicalType — it is the full declared
type (``varchar(36)``, ``decimal(10,2)``), which is what a reader of the
contract expects to see.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty

from datacontract.config import Config
from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import create_odcs, create_property, create_schema_object, create_server
from datacontract.imports.sql_importer import map_type_from_sql
from datacontract.model.exceptions import DataContractException

DEFAULT_PORT = 3306

_TABLES_QUERY = """
    SELECT table_name, table_type, table_comment
    FROM information_schema.tables
    WHERE table_schema = '{database}'
"""

_COLUMNS_QUERY = """
    SELECT table_name, column_name, column_type, is_nullable, column_key, column_comment,
           character_maximum_length, numeric_precision, numeric_scale
    FROM information_schema.columns
    WHERE table_schema = '{database}'
    ORDER BY table_name, ordinal_position
"""


class MysqlImporter(Importer):
    def import_source(self, source: str, import_args: dict, config: "Config | None" = None) -> OpenDataContractStandard:
        if source is None:
            raise DataContractException(
                type="source",
                name="mysql import source",
                reason="The host is required for the mysql import, e.g. --source localhost",
                engine="datacontract",
            )
        return import_mysql(
            host=source,
            port=import_args.get("port"),
            database=import_args.get("database"),
            tables=import_args.get("mysql_table"),
            config=config,
        )


def import_mysql(
    host: str,
    database: Optional[str],
    port: Optional[int] = None,
    tables: Optional[List[str]] = None,
    config: Optional[Config] = None,
) -> OpenDataContractStandard:
    if not database:
        raise DataContractException(
            type="source",
            name="mysql import database",
            reason="The database is required for the mysql import, e.g. --database mydb",
            engine="datacontract",
        )

    port = int(port) if port else DEFAULT_PORT
    con = _attach(host, port, database, config)
    try:
        table_rows = _query(con, _TABLES_QUERY.format(database=_escape(database)))
        column_rows = _query(con, _COLUMNS_QUERY.format(database=_escape(database)))
    finally:
        con.close()

    selected = _select_tables(table_rows, tables)
    if not selected:
        raise DataContractException(
            type="schema",
            result="failed",
            name="no tables found",
            reason=f"No tables found in the database '{database}'.",
            engine="datacontract",
        )

    odcs = create_odcs()
    odcs.servers = [create_server(name="mysql", server_type="mysql", host=host, port=port, database=database)]
    odcs.schema_ = [
        _create_schema(table, column_rows) for table in sorted(selected, key=lambda row: row["table_name"].lower())
    ]
    return odcs


def _attach(host: str, port: int, database: str, config: Optional[Config] = None):
    config = Config.from_input(config)
    """ATTACH the database exactly as the test path does."""
    try:
        import duckdb
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="mysql extra missing",
            reason="Install the extra datacontract-cli[mysql] to use mysql",
            engine="datacontract",
            original_exception=e,
        )

    from datacontract.engines.ibis.connections.duckdb_connection import _load_extension

    user = config.require("DATACONTRACT_MYSQL_USERNAME", server_type="mysql")
    password = config.require("DATACONTRACT_MYSQL_PASSWORD", server_type="mysql")

    con = duckdb.connect()
    _load_extension(con, "mysql", "mysql")
    connection_string = _escape(f"host={host} port={port} user={user} password={password} database={database}")
    try:
        con.execute(f"ATTACH '{connection_string}' AS mysqldb (TYPE mysql)")
    except Exception as e:
        con.close()
        raise DataContractException(
            type="schema",
            result="failed",
            name="mysql connection failed",
            reason=f"Could not connect to MySQL at {host}:{port}: {e}",
            engine="datacontract",
            original_exception=e,
        )
    return con


def _query(con, sql: str) -> List[Dict[str, Any]]:
    """Run a catalog statement on MySQL itself and return decoded rows.

    The statement is escaped a second time here: it travels inside a duckdb
    string literal, which consumes one level of quoting before MySQL sees it.
    Escaping only once would hand MySQL the raw quotes.
    """
    try:
        result = con.sql(f"SELECT * FROM mysql_query('mysqldb', '{_escape(sql)}')")
        # MySQL 8 names its information_schema columns in upper case
        columns = [description[0].lower() for description in result.description]
        return [dict(zip(columns, (_decode(value) for value in row))) for row in result.fetchall()]
    except Exception as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="mysql catalog query failed",
            reason=f"Could not read the MySQL catalog: {e}",
            engine="datacontract",
            original_exception=e,
        )


def _decode(value: Any) -> Any:
    """MySQL returns catalog text as bytes through the duckdb scanner."""
    return value.decode("utf-8") if isinstance(value, (bytes, bytearray)) else value


def _escape(value: str) -> str:
    return value.replace("'", "''")


def _select_tables(table_rows: List[Dict[str, Any]], tables: Optional[List[str]]) -> List[Dict[str, Any]]:
    if not tables:
        return table_rows
    wanted = {table.lower() for table in tables}
    return [row for row in table_rows if row["table_name"].lower() in wanted]


def _create_schema(table: Dict[str, Any], column_rows: List[Dict[str, Any]]) -> SchemaObject:
    table_name = table["table_name"]
    columns = [row for row in column_rows if row["table_name"] == table_name]
    primary_keys = [row["column_name"] for row in columns if row.get("column_key") == "PRI"]
    return create_schema_object(
        name=table_name,
        physical_type="view" if (table.get("table_type") or "").upper() == "VIEW" else "table",
        description=_clean(table.get("table_comment")),
        properties=[_create_property(row, primary_keys) for row in columns] or None,
    )


# duckdb's MySQL scanner surfaces JSON columns as text, so a contract declaring
# `object` would fail its own type check on the first run. The physicalType still
# records that the column really is JSON.
_SCANNER_LOGICAL_TYPES = {"json": "string"}


def _create_property(row: Dict[str, Any], primary_keys: List[str]) -> SchemaProperty:
    name = row["column_name"]
    physical_type = row.get("column_type")
    logical_type, format = map_type_from_sql(physical_type)
    if physical_type:
        logical_type = _SCANNER_LOGICAL_TYPES.get(physical_type.lower(), logical_type)
    is_decimal = physical_type is not None and physical_type.lower().startswith(("decimal", "numeric"))

    return create_property(
        name=name,
        logical_type=logical_type,
        physical_type=physical_type,
        description=_clean(row.get("column_comment")),
        required=row.get("is_nullable") == "NO" or None,
        primary_key=name in primary_keys or None,
        primary_key_position=primary_keys.index(name) + 1 if name in primary_keys else None,
        max_length=row.get("character_maximum_length"),
        precision=row.get("numeric_precision") if is_decimal else None,
        scale=row.get("numeric_scale") if is_decimal else None,
        format=format,
    )


def _clean(value: Optional[str]) -> Optional[str]:
    return value.strip() if value and value.strip() else None
