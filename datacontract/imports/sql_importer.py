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
        return import_sql(self.import_format, source, import_args)


def import_sql(format: str, source: str, import_args: dict = None) -> OpenDataContractStandard:
    sql = read_file(source)
    dialect = to_dialect(import_args) or None

    parsed = None

    try:
        parsed = sqlglot.parse_one(sql=sql, read=dialect)

        tables = parsed.find_all(sqlglot.expressions.Table)

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
        odcs.servers = [create_server(name=server_type, server_type=server_type)]

    tables = parsed.find_all(sqlglot.expressions.Table)

    for table in tables:
        table_name = table.this.name
        properties = []

        primary_key_position = 1
        for column in parsed.find_all(sqlglot.exp.ColumnDef):
            if column.parent.this.name != table_name:
                continue

            col_name = column.this.name
            col_type = to_col_type(column, dialect)
            logical_type = map_type_from_sql(col_type)
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
                primary_key=is_primary_key,
                primary_key_position=primary_key_position if is_primary_key else None,
                required=is_required if is_required else None,
                tags=tags,
            )

            if is_primary_key:
                primary_key_position += 1

            properties.append(prop)

        table_comment_property = parsed.find(sqlglot.expressions.SchemaCommentProperty)

        if table_comment_property:
            table_description = table_comment_property.this.this

        prop = parsed.find(sqlglot.expressions.Properties)
        if prop:
            tags = prop.find(sqlglot.expressions.Tags)
            if tags:
                tag_enum = tags.find(sqlglot.expressions.Property)
                table_tags = [str(t) for t in tag_enum]

        schema_obj = create_schema_object(
            name=table_name,
            physical_type="table",
            description=table_description if table_comment_property else None,
            tags=table_tags if tags else None,
            properties=properties,
        )
        odcs.schema_.append(schema_obj)

    return odcs


def map_physical_type(column, dialect) -> str | None:
    autoincrement = ""
    if column.get("autoincrement") and dialect == Dialects.SNOWFLAKE:
        autoincrement = " AUTOINCREMENT" + " START " + str(column.get("start")) if column.get("start") else ""
        autoincrement += " INCREMENT " + str(column.get("increment")) if column.get("increment") else ""
        autoincrement += " NOORDER" if not column.get("increment_order") else ""
    elif column.get("autoincrement"):
        autoincrement = " IDENTITY"

    if column.get("size") and isinstance(column.get("size"), tuple):
        return (
            column.get("type")
            + "("
            + str(column.get("size")[0])
            + ","
            + str(column.get("size")[1])
            + ")"
            + autoincrement
        )
    elif column.get("size"):
        return column.get("type") + "(" + str(column.get("size")) + ")" + autoincrement
    else:
        return column.get("type") + autoincrement


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
    return "None"


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


def get_tags(column: sqlglot.expressions.ColumnDef) -> str | None:
    tags = column.find(sqlglot.expressions.Tags)
    if tags:
        tag_enum = tags.find(sqlglot.expressions.Property)
        return [str(t) for t in tag_enum]
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


def map_type_from_sql(sql_type: str) -> str | None:
    """Map SQL type to ODCS logical type."""
    if sql_type is None:
        return None

    sql_type_normed = sql_type.lower().strip()

    if sql_type_normed.startswith("varchar"):
        return "string"
    elif sql_type_normed.startswith("char"):
        return "string"
    elif sql_type_normed.startswith("string"):
        return "string"
    elif sql_type_normed.startswith("nchar"):
        return "string"
    elif sql_type_normed.startswith("text"):
        return "string"
    elif sql_type_normed.startswith("nvarchar"):
        return "string"
    elif sql_type_normed.startswith("ntext"):
        return "string"
    elif sql_type_normed.endswith("integer"):
        return "integer"
    elif sql_type_normed.endswith("int"):  # covers int, bigint, smallint, tinyint
        return "integer"
    elif sql_type_normed.startswith("float") or sql_type_normed.startswith("double") or sql_type_normed == "real":
        return "number"
    elif sql_type_normed.startswith("number"):
        return "number"
    elif sql_type_normed.startswith("numeric"):
        return "number"
    elif sql_type_normed.startswith("decimal"):
        return "number"
    elif sql_type_normed.startswith("money"):
        return "number"
    elif sql_type_normed.startswith("bool"):
        return "boolean"
    elif sql_type_normed.startswith("bit"):
        return "boolean"
    elif sql_type_normed.startswith("binary"):
        return "object"
    elif sql_type_normed.startswith("varbinary"):
        return "object"
    elif sql_type_normed.startswith("raw"):
        return "array"
    elif sql_type_normed == "blob" or sql_type_normed == "bfile":
        return "array"
    elif sql_type_normed == "date":
        return "date"
    elif sql_type_normed == "time":
        return "string"
    elif sql_type_normed.startswith("timestamp"):
        return "timestamp"
    elif sql_type_normed == "smalldatetime":
        return "date"
    elif sql_type_normed.startswith("datetime"):  # tsql datatime2
        return "date"
    elif sql_type_normed == "uniqueidentifier":  # tsql
        return "string"
    elif sql_type_normed == "json":
        return "object"
    elif sql_type_normed == "xml":  # tsql
        return "string"
    elif sql_type_normed.startswith("number"):
        return "number"
    elif sql_type_normed == "clob" or sql_type_normed == "nclob":
        return "string"
    else:
        return "object"


def remove_variable_tokens(sql_script: str) -> str:
    ## to cleanse sql statement's script token like $(...) in sqlcmd for T-SQL langage,  ${...} for liquibase,  {{}} as Jinja
    ## https://learn.microsoft.com/en-us/sql/tools/sqlcmd/sqlcmd-use-scripting-variables?view=sql-server-ver17#b-use-the-setvar-command-interactively
    ## https://docs.liquibase.com/concepts/changelogs/property-substitution.html
    ## https://docs.getdbt.com/guides/using-jinja?step=1
    return re.sub(r"\$\((\w+)\)|\$\{(\w+)\}|\{\{(\w+)\}\}", r"\1", sql_script)


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
