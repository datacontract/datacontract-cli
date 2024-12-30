from datacontract.export.exporter import Exporter, _check_models_for_export, _determine_sql_server_type
from datacontract.export.sql_type_converter import convert_to_sql_type
from datacontract.model.data_contract_specification import DataContractSpecification, Model


class SqlExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        server_type = _determine_sql_server_type(
            data_contract,
            sql_server_type,
        )
        return to_sql_ddl(data_contract, server_type, export_args.get("server"))


class SqlQueryExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        model_name, model_value = _check_models_for_export(data_contract, model, self.export_format)
        server_type = _determine_sql_server_type(data_contract, sql_server_type, export_args.get("server"))
        return to_sql_query(
            data_contract,
            model_name,
            model_value,
            server_type,
        )


def to_sql_query(
    data_contract_spec: DataContractSpecification, model_name: str, model_value: Model, server_type: str = "snowflake"
) -> str:
    if data_contract_spec is None:
        return ""
    if data_contract_spec.models is None or len(data_contract_spec.models) == 0:
        return ""

    result = ""
    result += f"-- Data Contract: {data_contract_spec.id}\n"
    result += f"-- SQL Dialect: {server_type}\n"
    result += _to_sql_query(model_name, model_value, server_type)

    return result


def _to_sql_query(model_name, model_value, server_type) -> str:
    columns = []
    for field_name, field in model_value.fields.items():
        # TODO escape SQL reserved key words, probably dependent on server type
        columns.append(field_name)

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
    data_contract_spec: DataContractSpecification, server_type: str = "snowflake", server: str = None
) -> str:
    if data_contract_spec is None:
        return ""
    if data_contract_spec.models is None or len(data_contract_spec.models) == 0:
        return ""

    table_prefix = ""

    if server is None:
        servers = data_contract_spec.servers
    else:
        servers = {server: data_contract_spec.servers[server]}

    for server_name, server in iter(servers.items()):
        if server.type == "snowflake":
            server_type = "snowflake"
            break
        if server.type == "postgres":
            server_type = "postgres"
            break
        if server.type == "databricks":
            server_type = "databricks"
            if server.catalog is not None and server.schema_ is not None:
                table_prefix = server.catalog + "." + server.schema_ + "."
            break
        if server.type == server_type:
            break

    result = ""
    result += f"-- Data Contract: {data_contract_spec.id}\n"
    result += f"-- SQL Dialect: {server_type}\n"

    for model_name, model in iter(data_contract_spec.models.items()):
        result += _to_sql_table(table_prefix + model_name, model, server_type)

    return result.strip()


def _to_sql_table(model_name, model, server_type="snowflake"):
    if server_type == "databricks":
        # Databricks recommends to use the CREATE OR REPLACE statement for unity managed tables
        # https://docs.databricks.com/en/sql/language-manual/sql-ref-syntax-ddl-create-table-using.html
        result = f"CREATE OR REPLACE TABLE {model_name} (\n"
    else:
        result = f"CREATE TABLE {model_name} (\n"
    fields = len(model.fields)
    current_field_index = 1
    for field_name, field in iter(model.fields.items()):
        type = convert_to_sql_type(field, server_type)
        result += f"  {field_name} {type}"
        if field.required:
            result += " not null"
        if field.primaryKey or field.primary:
            result += " primary key"
        if server_type == "databricks" and field.description is not None:
            result += f' COMMENT "{_escape(field.description)}"'
        if current_field_index < fields:
            result += ","
        result += "\n"
        current_field_index += 1
    result += ")"
    if server_type == "databricks" and model.description is not None:
        result += f' COMMENT "{_escape(model.description)}"'
    result += ";\n"
    return result


def _escape(text: str | None) -> str | None:
    if text is None:
        return None
    return text.replace('"', '\\"')
