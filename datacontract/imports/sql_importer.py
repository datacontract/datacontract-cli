from simple_ddl_parser import parse_from_file

from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import DataContractSpecification, Model, Field


class SqlImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        return import_sql(data_contract_specification, self.import_format, source)


def import_sql(data_contract_specification: DataContractSpecification, format: str, source: str):
    ddl = parse_from_file(source, group_by_type=True)
    tables = ddl["tables"]

    for table in tables:
        if data_contract_specification.models is None:
            data_contract_specification.models = {}

        table_name = table["table_name"]

        fields = {}
        for column in table["columns"]:
            field = Field()
            field.type = map_type_from_sql(map_type_from_sql(column["type"]))
            if not column["nullable"]:
                field.required = True
            if column["unique"]:
                field.unique = True
            fields[column["name"]] = field
            if column["size"] is not None:
                field.maxLength = column["size"]

        if len(table["primary_key"]) == 1:
            primary_key = table["primary_key"][0]
            if primary_key in fields:
                fields[primary_key].unique = True
                fields[primary_key].required = True
                fields[primary_key].primary = True

        data_contract_specification.models[table_name] = Model(
            type="table",
            fields=fields,
        )

    return data_contract_specification


def map_type_from_sql(sql_type: str):
    if sql_type is None:
        return None

    sql_type_normed = sql_type.lower().strip()

    if sql_type_normed.startswith("varchar"):
        return "varchar"
    elif sql_type_normed.startswith("string"):
        return "string"
    elif sql_type_normed.startswith("text"):
        return "text"
    elif sql_type_normed.startswith("int"):
        return "integer"
    elif sql_type_normed.startswith("float"):
        return "float"
    elif sql_type_normed.startswith("decimal"):
        return "decimal"
    elif sql_type_normed.startswith("numeric"):
        return "numeric"
    elif sql_type_normed.startswith("bool"):
        return "boolean"
    elif sql_type_normed.startswith("timestamp"):
        return "timestamp"
    elif sql_type_normed == "date":
        return "date"
    elif sql_type_normed == "smalldatetime":
        return "timestamp_ntz"
    elif sql_type_normed == "datetime":
        return "timestamp_ntz"
    elif sql_type_normed == "datetime2":
        return "timestamp_ntz"
    elif sql_type_normed == "datetimeoffset":
        return "timestamp_tz"
    else:
        return "variant"
