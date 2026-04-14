import logging
import os
import re

import sqlglot
from open_data_contract_standard.model import OpenDataContractStandard
from sqlglot.dialects.dialect import Dialects

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
    create_server,
)
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum


class SqlImporter(Importer):
    def import_source(self, source: str, import_args: dict) -> OpenDataContractStandard:
        return import_sql(source, import_args)


def import_sql(source: str, import_args: dict = None) -> OpenDataContractStandard:
    sql = read_file(source)
    dialect = to_dialect(import_args)

    try:
        parsed = sqlglot.parse_one(sql=sql, read=dialect)
    except Exception as e:
        logging.error(f"Error sqlglot SQL: {str(e)}")
        raise DataContractException(
            type="import",
            name=f"Reading source from {source}",
            reason=f"Error parsing SQL: {str(e)}",
            engine="datacontract",
            result=ResultEnum.error,
        )

    odcs = create_odcs()
    odcs.schema_ = []

    server_type = to_server_type(source, dialect)
    if server_type is not None:
        server_defaults = get_server_defaults(server_type)
        odcs.servers = [create_server(name=server_type, server_type=server_type, **server_defaults)]
        logging.warning(
            "SQL import generated a server block with placeholder connection values. "
            "Update host, port, database, and schema in the output before use."
        )

    tables = [
        t
        for t in parsed.find_all(sqlglot.expressions.Table)
        if isinstance(t.find_ancestor(sqlglot.expressions.Create), sqlglot.expressions.Create)
    ]

    for table in tables:
        table_name = table.this.name
        properties = []

        primary_key_position = 1
        for column in parsed.find_all(sqlglot.exp.ColumnDef):
            if column.parent.this.name != table_name:
                continue

            col_name = column.this.name
            col_type = to_col_type(column, dialect)
            logical_type, format = map_type_from_sql(col_type)
            col_description = get_description(column)
            max_length = get_max_length(column)
            precision, scale = get_precision_scale(column)
            is_primary_key = get_primary_key(column)
            is_required = column.find(sqlglot.exp.NotNullColumnConstraint) is not None or None
            tags = get_tags(column)

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
            )

            if is_primary_key:
                primary_key_position += 1

            properties.append(prop)

        table_comment_property = parsed.find(sqlglot.expressions.SchemaCommentProperty)

        table_description = None
        if table_comment_property:
            table_description = table_comment_property.this.this

        table_tags = None
        table_props = parsed.find(sqlglot.expressions.Properties)
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


def map_type_from_sql(sql_type: str) -> tuple[str, str | None]:
    """Map SQL type to ODCS logical type and optional format.

    Returns (logicalType, format).
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
    elif sql_type_normed == "time":
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
    else:
        return ("object", None)


def remove_variable_tokens(sql_script: str) -> str:
    """Replace templating placeholders with bare variable names so sqlglot can parse the SQL."""
    variable_pattern = re.compile(
        r"\$\((\w+)\)"  # $(var) — sqlcmd (T-SQL)
        r"|\$\{(\w+)\}"  # ${var} — Liquibase
        r"|\{\{(\w+)\}\}"  # {{var}} — Jinja / dbt
    )
    return variable_pattern.sub(lambda m: m.group(1) or m.group(2) or m.group(3), sql_script)


def read_file(path):
    if not os.path.exists(path):
        raise DataContractException(
            type="import",
            name=f"Reading source from {path}",
            reason=f"The file '{path}' does not exist.",
            engine="datacontract",
            result=ResultEnum.error,
        )
    with open(path, "r") as file:
        file_content = file.read()

    return remove_variable_tokens(file_content)
