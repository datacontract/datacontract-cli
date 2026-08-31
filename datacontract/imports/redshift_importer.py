"""Create a data contract from a live Amazon Redshift schema.

Reads table and column metadata from the ``SVV_TABLES`` / ``SVV_COLUMNS``
catalog views, which cover local tables, views and external (Spectrum) tables on
both provisioned clusters and Serverless workgroups — unlike
``information_schema``, which only sees local objects.

The connection is opened with psycopg (shipped by the ``redshift`` extra) rather
than ibis: the import only reads catalog rows, and the ibis Postgres backend
would add its own introspection quirks (see ``redshift_patch``).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty

from datacontract.engines.ibis.connections.redshift_credentials import resolve_redshift_login
from datacontract.engines.ibis.connections.redshift_patch import CLIENT_ENCODING
from datacontract.engines.ibis.native_type import reconstruct_native_type
from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import create_odcs, create_property, create_schema_object, create_server
from datacontract.imports.sql_importer import map_type_from_sql
from datacontract.model.exceptions import DataContractException

DEFAULT_PORT = 5439

_TABLES_QUERY = """
    SELECT table_name, table_type, remarks
    FROM svv_tables
    WHERE table_schema = %s
"""

# Redshift reports the type in parts (base type plus length / precision / scale).
# reconstruct_native_type() reassembles them exactly as the test path reads them
# back from information_schema, so an imported physicalType matches on the first
# `datacontract test`.
_COLUMNS_QUERY = """
    SELECT table_name,
           column_name,
           data_type,
           character_maximum_length,
           numeric_precision,
           numeric_scale,
           is_nullable,
           remarks
    FROM svv_columns
    WHERE table_schema = %s
    ORDER BY table_name, ordinal_position
"""

# Redshift accepts PRIMARY KEY constraints (informational only, not enforced) and
# exposes them through information_schema for local tables.
_PRIMARY_KEYS_QUERY = """
    SELECT kcu.table_name, kcu.column_name, kcu.ordinal_position
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
     AND tc.table_schema = kcu.table_schema
    WHERE tc.constraint_type = 'PRIMARY KEY'
      AND tc.table_schema = %s
    ORDER BY kcu.table_name, kcu.ordinal_position
"""


class RedshiftImporter(Importer):
    def import_source(self, source: str, import_args: dict, config=None) -> OpenDataContractStandard:
        if source is None:
            raise DataContractException(
                type="source",
                name="redshift import source",
                reason=(
                    "The Redshift endpoint host is required for the redshift import, "
                    "e.g. --source my-workgroup.123456789012.us-east-1.redshift-serverless.amazonaws.com"
                ),
                engine="datacontract-cli",
            )
        return import_redshift_from_connector(
            host=source,
            port=import_args.get("port"),
            database=import_args.get("database"),
            schema=import_args.get("schema"),
            tables=import_args.get("redshift_table"),
            config=config,
        )


def import_redshift_from_connector(
    host: str,
    database: Optional[str],
    schema: Optional[str],
    port: Optional[int] = None,
    tables: Optional[List[str]] = None,
    config=None,
) -> OpenDataContractStandard:
    if not database:
        raise DataContractException(
            type="source",
            name="redshift import database",
            reason="The database is required for the redshift import, e.g. --database dev",
            engine="datacontract-cli",
        )
    if not schema:
        raise DataContractException(
            type="source",
            name="redshift import schema",
            reason="The schema is required for the redshift import, e.g. --schema public",
            engine="datacontract-cli",
        )

    port = int(port) if port else DEFAULT_PORT
    connection = redshift_connection(host=host, port=port, database=database, config=config)
    try:
        table_rows = _fetch(connection, _TABLES_QUERY, (schema,))
        column_rows = _fetch(connection, _COLUMNS_QUERY, (schema,))
        # A user without access to information_schema constraints still gets a
        # usable contract, just without primary keys.
        primary_key_rows = _fetch(connection, _PRIMARY_KEYS_QUERY, (schema,), optional=True)
    finally:
        connection.close()

    selected = _select_tables(table_rows, tables)
    if not selected:
        raise DataContractException(
            type="schema",
            result="failed",
            name="no tables found",
            reason=f"No tables found in schema '{schema}' of database '{database}'.",
            engine="datacontract-cli",
        )

    odcs = create_odcs()
    odcs.servers = [
        create_server(
            name="redshift",
            server_type="redshift",
            host=host,
            port=port,
            database=database,
            schema=schema,
        )
    ]
    odcs.schema_ = [
        _create_schema(table, column_rows, primary_key_rows)
        for table in sorted(selected, key=lambda row: row["table_name"].lower())
    ]
    return odcs


def redshift_connection(host: str, port: int, database: str, config=None):
    """Open a psycopg connection to Redshift using the DATACONTRACT_REDSHIFT_* env vars."""
    try:
        import psycopg
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="redshift extra missing",
            reason="Install the extra datacontract-cli[redshift] to use redshift",
            engine="datacontract-cli",
            original_exception=e,
        )

    login = resolve_redshift_login(host, database, config)
    kwargs = dict(
        host=host,
        port=port,
        dbname=database,
        user=login.user,
        password=login.password,
        client_encoding=CLIENT_ENCODING,
    )
    if login.sslmode:
        kwargs["sslmode"] = login.sslmode
    return psycopg.connect(**kwargs)


def _fetch(connection, query: str, params: tuple, optional: bool = False) -> List[Dict[str, Any]]:
    """Run a catalog query and return its rows as dicts keyed by column name."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        if optional:
            # Roll back so the failed statement doesn't poison the transaction.
            connection.rollback()
            return []
        raise DataContractException(
            type="schema",
            result="failed",
            name="redshift catalog query failed",
            reason=f"Could not read the Redshift catalog: {e}",
            engine="datacontract-cli",
            original_exception=e,
        )


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
        physical_type=_physical_type(table.get("table_type")),
        description=_clean(table.get("remarks")),
        properties=properties or None,
    )


def _create_property(row: Dict[str, Any], primary_keys: Dict[str, int]) -> SchemaProperty:
    name = row["column_name"]
    max_length = row.get("character_maximum_length")
    precision = row.get("numeric_precision")
    scale = row.get("numeric_scale")
    physical_type = reconstruct_native_type(row.get("data_type"), max_length, precision, scale)
    logical_type, format = map_type_from_sql(physical_type)
    # Precision/scale describe the declared type of decimals only; for integers
    # Redshift still reports a numeric_precision, which is not part of the type.
    is_decimal = physical_type is not None and physical_type.lower().startswith(("decimal", "numeric"))

    return create_property(
        name=name,
        logical_type=logical_type,
        physical_type=physical_type,
        description=_clean(row.get("remarks")),
        required=row.get("is_nullable") == "NO" or None,
        primary_key=name in primary_keys or None,
        primary_key_position=primary_keys.get(name),
        max_length=max_length,
        precision=precision if is_decimal else None,
        scale=scale if is_decimal else None,
        format=format,
    )


def _physical_type(table_type: Optional[str]) -> str:
    """Map an SVV_TABLES table_type ('BASE TABLE', 'VIEW', 'EXTERNAL TABLE') to ODCS.

    'BASE TABLE' becomes plain 'table', matching what the SQL and Snowflake
    imports write.
    """
    if not table_type:
        return "table"
    normalized = table_type.strip().lower()
    return normalized.removeprefix("base ") if normalized.endswith("table") else normalized


def _clean(value: Optional[str]) -> Optional[str]:
    return value.strip() if value and value.strip() else None
