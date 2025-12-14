
from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject

from datacontract.export.exporter import Exporter, _check_schema_name_for_export, _determine_sql_server_type
from datacontract.export.sql_type_converter import convert_to_sql_type


class SqlExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> str:
        server_type = _determine_sql_server_type(
            data_contract,
            sql_server_type,
        )
        return to_sql_ddl(data_contract, server_type, export_args.get("server"))


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
            columns.append(prop.name)

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
    data_contract: OpenDataContractStandard, server_type: str = "snowflake", server: str = None
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
        if srv.type == "snowflake":
            server_type = "snowflake"
            break
        if srv.type == "postgres":
            server_type = "postgres"
            break
        if srv.type == "databricks":
            server_type = "databricks"
            if srv.catalog is not None and srv.schema_ is not None:
                table_prefix = srv.catalog + "." + srv.schema_ + "."
            break
        if srv.type == server_type:
            break

    result = ""
    result += f"-- Data Contract: {data_contract.id}\n"
    result += f"-- SQL Dialect: {server_type}\n"

    for schema_obj in data_contract.schema_:
        result += _to_sql_table(table_prefix + schema_obj.name, schema_obj, server_type)

    return result.strip()


def _to_sql_table(model_name: str, model: SchemaObject, server_type: str = "snowflake") -> str:
    if server_type == "databricks":
        # Databricks recommends to use the CREATE OR REPLACE statement for unity managed tables
        # https://docs.databricks.com/en/sql/language-manual/sql-ref-syntax-ddl-create-table-using.html
        result = f"CREATE OR REPLACE TABLE {model_name} (\n"
    else:
        result = f"CREATE TABLE {model_name} (\n"

    properties = model.properties or []
    fields = len(properties)
    current_field_index = 1

    for prop in properties:
        type_str = convert_to_sql_type(prop, server_type)
        result += f"  {prop.name} {type_str}"
        if prop.required:
            result += " not null"
        if prop.primaryKey:
            result += " primary key"
        if server_type == "databricks" and prop.description is not None:
            result += f' COMMENT "{_escape(prop.description)}"'
        if server_type == "snowflake" and prop.description is not None:
            result += f" COMMENT '{_escape(prop.description)}'"
        if current_field_index < fields:
            result += ","
        result += "\n"
        current_field_index += 1
    result += ")"
    if server_type == "databricks" and model.description is not None:
        result += f' COMMENT "{_escape(model.description)}"'
    if server_type == "snowflake" and model.description is not None:
        result += f" COMMENT='{_escape(model.description)}'"
    result += ";\n"
    return result


def _escape(text: str | None) -> str | None:
    if text is None:
        return None
    return text.replace('"', '\\"')
