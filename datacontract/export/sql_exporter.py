import logging

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject

from datacontract.export.exporter import Exporter, _check_schema_name_for_export, _determine_sql_server_type
from datacontract.export.sql_type_converter import convert_to_sql_type


class SqlExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> str:
        server_type = _determine_sql_server_type(
            data_contract,
            sql_server_type,
        )
        return to_sql_ddl(
            data_contract,
            server_type,
            server=export_args.get("server"),
            clickhouse_engine=export_args.get("clickhouse_engine"),
            clickhouse_order_by=export_args.get("clickhouse_order_by"),
        )


class SqlQueryExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> str:
        model_name, model_value = _check_schema_name_for_export(data_contract, schema_name, self.export_format)
        server_type = _determine_sql_server_type(data_contract, sql_server_type, export_args.get("server"))
        return to_sql_query(
            data_contract,
            model_name,
            model_value,
            server_type,
        )


def to_sql_query(
    data_contract: OpenDataContractStandard, model_name: str, model_value: SchemaObject, server_type: str = "snowflake"
) -> str:
    if data_contract is None:
        return ""
    if data_contract.schema_ is None or len(data_contract.schema_) == 0:
        return ""

    result = ""
    result += f"-- Data Contract: {data_contract.id}\n"
    result += f"-- SQL Dialect: {server_type}\n"
    result += _to_sql_query(model_name, model_value, server_type)

    return result


def _to_sql_query(model_name: str, model_value: SchemaObject, server_type: str) -> str:
    columns = []
    if model_value.properties:
        for prop in model_value.properties:
            # TODO escape SQL reserved key words, probably dependent on server type
            columns.append(prop.physicalName or prop.name)

    result = "select\n"
    current_column_index = 1
    number_of_columns = len(columns)
    for column in columns:
        result += f"    {column}"
        if current_column_index < number_of_columns:
            result += ","
        result += "\n"
        current_column_index += 1
    result += f"from {model_name}\n"
    return result


def to_sql_ddl(
    data_contract: OpenDataContractStandard,
    server_type: str = "snowflake",
    server: str = None,
    **kwargs,
) -> str:
    if data_contract is None:
        return ""
    if data_contract.schema_ is None or len(data_contract.schema_) == 0:
        return ""

    table_prefix = ""

    # Get servers list
    servers = data_contract.servers or []
    if server is not None:
        # Filter to just the requested server
        servers = [s for s in servers if s.server == server]

    for srv in servers:
        if srv.type == "databricks" and server_type == "databricks":
            if srv.catalog is not None and srv.schema_ is not None:
                table_prefix = srv.catalog + "." + srv.schema_ + "."
            break

    result = ""
    result += f"-- Data Contract: {data_contract.id}\n"
    result += f"-- SQL Dialect: {server_type}\n"

    for schema_obj in data_contract.schema_:
        result += _to_sql_table(
            table_prefix + schema_obj.name,
            schema_obj,
            server_type,
            **kwargs,
        )

    return result.strip()


def _to_sql_table(
    model_name: str,
    model: SchemaObject,
    server_type: str = "snowflake",
    **kwargs,
) -> str:
    if (model.physicalType or "").lower() == "view":
        view = _to_sql_view(model_name, model, server_type)
        if view is not None:
            return view

    if server_type == "databricks":
        # Databricks recommends to use the CREATE OR REPLACE statement for unity managed tables
        # https://docs.databricks.com/en/sql/language-manual/sql-ref-syntax-ddl-create-table-using.html
        result = f"CREATE OR REPLACE TABLE {model_name} (\n"
    elif server_type == "clickhouse":
        result = f"CREATE TABLE IF NOT EXISTS `{model_name}` (\n"
    else:
        result = f"CREATE TABLE {model_name} (\n"

    properties = model.properties or []
    pk_props = [p for p in properties if p.primaryKey]
    composite_pk = len(pk_props) > 1
    fields = len(properties)
    # When using a table-level composite PK constraint, we need an extra line for it
    total_lines = fields + (1 if composite_pk and server_type != "clickhouse" else 0)
    current_line = 1

    for prop in properties:
        type_str = convert_to_sql_type(prop, server_type)
        column_name = prop.physicalName or prop.name
        if server_type == "clickhouse":
            # ClickHouse uses ORDER BY as the sorting/primary key.
            # Inline PRIMARY KEY is not used; see _get_clickhouse_order_by.
            col = f"  `{column_name}` "
            if prop.required or type_str.startswith(("Array(", "Map(", "Tuple(")):
                col += type_str
            else:
                col += f"Nullable({type_str})"
            if prop.description is not None:
                col += f" COMMENT '{_escape(prop.description)}'"
        else:
            col = f"  {column_name} {type_str}"
            if prop.required:
                col += " not null"
            if prop.primaryKey and not composite_pk:
                col += " primary key"
            if server_type == "databricks" and prop.description is not None:
                col += f' COMMENT "{_escape(prop.description)}"'
            if server_type == "snowflake" and prop.description is not None:
                col += f" COMMENT '{_escape(prop.description)}'"
        if current_line < total_lines:
            col += ","
        col += "\n"
        result += col
        current_line += 1

    if composite_pk and server_type != "clickhouse":
        # Sort by primaryKeyPosition (treat None as infinity so un-positioned cols go last)
        sorted_pk = sorted(pk_props, key=lambda p: (p.primaryKeyPosition is None, p.primaryKeyPosition))
        pk_columns = ", ".join(p.physicalName or p.name for p in sorted_pk)
        # Use the bare table name (strip schema prefix) for the constraint name
        constraint_name = model_name.split(".")[-1]
        result += f"  CONSTRAINT pk_{constraint_name} PRIMARY KEY ({pk_columns})\n"

    result += ")"
    if server_type == "clickhouse":
        engine = kwargs.get("clickhouse_engine") or "MergeTree()"
        result += f"\nENGINE = {engine}"
        order_by = kwargs.get("clickhouse_order_by") or _get_clickhouse_order_by(pk_props)
        if order_by:
            result += f"\nORDER BY ({order_by})"
        if model.description is not None:
            result += f"\nCOMMENT '{_escape(model.description)}'"
    elif server_type == "databricks" and model.description is not None:
        result += f' COMMENT "{_escape(model.description)}"'
    elif server_type == "snowflake" and model.description is not None:
        result += f" COMMENT='{_escape(model.description)}'"
    result += ";\n"
    return result


def _to_sql_view(model_name: str, model: SchemaObject, server_type: str) -> str | None:
    """Select the properties from their transformSourceObjects, joined on the view's foreignKey relationships.

    Returns None, after a warning, when the view cannot be written: no source objects, or a source object
    that no relationship joins to the others.
    """
    properties = model.properties or []
    column_names = [prop.physicalName or prop.name for prop in properties]

    # Per property, its (source object, source column). An entry of transformSourceObjects whose last part is
    # the property's name is a column of the object before it; any other entry is an object.
    property_sources = []
    all_sources = []
    for prop, column_name in zip(properties, column_names):
        names = {n.lower() for n in (prop.name, prop.physicalName) if n}
        refs = []
        for entry in prop.transformSourceObjects or []:
            obj, _, col = entry.rpartition(".")
            refs.append((obj, col) if obj and col.lower() in names else (entry, None))
        objects = list(dict.fromkeys(obj for obj, _ in refs))
        all_sources += objects
        column = next((col for _, col in refs if col), column_name)
        property_sources.append((objects[0] if len(objects) == 1 else None, column))
    sources = list(dict.fromkeys(all_sources))
    if not sources:
        logging.getLogger(__name__).warning(
            "Schema '%s' is a view without transformSourceObjects on its properties; exporting it as a table.",
            model.name,
        )
        return None

    def resolve(ref):
        # A `table.column` reference points to the source object that is, or ends with, that table
        table, _, column = str(ref).rpartition(".")
        matches = [s for s in sources if table and (s == table or s.endswith(f".{table}"))]
        return (matches[0], column) if len(matches) == 1 else None

    def as_list(refs):
        return refs if isinstance(refs, list) else [refs]

    edges = []
    for rel in model.relationships or []:
        if (rel.type or "foreignKey") == "foreignKey" and len(as_list(rel.from_)) == len(as_list(rel.to)):
            edges += [(resolve(f), resolve(t)) for f, t in zip(as_list(rel.from_), as_list(rel.to))]
    for prop, (source, column) in zip(properties, property_sources):
        for rel in prop.relationships or []:
            if (rel.type or "foreignKey") == "foreignKey" and source is not None and len(as_list(rel.to)) == 1:
                edges.append(((source, column), resolve(as_list(rel.to)[0])))
    edges = [(a, b) for a, b in edges if a and b and a[0] != b[0]]

    # Join each further source object to the ones already joined, on every relationship between them
    joined, joins = [sources[0]], []
    while len(joined) < len(sources):
        for source in (s for s in sources if s not in joined):
            conditions = [
                (b, a) if a[0] == source else (a, b) for a, b in edges if {a[0], b[0]} - {*joined} == {source}
            ]
            if conditions:
                joined.append(source)
                joins.append((source, conditions))
                break
        else:
            logging.getLogger(__name__).warning(
                "Schema '%s' is a view whose source objects %s are not all joined by foreignKey relationships; "
                "exporting it as a table.",
                model.name,
                ", ".join(sources),
            )
            return None

    # With several source objects, columns are qualified by an alias: the object's last part, made unique
    aliases = {}
    for source in sources:
        alias = source.rpartition(".")[2]
        aliases[source] = alias if alias not in aliases.values() else f"{alias}_{len(aliases) + 1}"
    select = []
    for column_name, (source, column) in zip(column_names, property_sources):
        expression = f"{aliases[source]}.{column}" if source is not None and len(sources) > 1 else column
        select.append(expression if column == column_name else f"{expression} AS {column_name}")
    from_clause = sources[0] if len(sources) == 1 else f"{sources[0]} {aliases[sources[0]]}"
    for source, conditions in joins:
        on = " AND ".join(f"{aliases[a[0]]}.{a[1]} = {aliases[b[0]]}.{b[1]}" for a, b in conditions)
        from_clause += f"\nLEFT JOIN {source} {aliases[source]} ON {on}"

    if server_type == "sqlserver":
        result = f"CREATE OR ALTER VIEW {model_name}"
    elif server_type == "clickhouse":
        result = f"CREATE OR REPLACE VIEW `{model_name}`"
    else:
        result = f"CREATE OR REPLACE VIEW {model_name}"

    # Snowflake and Databricks take column comments in the view's column list
    if server_type in ("snowflake", "databricks"):
        quote = '"' if server_type == "databricks" else "'"
        columns = []
        for prop, column_name in zip(properties, column_names):
            if prop.description is not None:
                column_name += f" COMMENT {quote}{_escape(prop.description)}{quote}"
            columns.append(f"  {column_name}")
        result += " (\n" + ",\n".join(columns) + "\n)"
        if model.description is not None:
            separator = "=" if server_type == "snowflake" else " "
            result += f" COMMENT{separator}{quote}{_escape(model.description)}{quote}"

    result += " AS\nSELECT\n" + ",\n".join(f"  {c}" for c in select)
    result += f"\nFROM {from_clause};\n"
    return result


def _get_clickhouse_order_by(pk_props: list) -> str | None:
    """Build the ORDER BY clause for ClickHouse from primary key columns."""
    if not pk_props:
        return None
    sorted_pk = sorted(pk_props, key=lambda p: (p.primaryKeyPosition is None, p.primaryKeyPosition))
    return ", ".join(p.physicalName or p.name for p in sorted_pk)


def _escape(text: str | None) -> str | None:
    if text is None:
        return None
    return text.replace('"', '\\"')
