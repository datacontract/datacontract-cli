import json
import os
from typing import List, Optional

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import ColumnInfo, TableInfo
from pyspark.sql import types

from datacontract.imports.importer import Importer
from datacontract.imports.spark_importer import _field_from_struct_type
from datacontract.model.data_contract_specification import DataContractSpecification, Field, Model
from datacontract.model.exceptions import DataContractException


class UnityImporter(Importer):
    """
    UnityImporter class for importing data contract specifications from Unity Catalog.
    """

    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        """
        Import data contract specification from a source.

        :param data_contract_specification: The data contract specification to be imported.
        :type data_contract_specification: DataContractSpecification
        :param source: The source from which to import the data contract specification.
        :type source: str
        :param import_args: Additional arguments for the import process.
        :type import_args: dict
        :return: The imported data contract specification.
        :rtype: DataContractSpecification
        """
        if source is not None:
            data_contract_specification = import_unity_from_json(data_contract_specification, source)
        else:
            data_contract_specification = import_unity_from_api(
                data_contract_specification, import_args.get("unity_table_full_name")
            )
        return data_contract_specification


def import_unity_from_json(
    data_contract_specification: DataContractSpecification, source: str
) -> DataContractSpecification:
    """
    Import data contract specification from a JSON file.

    :param data_contract_specification: The data contract specification to be imported.
    :type data_contract_specification: DataContractSpecification
    :param source: The path to the JSON file.
    :type source: str
    :return: The imported data contract specification.
    :rtype: DataContractSpecification
    :raises DataContractException: If there is an error parsing the JSON file.
    """
    try:
        with open(source, "r") as file:
            json_contents = json.loads(file.read())
            unity_schema = TableInfo.from_dict(json_contents)
    except json.JSONDecodeError as e:
        raise DataContractException(
            type="schema",
            name="Parse unity schema",
            reason=f"Failed to parse unity schema from {source}",
            engine="datacontract",
            original_exception=e,
        )
    return convert_unity_schema(data_contract_specification, unity_schema)


def import_unity_from_api(
    data_contract_specification: DataContractSpecification, unity_table_full_name: Optional[str] = None
) -> DataContractSpecification:
    """
    Import data contract specification from Unity Catalog API.

    :param data_contract_specification: The data contract specification to be imported.
    :type data_contract_specification: DataContractSpecification
    :param unity_table_full_name: The full name of the Unity table.
    :type unity_table_full_name: Optional[str]
    :return: The imported data contract specification.
    :rtype: DataContractSpecification
    :raises DataContractException: If there is an error retrieving the schema from the API.
    """
    try:
        workspace_client = WorkspaceClient()
        unity_schema: TableInfo = workspace_client.tables.get(unity_table_full_name)
    except Exception as e:
        raise DataContractException(
            type="schema",
            name="Retrieve unity catalog schema",
            reason=f"Failed to retrieve unity catalog schema from databricks profile: {os.getenv('DATABRICKS_CONFIG_PROFILE')}",
            engine="datacontract",
            original_exception=e,
        )

    convert_unity_schema(data_contract_specification, unity_schema)

    return data_contract_specification


def convert_unity_schema(
    data_contract_specification: DataContractSpecification, unity_schema: TableInfo
) -> DataContractSpecification:
    """
    Convert Unity schema to data contract specification.

    :param data_contract_specification: The data contract specification to be converted.
    :type data_contract_specification: DataContractSpecification
    :param unity_schema: The Unity schema to be converted.
    :type unity_schema: TableInfo
    :return: The converted data contract specification.
    :rtype: DataContractSpecification
    """
    if data_contract_specification.models is None:
        data_contract_specification.models = {}

    fields = import_table_fields(unity_schema.columns)

    table_id = unity_schema.name or unity_schema.table_id

    data_contract_specification.models[table_id] = Model(fields=fields, type="table")

    if unity_schema.name:
        data_contract_specification.models[table_id].title = unity_schema.name

    if unity_schema.comment:
        data_contract_specification.models[table_id].description = unity_schema.comment

    return data_contract_specification


def import_table_fields(columns: List[ColumnInfo]) -> dict[str, Field]:
    """
    Import table fields from Unity schema columns.

    Here we are first converting the `ColumnInfo.type_json` to a Spark StructField object
    so we can leave the complexity of the Spark field types to the Spark JSON schema parser,
    then re-use the logic in `datacontract.imports.spark_importer` to convert the StructField
    into a Field object.

    :param columns: The list of Unity schema columns.
    :type columns: List[ColumnInfo]
    :return: A dictionary of imported fields.
    :rtype: dict[str, Field]
    """
    imported_fields = {}

    for column in columns:
        struct_field: types.StructField = _type_json_to_spark_field(column.type_json)
        imported_fields[column.name] = _field_from_struct_type(struct_field)

    return imported_fields


def _type_json_to_spark_field(type_json: str) -> types.StructField:
    """
    Parses a JSON string representing a Spark field and returns a StructField object.

    The reason we do this is to leverage the Spark JSON schema parser to handle the
    complexity of the Spark field types. The field `type_json` in the Unity API is
    the output of a `StructField.jsonValue()` call.

    :param type_json: The JSON string representing the Spark field.
    :type type_json: str

    :return: The StructField object.
    :rtype: types.StructField
    """
    type_dict = json.loads(type_json)
    return types.StructField.fromJson(type_dict)
