"""SQL importer for data contracts.

This module provides functionality to import SQL DDL statements and convert them
into OpenDataContractStandard data contract specifications.
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
            source: The source file path.
            import_args: Additional import arguments.

        Returns:
            The populated data contract specification.
        """
        return import_sql(self.import_format, source, import_args)


def import_sql(import_format: str, source: str, import_args: dict[str, str] | None = None) -> OpenDataContractStandard:
    """Import SQL into the data contract specification.

    Args:
        import_format: The type of import format (e.g. "sql").
        source: The source file path.
        import_args: Additional import arguments.

    Returns:
        The populated data contract specification.
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

    server_type = to_server_type(dialect) if dialect is not None else None
    if server_type is not None:
        odcs.servers = [create_server(name=server_type, server_type=server_type)]

    tables = parsed.find_all(Table)

    for table in tables:
        table_name = table.this.name
        properties: list[Any] = []

        primary_key_position = 1
        for column in parsed.find_all(ColumnDef):
            if column.parent is None or column.parent.this.name != table_name:
                continue

            col_type = to_col_type(column, dialect)
            is_primary_key = get_primary_key(column)

            prop = create_property(
                name=column.this.name,
                logical_type=(map_type_from_sql(col_type) if col_type is not None else "object"),
                physical_type=col_type,
                description=get_description(column),
                max_length=get_max_length(column),
                precision=get_precision_scale(column)[0],
                scale=get_precision_scale(column)[1],
                primary_key=is_primary_key,
                primary_key_position=primary_key_position if is_primary_key else None,
                required=column.find(sqlglot.exp.NotNullColumnConstraint) is not None,
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
        column: The SQLGlot column expression.

    Returns:
        True if primary key, False if not or undetermined.
    """
    return (
        column.find(sqlglot.exp.PrimaryKeyColumnConstraint) is not None
        or column.find(sqlglot.exp.PrimaryKey) is not None
    )


def to_dialect(args_dialect: str) -> Dialects | None:
    """Convert import arguments to SQLGlot dialect.

    Args:
        args_dialect: The dialect string from import arguments.

    Returns:
        The corresponding SQLGlot dialect or None if not found.
    """
    if args_dialect.lower() == "sqlserver":
        return Dialects.TSQL
    elif args_dialect.upper() in Dialects.__members__:
        return Dialects[args_dialect.upper()]
    else:
        logger.warning("Dialect '%s' not recognized, defaulting to None", args_dialect)
        return None


def to_server_type(dialect: Dialects) -> str | None:
    """Convert dialect to ODCS object server type.

    Args:
        dialect: The SQLGlot dialect.

    Returns:
        The corresponding server type or None if not found.
    """
    server_type = {
        Dialects.TSQL: "sqlserver",
        Dialects.POSTGRES: "postgres",
        Dialects.BIGQUERY: "bigquery",
        Dialects.SNOWFLAKE: "snowflake",
        Dialects.REDSHIFT: "redshift",
        Dialects.ORACLE: "oracle",
        Dialects.MYSQL: "mysql",
        Dialects.DATABRICKS: "databricks",
        Dialects.TERADATA: "teradata",
    }.get(dialect)

    if server_type is None:
        logger.warning("No server type mapping for dialect '%s', defaulting to None", dialect)
    return server_type


def to_col_type(column: ColumnDef, dialect: Dialects | None) -> str | None:
    """Convert column to SQL type string.

    Args:
        column: The SQLGlot column expression.
        dialect: The SQLGlot dialect.

    Returns:
        The SQL type string or None if not found.
    """
    col_type_kind = column.args["kind"]
    return col_type_kind.sql(dialect) if col_type_kind is not None else None


def to_col_type_normalized(column: ColumnDef) -> str | None:
    """Convert column to normalized SQL type string.

    Args:
        column: The SQLGlot column expression.

    Returns:
        The normalized SQL type string or None if not found.
    """
    col_type = column.args["kind"].this.name
    return col_type.lower() if col_type is not None else None


def get_description(column: ColumnDef) -> str | None:
    """Get the description from column comments.

    Args:
        column: The SQLGlot column expression.

    Returns:
        The description string or None if not found.
    """
    return " ".join(comment.strip() for comment in column.comments) if column.comments is not None else None


def get_max_length(column: ColumnDef) -> int | None:
    """Get the maximum length from column definition.

    Args:
        column: The SQLGlot column expression.

    Returns:
        The maximum length or None if not found.
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
        column: The SQLGlot column expression.

    Returns:
        The precision and scale or None if not found.
    """
    col_type = to_col_type_normalized(column)
    if col_type is None or col_type not in ["decimal", "numeric", "float", "number"]:
        return None, None

    col_params = list(column.args["kind"].find_all(sqlglot.expressions.DataTypeParam))

    match col_params:
        case []:
            return None, None
        case [first] if first.name.isdigit():
            return int(first.name), 0
        case [first, second] if first.name.isdigit() and second.name.isdigit():
            return int(first.name), int(second.name)
        case _:
            return None, None


def map_type_from_sql(sql_type: str) -> str:
    """Map SQL type to ODCS logical type.

    Args:
        sql_type: The SQL type string.

    Returns:
        The corresponding ODCS logical type.
    """
    sql_type_normed = sql_type.lower().strip()

    # Check exact matches first
    exact_matches: dict[str, str] = {
        "date": "date",
        "time": "string",
        "uniqueidentifier": "string",
        "json": "object",
        "xml": "string",
    }
    if sql_type_normed in exact_matches:
        return exact_matches[sql_type_normed]

    # Check prefix and set matches
    string_types = ("varchar", "char", "string", "nchar", "text", "nvarchar", "ntext")
    if sql_type_normed.startswith(string_types) or sql_type_normed in ("clob", "nclob"):
        return "string"

    if (sql_type_normed.startswith("int") and not sql_type_normed.startswith("interval")) or sql_type_normed.startswith(
        ("bigint", "tinyint", "smallint")
    ):
        return "integer"

    if sql_type_normed.startswith(("float", "double", "decimal", "numeric", "number")):
        return "number"

    if sql_type_normed.startswith(("bool", "bit")):
        return "boolean"

    binary_types = ("binary", "varbinary", "raw")
    if sql_type_normed.startswith(binary_types) or sql_type_normed in ("blob", "bfile"):
        return "array"

    datetime_types = ("datetime", "datetime2", "smalldatetime", "datetimeoffset")
    if sql_type_normed.startswith("timestamp") or sql_type_normed in datetime_types:
        return "date"

    return "object"


def read_file(path: str) -> str:
    """Read the content of a file.

    Args:
        path: The file path.

    Returns:
        The content of the file.
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
