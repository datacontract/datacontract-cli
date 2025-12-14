from typing import List

from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty
from pydbml import Database, PyDBML
from pyparsing import ParseException

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
)
from datacontract.imports.sql_importer import map_type_from_sql
from datacontract.model.exceptions import DataContractException


class DBMLImporter(Importer):
    def import_source(
        self, source: str, import_args: dict
    ) -> OpenDataContractStandard:
        return import_dbml_from_source(
            source,
            import_args.get("dbml_schema"),
            import_args.get("dbml_table"),
        )


def import_dbml_from_source(
    source: str,
    import_schemas: List[str],
    import_tables: List[str],
) -> OpenDataContractStandard:
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

    return convert_dbml(dbml_schema, import_schemas, import_tables)


def convert_dbml(
    dbml_schema: Database,
    import_schemas: List[str],
    import_tables: List[str],
) -> OpenDataContractStandard:
    odcs = create_odcs()

    if dbml_schema.project is not None:
        odcs.name = dbml_schema.project.name

    odcs.schema_ = []

    for table in dbml_schema.tables:
        schema_name = table.schema
        table_name = table.name

        # Skip if import schemas or table names are defined and current table doesn't match
        if import_schemas and schema_name not in import_schemas:
            continue

        if import_tables and table_name not in import_tables:
            continue

        properties = import_table_fields(table, dbml_schema.refs)

        schema_obj = create_schema_object(
            name=table_name,
            physical_type="table",
            description=table.note.text if table.note else None,
            properties=properties,
        )

        # Store namespace as custom property
        if schema_name:
            from open_data_contract_standard.model import CustomProperty
            schema_obj.customProperties = [CustomProperty(property="namespace", value=schema_name)]

        odcs.schema_.append(schema_obj)

    return odcs


def import_table_fields(table, references) -> List[SchemaProperty]:
    """Import DBML table fields as ODCS SchemaProperties."""
    properties = []
    pk_position = 1

    for field in table.columns:
        field_name = field.name
        required = field.not_null
        description = field.note.text if field.note else None
        is_primary_key = field.pk
        is_unique = field.unique
        logical_type = map_type_from_sql(field.type)

        ref = get_reference(field, references)

        custom_props = {}
        if ref:
            custom_props["references"] = ref

        prop = create_property(
            name=field_name,
            logical_type=logical_type if logical_type else "string",
            physical_type=field.type,
            description=description,
            required=required if required else None,
            primary_key=is_primary_key if is_primary_key else None,
            primary_key_position=pk_position if is_primary_key else None,
            unique=is_unique if is_unique else None,
            custom_properties=custom_props if custom_props else None,
        )

        if is_primary_key:
            pk_position += 1

        properties.append(prop)

    return properties


def get_reference(field, references):
    """Get the reference for a field if it exists."""
    for ref in references:
        ref_table_name = ref.col1[0].table.name
        ref_col_name = ref.col1[0].name
        field_table_name = field.table.name
        field_name = field.name

        if ref_table_name == field_table_name and ref_col_name == field_name:
            return f"{ref.col2[0].table.name}.{ref.col2[0].name}"

    return None
