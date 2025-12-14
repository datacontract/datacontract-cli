import logging
import os

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
    def import_source(
        self, source: str, import_args: dict
    ) -> OpenDataContractStandard:
        return import_sql(self.import_format, source, import_args)


def import_sql(
    format: str, source: str, import_args: dict = None
) -> OpenDataContractStandard:
    sql = read_file(source)
    dialect = to_dialect(import_args)

    try:
        parsed = sqlglot.parse_one(sql=sql, read=dialect)
    except Exception as e:
        logging.error(f"Error parsing SQL: {str(e)}")
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
            )

            if is_primary_key:
                primary_key_position += 1

            properties.append(prop)

        schema_obj = create_schema_object(
            name=table_name,
            physical_type="table",
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
    if dialect == "sqlserver":
        return Dialects.TSQL
    return None


def to_physical_type_key(dialect: Dialects | str | None) -> str:
    dialect_map = {
        Dialects.TSQL: "sqlserverType",
        Dialects.POSTGRES: "postgresType",
        Dialects.BIGQUERY: "bigqueryType",
        Dialects.SNOWFLAKE: "snowflakeType",
        Dialects.REDSHIFT: "redshiftType",
        Dialects.ORACLE: "oracleType",
        Dialects.MYSQL: "mysqlType",
        Dialects.DATABRICKS: "databricksType",
    }
    if isinstance(dialect, str):
        dialect = Dialects[dialect.upper()] if dialect.upper() in Dialects.__members__ else None
    return dialect_map.get(dialect, "physicalType")


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
        return None
    return " ".join(comment.strip() for comment in column.comments)


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
    elif sql_type_normed.startswith("int") and not sql_type_normed.startswith("interval"):
        return "integer"
    elif sql_type_normed.startswith("bigint"):
        return "integer"
    elif sql_type_normed.startswith("tinyint"):
        return "integer"
    elif sql_type_normed.startswith("smallint"):
        return "integer"
    elif sql_type_normed.startswith("float"):
        return "number"
    elif sql_type_normed.startswith("double"):
        return "number"
    elif sql_type_normed.startswith("decimal"):
        return "number"
    elif sql_type_normed.startswith("numeric"):
        return "number"
    elif sql_type_normed.startswith("bool"):
        return "boolean"
    elif sql_type_normed.startswith("bit"):
        return "boolean"
    elif sql_type_normed.startswith("binary"):
        return "array"
    elif sql_type_normed.startswith("varbinary"):
        return "array"
    elif sql_type_normed.startswith("raw"):
        return "array"
    elif sql_type_normed == "blob" or sql_type_normed == "bfile":
        return "array"
    elif sql_type_normed == "date":
        return "date"
    elif sql_type_normed == "time":
        return "string"
    elif sql_type_normed.startswith("timestamp"):
        return "date"
    elif sql_type_normed == "datetime" or sql_type_normed == "datetime2":
        return "date"
    elif sql_type_normed == "smalldatetime":
        return "date"
    elif sql_type_normed == "datetimeoffset":
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
    return file_content
