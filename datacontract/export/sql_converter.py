from datacontract.export.sql_type_converter import convert_to_sql_type
from datacontract.model.data_contract_specification import \
    DataContractSpecification, Model


def to_sql_query(data_contract_spec: DataContractSpecification, model_name: str, model_value: Model, server_type: str = "snowflake") -> str:
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


def to_sql_ddl(data_contract_spec: DataContractSpecification, server_type: str = "snowflake") -> str:
    if data_contract_spec is None:
        return ""
    if data_contract_spec.models is None or len(data_contract_spec.models) == 0:
        return ""

    for server_name, server in iter(data_contract_spec.servers.items()):
        if server.type == server_type:
            break
        if server.type == "snowflake":
            server_type = "snowflake"
            break
        if server.type == "postgres":
            server_type = "postgres"
            break

    result = ""
    result += f"-- Data Contract: {data_contract_spec.id}\n"
    result += f"-- SQL Dialect: {server_type}\n"
    for model_name, model in iter(data_contract_spec.models.items()):
        result += _to_sql_table(model_name, model, server_type)

    return result.strip()


def _to_sql_table(model_name, model, server_type="snowflake"):
    result = f"CREATE TABLE {model_name} (\n"
    fields = len(model.fields)
    current_field_index = 1
    for field_name, field in iter(model.fields.items()):
        type = convert_to_sql_type(field, server_type)
        result += f"  {field_name} {type}"
        if field.required:
            result += " not null"
        if field.primary:
            result += " primary key"
        if current_field_index < fields:
            result += ","
        result += "\n"
        current_field_index += 1
    result += ");\n"
    return result


