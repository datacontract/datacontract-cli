import logging
import os
import re
from enum import Enum

import sqlglot
from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty
from sqlglot.dialects.dialect import Dialects

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
    create_server,
    property_from_type_string,
)
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum


class SqlDialect(str, Enum):
    postgres = "postgres"
    tsql = "tsql"
    sqlserver = "sqlserver"
    bigquery = "bigquery"
    snowflake = "snowflake"
    databricks = "databricks"
    spark = "spark"
    duckdb = "duckdb"
    oracle = "oracle"
    mysql = "mysql"
    redshift = "redshift"


class SqlImporter(Importer):
    def import_source(self, source: str, import_args: dict) -> OpenDataContractStandard:
        return import_sql(source, import_args)


def import_sql(source: str, import_args: dict = None) -> OpenDataContractStandard:
    sql, variables = read_file(source)
    dialect = to_dialect(import_args)

    try:
        # not parse_one: sqlglot below 29 gives it only the first statement of a script
        statements = [s for s in sqlglot.parse(sql=sql, read=dialect) if s is not None]
    except Exception as e:
        logging.error(f"Error sqlglot SQL: {str(e)}")
        raise DataContractException(
            type="import",
            name=f"Reading source from {source}",
            reason=f"Error parsing SQL: {str(e)}",
            engine="datacontract-cli",
            result=ResultEnum.error,
        )

    odcs = create_odcs()
    odcs.schema_ = []

    server_type = to_server_type(source, dialect)
    if server_type is not None:
        server_defaults = get_server_defaults(server_type)
        location = get_created_location(statements, server_type, variables)
        server_defaults.update(location)
        odcs.servers = [create_server(name=server_type, server_type=server_type, **server_defaults)]
        placeholders = ", ".join(field for field in server_defaults if field not in location)
        logging.warning(
            f"SQL import generated a server block with placeholder connection values. "
            f"Update the following values before use: {placeholders}"
        )

    # Only a CREATE TABLE creates one. CREATE SCHEMA carries a table node with no table name,
    # and a CTAS or CREATE VIEW carries its query sources.
    creates = [create for create in find_all(statements, sqlglot.expressions.Create) if create.kind == "TABLE"]

    for create in creates:
        table = create.this.find(sqlglot.expressions.Table)
        table_name = table.this.name
        properties = []

        primary_key_position = 1
        for column in create.find_all(sqlglot.exp.ColumnDef):
            col_name = column.this.name
            col_type = to_col_type(column, dialect)
            logical_type, format = map_type_from_sql(col_type)
            col_description = get_description(column)
            max_length = get_max_length(column)
            precision, scale = get_precision_scale(column)
            is_primary_key = get_primary_key(column)
            is_required = column.find(sqlglot.exp.NotNullColumnConstraint) is not None or None
            tags = get_tags(column)

            map_key, map_value = map_key_value_from_type(col_type) if logical_type == "map" else (None, None)

            prop = create_property(
                name=col_name,
                logical_type=logical_type,
                physical_type=col_type,
                description=col_description,
                max_length=max_length,
                precision=precision,
                scale=scale,
                format=format,
                primary_key=is_primary_key,
                primary_key_position=primary_key_position if is_primary_key else None,
                required=is_required if is_required else None,
                tags=tags,
                map_key=map_key,
                map_value=map_value,
            )

            if is_primary_key:
                primary_key_position += 1

            properties.append(prop)

        table_comment_property = find_first(statements, sqlglot.expressions.SchemaCommentProperty)

        table_description = None
        if table_comment_property:
            table_description = table_comment_property.this.this

        table_tags = None
        table_props = find_first(statements, sqlglot.expressions.Properties)
        if table_props:
            tags = table_props.find(sqlglot.expressions.Tags)
            if tags:
                table_tags = [str(t) for t in tags.expressions]

        schema_obj = create_schema_object(
            name=table_name,
            physical_type="table",
            description=table_description,
            tags=table_tags,
            properties=properties,
        )
        odcs.schema_.append(schema_obj)

    return odcs


def get_primary_key(column) -> bool | None:
    if column.find(sqlglot.exp.PrimaryKeyColumnConstraint) is not None:
        return True
    if column.find(sqlglot.exp.PrimaryKey) is not None:
        return True
    return None


def to_dialect(import_args: dict) -> Dialects | None:
    if import_args is None:
        return None
    if "dialect" not in import_args:
        return None
    dialect = import_args.get("dialect")
    if dialect is None:
        return None
    if dialect == "sqlserver":
        return Dialects.TSQL
    if dialect.upper() in Dialects.__members__:
        return Dialects[dialect.upper()]
    return None


# Server types whose qualified table names mean database.schema. Elsewhere the parts mean
# something else, such as project.dataset on BigQuery or the database alone on MySQL, and
# belong in other server fields, so their DDL is left to the placeholders.
DATABASE_SCHEMA_SERVER_TYPES = ("snowflake", "sqlserver", "postgres", "redshift")


def find_all(statements: list, *types):
    for statement in statements:
        yield from statement.find_all(*types)


def find_first(statements: list, *types):
    return next(find_all(statements, *types), None)


def get_created_location(statements: list, server_type: str, variables: set[str]) -> dict:
    """Database and schema of the created tables, when every one of them names the same."""
    if server_type not in DATABASE_SCHEMA_SERVER_TYPES:
        return {}

    locations = set()
    for create in find_all(statements, sqlglot.expressions.Create):
        if (create.kind or "").upper() != "TABLE":
            continue
        target = create.this
        if isinstance(target, sqlglot.expressions.Schema):
            target = target.this
        if isinstance(target, sqlglot.expressions.Table):
            locations.add((target.catalog, target.db))
    if len(locations) != 1:
        return {}

    catalog, db = locations.pop()
    location = {}
    if catalog and not is_templated(catalog, variables):
        location["database"] = catalog
    if db and not is_templated(db, variables):
        location["schema"] = db
    return location


def is_templated(name: str, variables: set[str]) -> bool:
    """Whether an identifier carries substituted text, so is no more usable than a placeholder.

    Substring matching keeps names like ${env}_DB out. It can also hold back a literal name
    that happens to contain a variable name, which leaves the placeholder in place.
    """
    return any(variable in name for variable in variables)


def get_server_defaults(server_type: str) -> dict:
    """Return placeholder connection fields for a given server type.

    These placeholders make it obvious to users which fields require values,
    since an empty server stub immediately fails `datacontract lint`.
    """
    port_map = {
        "postgres": 5432,
        "redshift": 5439,
        "mysql": 3306,
        "sqlserver": 1433,
        "oracle": 1521,
        "snowflake": 443,
        "databricks": 443,
    }
    schema_map = {
        "postgres": "public",
        "redshift": "public",
    }
    defaults = {
        "host": "my_host",
        "database": "my_database",
        "schema": schema_map.get(server_type, "my_schema"),
    }
    port = port_map.get(server_type)
    if port is not None:
        defaults["port"] = port
    return defaults


def to_server_type(source, dialect: Dialects | None) -> str | None:
    if dialect is None:
        return None
    dialect_map = {
        Dialects.TSQL: "sqlserver",
        Dialects.POSTGRES: "postgres",
        Dialects.BIGQUERY: "bigquery",
        Dialects.SNOWFLAKE: "snowflake",
        Dialects.REDSHIFT: "redshift",
        Dialects.ORACLE: "oracle",
        Dialects.MYSQL: "mysql",
        Dialects.DATABRICKS: "databricks",
    }
    return dialect_map.get(dialect, None)


def to_col_type(column, dialect):
    col_type_kind = column.args["kind"]
    if col_type_kind is None:
        return None

    return col_type_kind.sql(dialect)


def to_col_type_normalized(column):
    col_type = column.args["kind"].this.name
    if col_type is None:
        return None
    return col_type.lower()


def get_description(column: sqlglot.expressions.ColumnDef) -> str | None:
    if column.comments is None:
        description = column.find(sqlglot.expressions.CommentColumnConstraint)
        if description:
            return description.this.this
        else:
            return None
    return " ".join(comment.strip() for comment in column.comments)


def get_tags(column: sqlglot.expressions.ColumnDef) -> list[str] | None:
    tags = column.find(sqlglot.expressions.Tags)
    if tags:
        return [str(t) for t in tags.expressions]
    else:
        return None


def get_max_length(column: sqlglot.expressions.ColumnDef) -> int | None:
    col_type = to_col_type_normalized(column)
    if col_type is None:
        return None
    if col_type not in ["varchar", "char", "nvarchar", "nchar"]:
        return None
    col_params = list(column.args["kind"].find_all(sqlglot.expressions.DataTypeParam))
    max_length_str = None
    if len(col_params) == 0:
        return None
    if len(col_params) == 1:
        max_length_str = col_params[0].name
    if len(col_params) == 2:
        max_length_str = col_params[1].name
    if max_length_str is not None:
        return int(max_length_str) if max_length_str.isdigit() else None


def get_precision_scale(column):
    col_type = to_col_type_normalized(column)
    if col_type is None:
        return None, None
    if col_type not in ["decimal", "numeric", "float", "number"]:
        return None, None
    col_params = list(column.args["kind"].find_all(sqlglot.expressions.DataTypeParam))
    if len(col_params) == 0:
        return None, None
    if len(col_params) == 1:
        if not col_params[0].name.isdigit():
            return None, None
        precision = int(col_params[0].name)
        scale = 0
        return precision, scale
    if len(col_params) == 2:
        if not col_params[0].name.isdigit() or not col_params[1].name.isdigit():
            return None, None
        precision = int(col_params[0].name)
        scale = int(col_params[1].name)
        return precision, scale
    return None, None


def map_key_value_from_type(sql_type: str | None) -> tuple[SchemaProperty | None, SchemaProperty | None]:
    """The key and value properties of a ``map<k,v>`` / ``MAP(k, v)`` type string, or ``(None, None)``."""
    if not sql_type:
        return None, None
    prop = property_from_type_string("map", sql_type)
    if prop.map is None:
        return None, None
    return prop.map.key, prop.map.value


def map_type_from_sql(sql_type: str) -> tuple[str | None, str | None]:
    """Map SQL type to ODCS logical type and optional format.

    Returns (logicalType, format). logicalType is None for unknown or unmappable
    types, leaving the field's logicalType unset.
    The format corresponds to ODCS logicalTypeOptions.format (e.g. "binary", "uuid").
    """
    if sql_type is None:
        return ("string", None)

    sql_type_normed = sql_type.lower().strip()

    if sql_type_normed.startswith("varchar"):
        return ("string", None)
    elif sql_type_normed.startswith("char"):
        return ("string", None)
    elif sql_type_normed.startswith("string"):
        return ("string", None)
    elif sql_type_normed.startswith("nchar"):
        return ("string", None)
    elif sql_type_normed.startswith("text"):
        return ("string", None)
    elif sql_type_normed.startswith("nvarchar"):
        return ("string", None)
    elif sql_type_normed.startswith("ntext"):
        return ("string", None)
    elif sql_type_normed.endswith("int") and not sql_type_normed.endswith("point"):
        return ("integer", None)
    elif sql_type_normed.endswith("integer"):
        return ("integer", None)
    elif sql_type_normed.startswith("float"):
        return ("number", None)
    elif sql_type_normed.startswith("double"):
        return ("number", None)
    elif sql_type_normed == "real":
        return ("number", None)
    elif sql_type_normed.startswith("number"):
        return ("number", None)
    elif sql_type_normed.startswith("numeric"):
        return ("number", None)
    elif sql_type_normed.startswith("decimal"):
        return ("number", None)
    elif sql_type_normed.startswith("money"):
        return ("number", None)
    elif sql_type_normed.startswith("bool"):
        return ("boolean", None)
    elif sql_type_normed.startswith("bit"):
        return ("boolean", None)
    elif sql_type_normed.startswith("binary"):
        return ("string", "binary")
    elif sql_type_normed.startswith("varbinary"):
        return ("string", "binary")
    elif sql_type_normed.startswith("raw"):
        return ("string", "binary")
    elif sql_type_normed == "blob":
        return ("string", "binary")
    elif sql_type_normed == "bfile":
        return ("string", "binary")
    elif sql_type_normed.startswith("bytea"):
        return ("string", "binary")
    elif sql_type_normed == "image":
        return ("string", "binary")
    elif sql_type_normed == "date":
        return ("date", None)
    elif sql_type_normed == "time" or sql_type_normed.startswith("time(") or sql_type_normed.startswith("time "):
        # TIME, TIME(9), TIME WITH TIME ZONE — but not TIMESTAMP, which is checked below
        return ("time", None)
    elif sql_type_normed == "timetz":  # postgres
        return ("time", None)
    elif sql_type_normed.startswith("timestamp"):
        return ("timestamp", None)
    elif sql_type_normed == "smalldatetime":
        return ("timestamp", None)
    elif sql_type_normed.startswith("datetime"):  # tsql datetime2, datetimeoffset
        return ("timestamp", None)
    elif sql_type_normed == "uniqueidentifier":  # tsql
        return ("string", "uuid")
    elif sql_type_normed == "json":
        return ("object", None)
    elif sql_type_normed == "xml":  # tsql
        return ("string", None)
    elif sql_type_normed == "clob" or sql_type_normed == "nclob":
        return ("string", None)
    elif sql_type_normed.startswith("array"):
        return ("array", None)
    elif sql_type_normed.startswith("struct"):
        return ("object", None)
    elif sql_type_normed.startswith("map"):
        return ("map", None)
    else:
        return (None, None)


def remove_variable_tokens(sql_script: str) -> tuple[str, set[str]]:
    """Replace templating placeholders with bare variable names so sqlglot can parse the SQL.

    Returns the rewritten script and the names that came from a placeholder.
    """
    variable_pattern = re.compile(
        r"\$\((\w+)\)"  # $(var) — sqlcmd (T-SQL)
        r"|\$\{(\w+)\}"  # ${var} — Liquibase
        r"|\{\{(\w+)\}\}"  # {{var}} — Jinja / dbt
    )
    variables = set()

    def to_variable_name(match: re.Match) -> str:
        name = match.group(1) or match.group(2) or match.group(3)
        variables.add(name)
        return name

    return variable_pattern.sub(to_variable_name, sql_script), variables


def read_file(path):
    if not os.path.exists(path):
        raise DataContractException(
            type="import",
            name=f"Reading source from {path}",
            reason=f"The file '{path}' does not exist.",
            engine="datacontract-cli",
            result=ResultEnum.error,
        )
    with open(path, "r") as file:
        file_content = file.read()

    return remove_variable_tokens(file_content)
