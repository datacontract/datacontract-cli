from pydbml import PyDBML, Database
from typing import List

from pyparsing import ParseException

from datacontract.imports.importer import Importer
from datacontract.imports.sql_importer import map_type_from_sql
from datacontract.model.data_contract_specification import DataContractSpecification, Model, Field
from datacontract.model.exceptions import DataContractException


class DBMLImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        data_contract_specification = import_dbml_from_source(
            data_contract_specification,
            source,
            import_args.get("dbml_schema"),
            import_args.get("dbml_table"),
        )
        return data_contract_specification


def import_dbml_from_source(
    data_contract_specification: DataContractSpecification,
    source: str,
    import_schemas: List[str],
    import_tables: List[str],
) -> DataContractSpecification:
    try:
        with open(source, "r") as file:
            dbml_schema = PyDBML(file)
    except ParseException as e:
        raise DataContractException(
            type="schema",
            name="Parse DBML schema",
            reason=f"Failed to parse DBML schema from {source}",
            engine="datacontract",
            original_exception=e,
        )

    return convert_dbml(data_contract_specification, dbml_schema, import_schemas, import_tables)


def convert_dbml(
    data_contract_specification: DataContractSpecification,
    dbml_schema: Database,
    import_schemas: List[str],
    import_tables: List[str],
) -> DataContractSpecification:
    if dbml_schema.project is not None:
        data_contract_specification.info.title = dbml_schema.project.name

    if data_contract_specification.models is None:
        data_contract_specification.models = {}

    for table in dbml_schema.tables:
        schema_name = table.schema
        table_name = table.name

        # Skip if import schemas or table names are defined
        # and the current table doesn't match
        # if empty no filtering is done
        if import_schemas and schema_name not in import_schemas:
            continue

        if import_tables and table_name not in import_tables:
            continue

        fields = import_table_fields(table, dbml_schema.refs)

        data_contract_specification.models[table_name] = Model(
            fields=fields, namespace=schema_name, description=table.note.text
        )

    return data_contract_specification


def import_table_fields(table, references) -> dict[str, Field]:
    imported_fields = {}
    for field in table.columns:
        field_name = field.name
        imported_fields[field_name] = Field()
        imported_fields[field_name].required = field.not_null
        imported_fields[field_name].description = field.note.text
        imported_fields[field_name].primary = field.pk
        imported_fields[field_name].unique = field.unique
        # This is an assumption, that these might be valid SQL Types, since
        # DBML doesn't really enforce anything other than 'no spaces' in column types
        imported_fields[field_name].type = map_type_from_sql(field.type)

        ref = get_reference(field, references)
        if ref is not None:
            imported_fields[field_name].references = ref

    return imported_fields


def get_reference(field, references):
    result = None
    for ref in references:
        ref_table_name = ref.col1[0].table.name
        ref_col_name = ref.col1[0].name
        field_table_name = field.table.name
        field_name = field.name

        if ref_table_name == field_table_name and ref_col_name == field_name:
            result = f"{ref.col2[0].table.name}.{ref.col2[0].name}"
            return result

    return result
