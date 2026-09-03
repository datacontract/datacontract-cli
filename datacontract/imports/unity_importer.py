import json
import logging
from typing import List, Optional, Tuple

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import ColumnInfo, TableInfo
from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty

from datacontract.config import Config
from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
    create_server,
)
from datacontract.imports.sql_importer import map_type_from_sql
from datacontract.model.exceptions import DataContractException

logger = logging.getLogger(__name__)


class UnityImporter(Importer):
    """UnityImporter class for importing data contract specifications from Unity Catalog."""

    def import_source(
        self,
        source: str,
        import_args: dict,
        config: "Config | None" = None,
    ) -> OpenDataContractStandard:
        """Import data contract specification from a source."""
        if source is not None:
            return import_unity_from_json(source)
        else:
            unity_table_full_name_list = import_args.get("unity_table_full_name")
            return import_unity_from_api(unity_table_full_name_list, config)


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
            engine="datacontract-cli",
            original_exception=e,
        )

    odcs = create_odcs()
    return convert_unity_schema(odcs, unity_schema)


def import_unity_from_api(
    unity_table_full_name_list: List[str] = None, config: "Config | None" = None
) -> OpenDataContractStandard:
    """Import data contract specification from Unity Catalog API."""
    config = Config.resolve(config)
    try:
        profile = config.get_databricks_profile()
        host, token = (
            config.get_databricks_server_hostname(),
            config.get_databricks_token(),
        )
        exception = DataContractException(
            type="configuration",
            name="Databricks configuration",
            reason="",
            engine="datacontract-cli",
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
            engine="datacontract-cli",
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
                engine="datacontract-cli",
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
    logical_type, format = map_type_from_sql(sql_type)
    required = column.nullable is None or not column.nullable
    nested_properties, items, map_key, map_value = _to_nested_types(column)

    return create_property(
        name=column.name,
        logical_type=logical_type,
        physical_type=sql_type,
        description=column.comment,
        format=format,
        required=required if required else None,
        properties=nested_properties,
        items=items,
        map_key=map_key,
        map_value=map_value,
    )


def _to_nested_types(
    column: ColumnInfo,
) -> Tuple[
    Optional[List[SchemaProperty]], Optional[SchemaProperty], Optional[SchemaProperty], Optional[SchemaProperty]
]:
    """Resolve nested struct/array types from Unity's type_json.

    Unity's type_json carries the full column type as Spark StructField JSON.
    Returns (properties, items, map_key, map_value) for struct, array and map
    columns, all ``None`` otherwise.
    """
    if not column.type_json:
        return None, None, None, None
    try:
        from datacontract.imports.spark_type_json import property_from_field_json, property_from_type_json

        data_type = json.loads(column.type_json)["type"]
        if isinstance(data_type, dict):
            if data_type.get("type") == "array":
                items = property_from_type_json(
                    "items", data_type["elementType"], not data_type.get("containsNull", True)
                )
                return None, items, None, None
            if data_type.get("type") == "struct":
                return [property_from_field_json(f) for f in data_type["fields"]], None, None, None
            if data_type.get("type") == "map":
                prop = property_from_type_json("map", data_type)
                return None, None, prop.map.key, prop.map.value
    except Exception as e:
        logger.warning("Could not resolve nested type for column %s from type_json: %s", column.name, e)
    return None, None, None, None
