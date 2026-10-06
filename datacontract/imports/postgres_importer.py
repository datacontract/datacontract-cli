"""Create a data contract from a live PostgreSQL schema.

Reads table and column metadata from ``information_schema``, the same catalog
``datacontract test`` reads back to verify physical types, so an imported
contract passes on the first run without hand-editing. Primary keys use
PostgreSQL catalog metadata when available, with the portable
information-schema result as a fallback. Comments come from
``pg_description`` via ``obj_description`` / ``col_description``, which
``information_schema`` does not expose.

The connection is opened with psycopg (shipped by the ``postgres`` extra)
rather than ibis: the import only reads catalog rows, so a full ibis backend
with its own introspection quirks would buy nothing.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from open_data_contract_standard.model import (
    OpenDataContractStandard,
    Relationship,
    SchemaObject,
    SchemaProperty,
)

from datacontract.config import Config
from datacontract.engines.ibis.native_type import reconstruct_native_type
from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
    create_server,
    report_unmapped_types,
)
from datacontract.imports.sql_importer import map_type_from_sql, vector_from_type
from datacontract.model.exceptions import DataContractException

DEFAULT_PORT = 5432
DEFAULT_SCHEMA = "public"

# to_regclass() yields NULL instead of raising for objects the user cannot see,
# so a missing comment never fails the whole import.
_TABLES_QUERY = """
    SELECT table_name,
           lower(replace(table_type, 'BASE ', '')) AS table_type,
           obj_description(
               to_regclass(quote_ident(table_schema) || '.' || quote_ident(table_name))
           ) AS remarks
    FROM information_schema.tables
    WHERE table_schema = %s
"""

# Postgres reports the type in parts (base type plus length / precision / scale).
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
           col_description(
               to_regclass(quote_ident(table_schema) || '.' || quote_ident(table_name)),
               ordinal_position
           ) AS remarks
    FROM information_schema.columns
    WHERE table_schema = %s
    ORDER BY table_name, ordinal_position
"""

_INFORMATION_SCHEMA_PRIMARY_KEYS_QUERY = """
    SELECT kcu.table_name, kcu.column_name, kcu.ordinal_position
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
     AND tc.table_schema = kcu.table_schema
     AND tc.table_name = kcu.table_name
    WHERE tc.constraint_type = 'PRIMARY KEY'
      AND tc.table_schema = %s
    ORDER BY kcu.table_name, kcu.ordinal_position
"""

# pg_constraint is the preferred source of primary-key metadata. The portable
# information-schema query remains a fallback when reading the catalog fails.
# conkey retains the declared order of columns in composite primary keys.
_CATALOG_PRIMARY_KEYS_QUERY = """
    SELECT relation.relname AS table_name,
           attribute.attname AS column_name,
           con.oid AS constraint_oid,
           cardinality(con.conkey) AS expected_column_count,
           key_column.ordinality AS ordinal_position
    FROM pg_catalog.pg_constraint AS con
    JOIN pg_catalog.pg_class AS relation
      ON relation.oid = con.conrelid
    JOIN pg_catalog.pg_namespace AS namespace
      ON namespace.oid = relation.relnamespace
    CROSS JOIN LATERAL unnest(con.conkey)
      WITH ORDINALITY AS key_column(attnum, ordinality)
    JOIN pg_catalog.pg_attribute AS attribute
      ON attribute.attrelid = relation.oid
     AND attribute.attnum = key_column.attnum
     AND NOT attribute.attisdropped
    WHERE con.contype = 'p'
      AND namespace.nspname = %s
    ORDER BY relation.relname, key_column.ordinality
"""

# Pairing conkey and confkey by ordinality preserves the source-to-target
# column mapping for both single-column and composite foreign keys.
_FOREIGN_KEYS_QUERY = """
    SELECT source_relation.relname AS table_name,
           source_attribute.attname AS column_name,
           target_relation.relname AS foreign_table_name,
           target_namespace.nspname AS foreign_table_schema,
           target_attribute.attname AS foreign_column_name,
           con.oid AS constraint_oid,
           cardinality(con.conkey) AS expected_column_count,
           key_column.ordinality AS ordinal_position
    FROM pg_catalog.pg_constraint AS con
    JOIN pg_catalog.pg_class AS source_relation
      ON source_relation.oid = con.conrelid
    JOIN pg_catalog.pg_namespace AS source_namespace
      ON source_namespace.oid = source_relation.relnamespace
    JOIN pg_catalog.pg_class AS target_relation
      ON target_relation.oid = con.confrelid
    JOIN pg_catalog.pg_namespace AS target_namespace
      ON target_namespace.oid = target_relation.relnamespace
    CROSS JOIN LATERAL unnest(con.conkey, con.confkey)
      WITH ORDINALITY AS key_column(source_attnum, target_attnum, ordinality)
    JOIN pg_catalog.pg_attribute AS source_attribute
      ON source_attribute.attrelid = source_relation.oid
     AND source_attribute.attnum = key_column.source_attnum
     AND NOT source_attribute.attisdropped
    JOIN pg_catalog.pg_attribute AS target_attribute
      ON target_attribute.attrelid = target_relation.oid
     AND target_attribute.attnum = key_column.target_attnum
     AND NOT target_attribute.attisdropped
    WHERE con.contype = 'f'
      AND source_namespace.nspname = %s
    ORDER BY source_relation.relname, con.oid, key_column.ordinality
"""


class PostgresImporter(Importer):
    def import_source(self, source: str, import_args: dict, config: "Config | None" = None) -> OpenDataContractStandard:
        if source is None:
            raise DataContractException(
                type="source",
                name="postgres import source",
                reason="The host is required for the postgres import, e.g. --source localhost",
                engine="datacontract-cli",
            )
        return import_postgres_from_connector(
            host=source,
            port=import_args.get("port"),
            database=import_args.get("database"),
            schema=import_args.get("schema"),
            tables=import_args.get("postgres_table"),
            config=config,
        )


def import_postgres_from_connector(
    host: str,
    database: Optional[str],
    schema: Optional[str] = None,
    port: Optional[int] = None,
    tables: Optional[List[str]] = None,
    config: Optional[Config] = None,
) -> OpenDataContractStandard:
    if not database:
        raise DataContractException(
            type="source",
            name="postgres import database",
            reason="The database is required for the postgres import, e.g. --database postgres",
            engine="datacontract-cli",
        )

    port = int(port) if port else DEFAULT_PORT
    schema = schema or DEFAULT_SCHEMA
    connection = postgres_connection(host=host, port=port, database=database, config=config)
    try:
        table_rows = _fetch(connection, _TABLES_QUERY, (schema,))
        column_rows = _fetch(connection, _COLUMNS_QUERY, (schema,))
        information_schema_primary_key_rows = _fetch(
            connection, _INFORMATION_SCHEMA_PRIMARY_KEYS_QUERY, (schema,), optional=True
        )
        catalog_primary_key_rows = _fetch(connection, _CATALOG_PRIMARY_KEYS_QUERY, (schema,), optional=True)
        primary_key_rows = (
            catalog_primary_key_rows
            if catalog_primary_key_rows is not None
            else information_schema_primary_key_rows or []
        )
        foreign_key_rows = _fetch(connection, _FOREIGN_KEYS_QUERY, (schema,), optional=True)
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
            name="postgres",
            server_type="postgres",
            host=host,
            port=port,
            database=database,
            schema=schema,
        )
    ]
    selected_table_names = {table["table_name"] for table in selected}
    selected_column_names = {
        table_name: {row["column_name"] for row in column_rows if row["table_name"] == table_name}
        for table_name in selected_table_names
    }
    if catalog_primary_key_rows is not None:
        primary_key_rows = _complete_catalog_constraint_rows(
            primary_key_rows,
            lambda row: row["column_name"] in selected_column_names.get(row["table_name"], set()),
        )
    selected_foreign_key_rows = [
        row
        for row in foreign_key_rows or []
        if row["table_name"] in selected_table_names
        and row["foreign_table_schema"] == schema
        and row["foreign_table_name"] in selected_table_names
    ]
    if foreign_key_rows is not None:
        selected_foreign_key_rows = _complete_catalog_constraint_rows(
            selected_foreign_key_rows,
            lambda row: (
                row["column_name"] in selected_column_names.get(row["table_name"], set())
                and row["foreign_column_name"] in selected_column_names.get(row["foreign_table_name"], set())
            ),
        )
    odcs.schema_ = [
        _create_schema(table, column_rows, primary_key_rows, selected_foreign_key_rows)
        for table in sorted(selected, key=lambda row: row["table_name"].lower())
    ]
    report_unmapped_types(odcs)
    return odcs


def postgres_connection(host: str, port: int, database: str, config: Optional[Config] = None):
    """Open a psycopg connection using the same DATACONTRACT_POSTGRES_* env vars as `datacontract test`."""
    config = Config.resolve(config)
    try:
        import psycopg
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="postgres extra missing",
            reason="Install the extra datacontract-cli[postgres] to use postgres",
            engine="datacontract-cli",
            original_exception=e,
        )

    return psycopg.connect(
        host=host,
        port=port,
        dbname=database,
        user=config.get_postgres_username(required=True),
        password=config.get_postgres_password(required=True),
    )


def _fetch(connection, query: str, params: tuple, optional: bool = False) -> Optional[List[Dict[str, Any]]]:
    """Run a catalog query and return its rows as dicts keyed by column name."""
    with connection.cursor() as cursor:
        try:
            cursor.execute(query, params)
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            if optional and getattr(e, "sqlstate", None) == "42501":
                # Roll back so the failed statement doesn't poison the transaction.
                connection.rollback()
                return None
            raise DataContractException(
                type="schema",
                result="failed",
                name="postgres catalog query failed",
                reason=f"Could not read the Postgres catalog: {e}",
                engine="datacontract-cli",
                original_exception=e,
            )


def _select_tables(table_rows: List[Dict[str, Any]], tables: Optional[List[str]]) -> List[Dict[str, Any]]:
    if not tables:
        return table_rows
    wanted = {table.lower() for table in tables}
    return [row for row in table_rows if row["table_name"].lower() in wanted]


def _complete_catalog_constraint_rows(
    rows: List[Dict[str, Any]], row_is_visible: Callable[[Dict[str, Any]], bool]
) -> List[Dict[str, Any]]:
    """Return only complete, ordinally valid catalog constraints with visible columns."""
    rows_by_constraint = {}
    for row in rows:
        rows_by_constraint.setdefault(row["constraint_oid"], []).append(row)

    complete_rows = []
    for constraint_rows in rows_by_constraint.values():
        expected_column_count = constraint_rows[0]["expected_column_count"]
        ordinals = {row["ordinal_position"] for row in constraint_rows}
        if (
            len(constraint_rows) == expected_column_count
            and ordinals == set(range(1, expected_column_count + 1))
            and all(row["expected_column_count"] == expected_column_count for row in constraint_rows)
            and all(row_is_visible(row) for row in constraint_rows)
        ):
            complete_rows.extend(sorted(constraint_rows, key=lambda row: row["ordinal_position"]))
    return complete_rows


def _create_schema(
    table: Dict[str, Any],
    column_rows: List[Dict[str, Any]],
    primary_key_rows: List[Dict[str, Any]],
    foreign_key_rows: List[Dict[str, Any]],
) -> SchemaObject:
    table_name = table["table_name"]
    primary_keys = {
        row["column_name"]: row["ordinal_position"] for row in primary_key_rows if row["table_name"] == table_name
    }
    relationships = {}
    schema_relationships = []
    foreign_keys_by_constraint = {}
    for row in foreign_key_rows:
        if row["table_name"] == table_name:
            foreign_keys_by_constraint.setdefault(row["constraint_oid"], []).append(row)
    for constraint_rows in foreign_keys_by_constraint.values():
        if len(constraint_rows) == 1:
            row = constraint_rows[0]
            relationships.setdefault(row["column_name"], []).append(
                Relationship(type="foreignKey", to=f"{row['foreign_table_name']}.{row['foreign_column_name']}")
            )
        else:
            schema_relationships.append(
                Relationship(
                    type="foreignKey",
                    **{
                        "from": [f"{table_name}.{row['column_name']}" for row in constraint_rows],
                        "to": [f"{row['foreign_table_name']}.{row['foreign_column_name']}" for row in constraint_rows],
                    },
                )
            )
    properties = [
        _create_property(row, primary_keys, relationships.get(row["column_name"]))
        for row in column_rows
        if row["table_name"] == table_name
    ]
    schema = create_schema_object(
        name=table_name,
        physical_type=table.get("table_type") or "table",
        description=_clean(table.get("remarks")),
        properties=properties or None,
    )
    if schema_relationships:
        schema.relationships = schema_relationships
    return schema


def _create_property(
    row: Dict[str, Any],
    primary_keys: Dict[str, int],
    relationships: Optional[List[Relationship]] = None,
) -> SchemaProperty:
    name = row["column_name"]
    max_length = row.get("character_maximum_length")
    precision = row.get("numeric_precision")
    scale = row.get("numeric_scale")
    physical_type = reconstruct_native_type(row.get("data_type"), max_length, precision, scale)
    logical_type, format = map_type_from_sql(physical_type)
    dimensions, element_type = vector_from_type(physical_type) if logical_type == "vector" else (None, None)
    # Precision/scale describe the declared type of decimals only; for integers
    # Postgres still reports a numeric_precision, which is not part of the type.
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
        dimensions=dimensions,
        element_type=element_type,
        relationships=relationships,
    )


def _clean(value: Optional[str]) -> Optional[str]:
    return value.strip() if value and value.strip() else None
