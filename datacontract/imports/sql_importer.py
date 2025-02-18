import logging
import os

import sqlglot
from sqlglot.dialects.dialect import Dialects

from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import DataContractSpecification, Field, Model, Server
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum


class SqlImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        return import_sql(data_contract_specification, self.import_format, source, import_args)


def import_sql(
    data_contract_specification: DataContractSpecification, format: str, source: str, import_args: dict = None
) -> DataContractSpecification:
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

    server_type: str | None = to_server_type(source, dialect)
    if server_type is not None:
        data_contract_specification.servers[server_type] = Server(type=server_type)

    tables = parsed.find_all(sqlglot.expressions.Table)

    for table in tables:
        if data_contract_specification.models is None:
            data_contract_specification.models = {}

        table_name = table.this.name

        fields = {}
        for column in parsed.find_all(sqlglot.exp.ColumnDef):
            if column.parent.this.name != table_name:
                continue

            field = Field()
            col_name = column.this.name
            col_type = to_col_type(column, dialect)
            field.type = map_type_from_sql(col_type)
            col_description = get_description(column)
            field.description = col_description
            field.maxLength = get_max_length(column)
            precision, scale = get_precision_scale(column)
            field.precision = precision
            field.scale = scale
            field.primaryKey = get_primary_key(column)
            field.required = column.find(sqlglot.exp.NotNullColumnConstraint) is not None or None
            physical_type_key = to_physical_type_key(dialect)
            field.config = {
                physical_type_key: col_type,
            }

            fields[col_name] = field

        data_contract_specification.models[table_name] = Model(
            type="table",
            fields=fields,
        )

    return data_contract_specification


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


def to_physical_type_key(dialect: Dialects | None) -> str:
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


def map_type_from_sql(sql_type: str):
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
    elif sql_type_normed.startswith("int"):
        return "int"
    elif sql_type_normed.startswith("bigint"):
        return "long"
    elif sql_type_normed.startswith("tinyint"):
        return "int"
    elif sql_type_normed.startswith("smallint"):
        return "int"
    elif sql_type_normed.startswith("float"):
        return "float"
    elif sql_type_normed.startswith("decimal"):
        return "decimal"
    elif sql_type_normed.startswith("numeric"):
        return "decimal"
    elif sql_type_normed.startswith("bool"):
        return "boolean"
    elif sql_type_normed.startswith("bit"):
        return "boolean"
    elif sql_type_normed.startswith("binary"):
        return "bytes"
    elif sql_type_normed.startswith("varbinary"):
        return "bytes"
    elif sql_type_normed == "date":
        return "date"
    elif sql_type_normed == "time":
        return "string"
    elif sql_type_normed == "timestamp":
        return "timestamp_ntz"
    elif (
        sql_type_normed == "timestamptz"
        or sql_type_normed == "timestamp_tz"
        or sql_type_normed == "timestamp with time zone"
    ):
        return "timestamp_tz"
    elif sql_type_normed == "timestampntz" or sql_type_normed == "timestamp_ntz":
        return "timestamp_ntz"
    elif sql_type_normed == "smalldatetime":
        return "timestamp_ntz"
    elif sql_type_normed == "datetime":
        return "timestamp_ntz"
    elif sql_type_normed == "datetime2":
        return "timestamp_ntz"
    elif sql_type_normed == "datetimeoffset":
        return "timestamp_tz"
    elif sql_type_normed == "uniqueidentifier":  # tsql
        return "string"
    elif sql_type_normed == "json":
        return "string"
    elif sql_type_normed == "xml":  # tsql
        return "string"
    else:
        return "variant"


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
