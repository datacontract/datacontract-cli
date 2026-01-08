import json
import os
from typing import List

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import ColumnInfo, TableInfo
from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
    create_server,
)
from datacontract.imports.sql_importer import map_type_from_sql
from datacontract.model.exceptions import DataContractException


class UnityImporter(Importer):
    """UnityImporter class for importing data contract specifications from Unity Catalog."""

    def import_source(
        self,
        source: str,
        import_args: dict,
    ) -> OpenDataContractStandard:
        """Import data contract specification from a source."""
        if source is not None:
            return import_unity_from_json(source)
        else:
            unity_table_full_name_list = import_args.get("unity_table_full_name")
            return import_unity_from_api(unity_table_full_name_list)


def import_unity_from_json(source: str) -> OpenDataContractStandard:
    """Import data contract specification from a JSON file."""
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

    odcs = create_odcs()
    return convert_unity_schema(odcs, unity_schema)


def import_unity_from_api(unity_table_full_name_list: List[str] = None) -> OpenDataContractStandard:
    """Import data contract specification from Unity Catalog API."""
    try:
        profile = os.getenv("DATACONTRACT_DATABRICKS_PROFILE")
        host, token = os.getenv("DATACONTRACT_DATABRICKS_SERVER_HOSTNAME"), os.getenv("DATACONTRACT_DATABRICKS_TOKEN")
        exception = DataContractException(
            type="configuration",
            name="Databricks configuration",
            reason="",
            engine="datacontract",
        )

        if not profile and not host and not token:
            reason = "Either DATACONTRACT_DATABRICKS_PROFILE or both DATACONTRACT_DATABRICKS_SERVER_HOSTNAME and DATACONTRACT_DATABRICKS_TOKEN environment variables must be set"
            exception.reason = reason
            raise exception
        if token and not host:
            reason = "DATACONTRACT_DATABRICKS_SERVER_HOSTNAME environment variable is not set"
            exception.reason = reason
            raise exception
        if host and not token:
            reason = "DATACONTRACT_DATABRICKS_TOKEN environment variable is not set"
            exception.reason = reason
            raise exception
        workspace_client = WorkspaceClient(profile=profile) if profile else WorkspaceClient(host=host, token=token)
    except Exception as e:
        raise DataContractException(
            type="schema",
            name="Retrieve unity catalog schema",
            reason="Failed to connect to unity catalog schema",
            engine="datacontract",
            original_exception=e,
        )

    odcs = create_odcs()
    odcs.schema_ = []

    for unity_table_full_name in unity_table_full_name_list:
        try:
            unity_schema: TableInfo = workspace_client.tables.get(unity_table_full_name)
        except Exception as e:
            raise DataContractException(
                type="schema",
                name="Retrieve unity catalog schema",
                reason=f"Unity table {unity_table_full_name} not found",
                engine="datacontract",
                original_exception=e,
            )
        odcs = convert_unity_schema(odcs, unity_schema)

    return odcs


def convert_unity_schema(odcs: OpenDataContractStandard, unity_schema: TableInfo) -> OpenDataContractStandard:
    """Convert Unity schema to ODCS data contract."""
    if odcs.schema_ is None:
        odcs.schema_ = []

    # Configure databricks server with catalog and schema from Unity table info
    schema_name = unity_schema.schema_name
    catalog_name = unity_schema.catalog_name

    if catalog_name and schema_name:
        if odcs.servers is None:
            odcs.servers = []

        server = create_server(
            name="databricks",
            server_type="databricks",
            catalog=catalog_name,
            schema=schema_name,
        )
        odcs.servers = [server]

    properties = import_table_fields(unity_schema.columns)

    table_id = unity_schema.name or unity_schema.table_id

    schema_obj = create_schema_object(
        name=table_id,
        physical_type="table",
        description=unity_schema.comment,
        properties=properties,
    )

    if unity_schema.name:
        schema_obj.businessName = unity_schema.name

    odcs.schema_.append(schema_obj)

    return odcs


def import_table_fields(columns: List[ColumnInfo]) -> List[SchemaProperty]:
    """Import table fields from Unity schema columns."""
    return [_to_property(column) for column in columns]


def _to_property(column: ColumnInfo) -> SchemaProperty:
    """Convert a Unity ColumnInfo to an ODCS SchemaProperty."""
    sql_type = str(column.type_text) if column.type_text else "string"
    logical_type = map_type_from_sql(sql_type)
    required = column.nullable is None or not column.nullable

    return create_property(
        name=column.name,
        logical_type=logical_type if logical_type else "string",
        physical_type=sql_type,
        description=column.comment,
        required=required if required else None,
        custom_properties={"databricksType": sql_type} if sql_type else None,
    )
