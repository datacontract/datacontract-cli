"""SQL importer for data contracts.

This module provides functionality to import SQL DDL statements and convert them
into OpenDataContractStandard data contract specifications .
"""

import logging
import pathlib
from typing import Any

import sqlglot
from open_data_contract_standard.model import OpenDataContractStandard
from sqlglot.dialects.dialect import Dialects
from sqlglot.expressions import ColumnDef, Table

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
    create_server,
)
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum

logger = logging.getLogger(__name__)


class SqlImporter(Importer):
    """Importer for SQL DDL files."""

    def import_source(self, source: str, import_args: dict[str, str]) -> OpenDataContractStandard:
        """Import source into the data contract specification.

        Args:
            source (str): The source file path.
            import_args (dict[str, str]): Additional import arguments.

        Returns:
            OpenDataContractStandard: The populated data contract specification.
        """
        return import_sql(self.import_format, source, import_args)


def import_sql(import_format: str, source: str, import_args: dict[str, str] | None = None) -> OpenDataContractStandard:
    """Import SQL into the data contract specification.

    Args:
        import_format (str): The type of import format (e.g. "sql").
        source (str): The source file path.
        import_args (dict): Additional import arguments.

    Returns:
        OpenDataContractStandard: The populated data contract specification.
    """
    sql = read_file(source)

    dialect = None
    if import_args is not None and "dialect" in import_args:
        dialect = to_dialect(import_args["dialect"])

    try:
        parsed = sqlglot.parse_one(sql=sql, read=dialect)
    except Exception as e:
        logger.exception("Error parsing SQL")
        raise DataContractException(
            type="import",
            name=f"Reading source from {source}",
            reason=f"Error parsing SQL: {e!s}",
            engine="datacontract",
            result=ResultEnum.error,
        ) from e

    odcs = create_odcs()
    odcs.schema_ = []

    server_type = to_server_type(dialect)
    if server_type is not None:
        odcs.servers = [create_server(name=server_type, server_type=server_type)]

    tables = parsed.find_all(Table)

    for table in tables:
        table_name = table.this.name
        properties = []

        primary_key_position = 1
        for column in parsed.find_all(ColumnDef):
            if column.parent is None or column.parent.this.name != table_name:
                continue

            col_name = column.this.name
            col_type = to_col_type(column, dialect)
            logical_type = map_type_from_sql(col_type) if col_type is not None else None
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


def get_primary_key(column: ColumnDef) -> bool:
    """Determine if the column is a primary key.

    Args:
        column (ColumnDef): The SQLGlot column expression.

    Returns:
        bool: True if primary key, False if not or undetermined.
    """
    return (
        column.find(sqlglot.exp.PrimaryKeyColumnConstraint) is not None
        or column.find(sqlglot.exp.PrimaryKey) is not None
    )


def to_dialect(args_dialect: str) -> Dialects | None:
    """Convert import arguments to SQLGlot dialect.

    Args:
        args_dialect (str): The dialect string from import arguments.

    Returns:
        Dialects | None: The corresponding SQLGlot dialect or None if not found.
    """
    if args_dialect == "sqlserver":
        return Dialects.TSQL
    elif args_dialect.upper() in Dialects.__members__:
        return Dialects[args_dialect.upper()]
    else:
        logger.warning("Dialect '%s' not recognized, defaulting to None", args_dialect)
        return None


def to_physical_type_key(dialect: Dialects | str | None) -> str:
    """Convert dialect to ODCS object physical type key.

    Args:
        dialect (Dialects | str | None): The SQLGlot dialect or string representation.

    Returns:
        str: The corresponding physical type key.
    """
    dialect_map = {
        Dialects.TSQL: "sqlserverType",
        Dialects.POSTGRES: "postgresType",
        Dialects.BIGQUERY: "bigqueryType",
        Dialects.SNOWFLAKE: "snowflakeType",
        Dialects.REDSHIFT: "redshiftType",
        Dialects.ORACLE: "oracleType",
        Dialects.MYSQL: "mysqlType",
        Dialects.DATABRICKS: "databricksType",
        Dialects.TERADATA: "teradataType",
    }
    if isinstance(dialect, str):
        dialect = Dialects[dialect.upper()] if dialect.upper() in Dialects.__members__ else None
    return dialect_map.get(dialect, "physicalType")


def to_server_type(dialect: Dialects | None) -> str | None:
    """Convert dialect to ODCS object server type.

    Args:
        dialect (Dialects | None): The SQLGlot dialect.

    Returns:
        str | None: The corresponding server type or None if not found.
    """
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
        Dialects.TERADATA: "teradata",
    }
    return dialect_map.get(dialect)


def to_col_type(column: ColumnDef, dialect: Dialects | None) -> str | None:
    """Convert column to SQL type string.

    Args:
        column (ColumnDef): The SQLGlot column expression.
        dialect (Dialects | None): The SQLGlot dialect.

    Returns:
        str | None: The SQL type string or None if not found.
    """
    col_type_kind = column.args["kind"]
    return col_type_kind.sql(dialect) if col_type_kind is None else None


def to_col_type_normalized(column: ColumnDef) -> str | None:
    """Convert column to normalized SQL type string.

    Args:
        column (ColumnDef): The SQLGlot column expression.

    Returns:
        str | None: The normalized SQL type string or None if not found.
    """
    col_type = column.args["kind"].this.name
    return col_type.lower() if col_type is not None else None


def get_description(column: ColumnDef) -> str | None:
    """Get the description from column comments.

    Args:
        column (ColumnDef): The SQLGlot column expression.

    Returns:
        str | None: The description string or None if not found.
    """
    return " ".join(comment.strip() for comment in column.comments) if column.comments is not None else None


def get_max_length(column: ColumnDef) -> int | None:
    """Get the maximum length from column definition.

    Args:
        column (ColumnDef): The SQLGlot column expression.

    Returns:
        int | None: The maximum length or None if not found.
    """
    col_type = to_col_type_normalized(column)
    if col_type is None or col_type not in ["varchar", "char", "nvarchar", "nchar"]:
        return None
    col_params: list[Any] = list(column.args["kind"].find_all(sqlglot.expressions.DataTypeParam))
    max_length_str = None
    match len(col_params):
        case 0:
            return None
        case 1:
            max_length_str = col_params[0].name
        case 2:
            max_length_str = col_params[1].name

    if max_length_str is not None:
        return int(max_length_str) if max_length_str.isdigit() else None


def get_precision_scale(column: ColumnDef) -> tuple[int | None, int | None]:
    """Get the precision and scale from column definition.

    Args:
        column (ColumnDef): The SQLGlot column expression.

    Returns:
        tuple[int | None, int | None]: The precision and scale or None if not found.
    """
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


def map_type_from_sql(sql_type: str) -> str:
    """Map SQL type to ODCS logical type.

    Args:
        sql_type (str): The SQL type string.

    Returns:
        str: The corresponding ODCS logical type or None if not found.
    """
    sql_type_normed = sql_type.lower().strip()

    if (
        sql_type_normed.startswith("varchar")
        or sql_type_normed.startswith("char")
        or sql_type_normed.startswith("string")
        or sql_type_normed.startswith("nchar")
        or sql_type_normed.startswith("text")
        or sql_type_normed.startswith("nvarchar")
        or sql_type_normed.startswith("ntext")
    ):
        return "string"
    elif (
        (sql_type_normed.startswith("int") and not sql_type_normed.startswith("interval"))
        or sql_type_normed.startswith("bigint")
        or sql_type_normed.startswith("tinyint")
        or sql_type_normed.startswith("smallint")
    ):
        return "integer"
    elif (
        sql_type_normed.startswith("float")
        or sql_type_normed.startswith("double")
        or sql_type_normed.startswith("decimal")
        or sql_type_normed.startswith("numeric")
    ):
        return "number"
    elif sql_type_normed.startswith("bool") or sql_type_normed.startswith("bit"):
        return "boolean"
    elif (
        sql_type_normed.startswith("binary")
        or sql_type_normed.startswith("varbinary")
        or sql_type_normed.startswith("raw")
        or sql_type_normed == "blob"
        or sql_type_normed == "bfile"
    ):
        return "array"
    elif sql_type_normed == "date":
        return "date"
    elif sql_type_normed == "time":
        return "string"
    elif (
        sql_type_normed.startswith("timestamp")
        or sql_type_normed == "datetime"
        or sql_type_normed == "datetime2"
        or sql_type_normed == "smalldatetime"
        or sql_type_normed == "datetimeoffset"
    ):
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


def read_file(path: str) -> str:
    """Read the content of a file.

    Args:
        path (str): The file path.

    Returns:
        str: The content of the file.
    """
    if not pathlib.Path(path).exists():
        raise DataContractException(
            type="import",
            name=f"Reading source from {path}",
            reason=f"The file '{path}' does not exist.",
            engine="datacontract",
            result=ResultEnum.error,
        )
    with pathlib.Path(path).open("r") as file:
        file_content = file.read()
    if file_content.strip() == "":
        raise DataContractException(
            type="import",
            name=f"Reading source from {path}",
            reason=f"The file '{path}' is empty.",
            engine="datacontract",
            result=ResultEnum.error,
        )
    else:
        return file_content
