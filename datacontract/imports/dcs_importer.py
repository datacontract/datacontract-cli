"""DCS Importer - Converts Data Contract Specification (DCS) to ODCS format."""

import json
import logging
from typing import Any, Dict, List, Optional

from datacontract_specification.model import DataContractSpecification, Field, Model
from datacontract_specification.model import Server as DCSServer
from open_data_contract_standard.model import (
    CustomProperty,
    DataQuality,
    Description,
    OpenDataContractStandard,
    Relationship,
    SchemaObject,
    SchemaProperty,
    ServiceLevelAgreementProperty,
    Team,
)
from open_data_contract_standard.model import (
    Server as ODCSServer,
)

from datacontract.imports.importer import Importer

logger = logging.getLogger(__name__)


class DcsImporter(Importer):
    """Importer for Data Contract Specification (DCS) format."""

    def import_source(
        self, source: str, import_args: dict
    ) -> OpenDataContractStandard:
        import yaml

        from datacontract.lint.resources import read_resource

        source_str = read_resource(source)
        dcs_dict = yaml.safe_load(source_str)
        dcs = parse_dcs_from_dict(dcs_dict)
        return convert_dcs_to_odcs(dcs)


def parse_dcs_from_dict(dcs_dict: dict) -> DataContractSpecification:
    """Parse a DCS dictionary into a DataContractSpecification object."""
    return DataContractSpecification(**dcs_dict)


def convert_dcs_to_odcs(dcs: DataContractSpecification) -> OpenDataContractStandard:
    """Convert a DCS data contract to ODCS format."""
    odcs = OpenDataContractStandard(
        id=dcs.id,
        kind="DataContract",
        apiVersion="v3.1.0",
    )

    # Convert basic info
    if dcs.info:
        odcs.name = dcs.info.title
        odcs.version = dcs.info.version
        if dcs.info.description:
            odcs.description = Description(purpose=dcs.info.description)
        if dcs.info.owner:
            team = Team(name=dcs.info.owner)
            # Add contact info to customProperties if available
            if dcs.info.contact:
                contact_props = []
                if dcs.info.contact.name:
                    contact_props.append(CustomProperty(property="contactName", value=dcs.info.contact.name))
                if dcs.info.contact.url:
                    contact_props.append(CustomProperty(property="contactUrl", value=dcs.info.contact.url))
                if dcs.info.contact.email:
                    contact_props.append(CustomProperty(property="contactEmail", value=dcs.info.contact.email))
                if contact_props:
                    team.customProperties = contact_props
            odcs.team = team

    # Convert status
    if dcs.info and dcs.info.status:
        odcs.status = dcs.info.status

    # Convert servers
    if dcs.servers:
        odcs.servers = _convert_servers(dcs.servers)

    # Convert models to schema
    if dcs.models:
        odcs.schema_ = _convert_models_to_schema(dcs.models, dcs.definitions)

    # Convert service levels to SLA properties
    if dcs.servicelevels:
        odcs.slaProperties = _convert_servicelevels(dcs.servicelevels)

    # Convert tags
    if dcs.tags:
        odcs.tags = dcs.tags

    # Convert links to authoritativeDefinitions
    if dcs.links:
        from open_data_contract_standard.model import AuthoritativeDefinition
        odcs.authoritativeDefinitions = [
            AuthoritativeDefinition(type=key, url=value) for key, value in dcs.links.items()
        ]

    # Convert terms to Description fields
    if dcs.terms:
        if odcs.description is None:
            odcs.description = Description()
        if dcs.terms.usage:
            odcs.description.usage = dcs.terms.usage
        if dcs.terms.limitations:
            odcs.description.limitations = dcs.terms.limitations
        # Convert policies to authoritativeDefinitions
        if dcs.terms.policies:
            from open_data_contract_standard.model import AuthoritativeDefinition
            policy_defs = [
                AuthoritativeDefinition(type=p.name, description=getattr(p, "description", None), url=getattr(p, "url", None))
                for p in dcs.terms.policies
            ]
            if odcs.authoritativeDefinitions:
                odcs.authoritativeDefinitions.extend(policy_defs)
            else:
                odcs.authoritativeDefinitions = policy_defs
        # Store billing, noticePeriod in customProperties
        desc_custom_props = odcs.description.customProperties or []
        if dcs.terms.billing:
            desc_custom_props.append(CustomProperty(property="billing", value=dcs.terms.billing))
        if dcs.terms.noticePeriod:
            desc_custom_props.append(CustomProperty(property="noticePeriod", value=dcs.terms.noticePeriod))
        if desc_custom_props:
            odcs.description.customProperties = desc_custom_props

    return odcs


def _convert_servers(dcs_servers: Dict[str, DCSServer]) -> List[ODCSServer]:
    """Convert DCS servers dict to ODCS servers list."""
    servers = []
    for server_name, dcs_server in dcs_servers.items():
        odcs_server = ODCSServer(
            server=server_name,
            type=dcs_server.type,
        )

        # Copy common attributes
        if dcs_server.environment:
            odcs_server.environment = dcs_server.environment
        if dcs_server.account:
            odcs_server.account = dcs_server.account
        if dcs_server.database:
            odcs_server.database = dcs_server.database
        if dcs_server.schema_:
            odcs_server.schema_ = dcs_server.schema_
        if dcs_server.format:
            odcs_server.format = dcs_server.format
        if dcs_server.project:
            odcs_server.project = dcs_server.project
        if dcs_server.dataset:
            odcs_server.dataset = dcs_server.dataset
        if dcs_server.path:
            odcs_server.path = dcs_server.path
        if dcs_server.delimiter:
            odcs_server.delimiter = dcs_server.delimiter
        if dcs_server.endpointUrl:
            odcs_server.endpointUrl = dcs_server.endpointUrl
        if dcs_server.location:
            odcs_server.location = dcs_server.location
        if dcs_server.host:
            odcs_server.host = dcs_server.host
        if dcs_server.port:
            odcs_server.port = dcs_server.port
        if dcs_server.catalog:
            odcs_server.catalog = dcs_server.catalog
        if dcs_server.description:
            odcs_server.description = dcs_server.description
        if dcs_server.roles:
            from open_data_contract_standard.model import Role as ODCSRole
            odcs_server.roles = [ODCSRole(role=r.name, description=r.description) for r in dcs_server.roles]
        if dcs_server.topic:
            # Store topic in customProperties since ODCS Server doesn't have a topic field
            if odcs_server.customProperties is None:
                odcs_server.customProperties = []
            odcs_server.customProperties.append(CustomProperty(property="topic", value=dcs_server.topic))
        if getattr(dcs_server, "http_path", None):
            # Store http_path in customProperties since ODCS Server doesn't have it
            if odcs_server.customProperties is None:
                odcs_server.customProperties = []
            odcs_server.customProperties.append(CustomProperty(property="http_path", value=dcs_server.http_path))
        if getattr(dcs_server, "driver", None):
            # Store driver in customProperties since ODCS Server doesn't have it
            if odcs_server.customProperties is None:
                odcs_server.customProperties = []
            odcs_server.customProperties.append(CustomProperty(property="driver", value=dcs_server.driver))
        if getattr(dcs_server, "service_name", None):
            odcs_server.serviceName = dcs_server.service_name

        servers.append(odcs_server)

    return servers


def _convert_models_to_schema(models: Dict[str, Model], definitions: Dict[str, Field] = None) -> List[SchemaObject]:
    """Convert DCS models dict to ODCS schema list."""
    schema = []
    for model_name, model in models.items():
        schema_obj = SchemaObject(
            name=model_name,
            physicalType=model.type,
            description=model.description,
        )

        # Convert config.*Table to physicalName
        if model.config:
            physical_name = _get_physical_name_from_config(model.config)
            if physical_name:
                schema_obj.physicalName = physical_name

        # Store namespace in customProperties for Avro export
        if hasattr(model, 'namespace') and model.namespace:
            if schema_obj.customProperties is None:
                schema_obj.customProperties = []
            schema_obj.customProperties.append(CustomProperty(property="namespace", value=model.namespace))

        # Convert fields to properties
        # Pass model-level primaryKey list to set primaryKey and primaryKeyPosition on fields
        model_primary_keys = model.primaryKey if hasattr(model, 'primaryKey') and model.primaryKey else []
        if model.fields:
            schema_obj.properties = _convert_fields_to_properties(model.fields, model_primary_keys, definitions)

        # Convert quality rules
        if model.quality:
            schema_obj.quality = _convert_quality_list(model.quality)

        schema.append(schema_obj)

    return schema


def _get_physical_name_from_config(config: Dict[str, Any]) -> Optional[str]:
    """Extract physical table name from DCS model config."""
    # Check for server-specific table name config keys
    table_config_keys = [
        "postgresTable",
        "databricksTable",
        "snowflakeTable",
        "sqlserverTable",
        "bigqueryTable",
        "redshiftTable",
        "oracleTable",
        "mysqlTable",
    ]
    for key in table_config_keys:
        if key in config and config[key]:
            return config[key]
    return None


def _convert_fields_to_properties(
    fields: Dict[str, Field], model_primary_keys: List[str] = None, definitions: Dict[str, Field] = None
) -> List[SchemaProperty]:
    """Convert DCS fields dict to ODCS properties list."""
    model_primary_keys = model_primary_keys or []
    properties = []
    for field_name, field in fields.items():
        # Determine primaryKeyPosition from model-level primaryKey list
        primary_key_position = None
        if field_name in model_primary_keys:
            primary_key_position = model_primary_keys.index(field_name) + 1
        prop = _convert_field_to_property(field_name, field, primary_key_position, definitions)
        properties.append(prop)
    return properties


def _resolve_field_ref(field: Field, definitions: Dict[str, Field]) -> Field:
    """Resolve a field's $ref and merge with field properties."""
    if not field.ref:
        return field

    ref_path = field.ref
    resolved_data = None

    # Handle file:// references
    if ref_path.startswith("file://"):
        resolved_data = _resolve_file_ref(ref_path)
    # Handle #/definitions/ references
    elif ref_path.startswith("#/") and definitions:
        resolved_data = _resolve_local_ref(ref_path, definitions)

    if resolved_data is None:
        return field

    # Create merged field: resolved values as base, field values override
    merged_data = {}
    for attr in Field.model_fields.keys():
        resolved_value = resolved_data.get(attr)
        field_value = getattr(field, attr, None)
        # Field value takes precedence if set (not None and not empty for collections)
        if field_value is not None:
            if isinstance(field_value, (list, dict)):
                if field_value:  # Non-empty collection
                    merged_data[attr] = field_value
                elif resolved_value:
                    merged_data[attr] = resolved_value
            else:
                merged_data[attr] = field_value
        elif resolved_value is not None:
            merged_data[attr] = resolved_value
    # Clear ref to avoid infinite recursion
    merged_data['ref'] = None
    return Field(**merged_data)


def _resolve_file_ref(ref_path: str) -> Optional[Dict[str, Any]]:
    """Resolve a file:// reference, optionally with a JSON pointer path."""
    from urllib.parse import urlparse

    import yaml

    # Split file path and JSON pointer
    if "#" in ref_path:
        file_url, pointer = ref_path.split("#", 1)
    else:
        file_url, pointer = ref_path, ""

    try:
        # Parse the file:// URL to get the path
        parsed = urlparse(file_url)
        if parsed.scheme == "file":
            file_path = parsed.path
        else:
            # Not a file:// URL, can't handle
            logger.warning(f"Unsupported URL scheme in reference: {ref_path}")
            return None

        # Read the file
        with open(file_path, "r") as f:
            content = f.read()

        data = yaml.safe_load(content)

        if pointer:
            # Navigate the JSON pointer path
            data = _navigate_path(data, pointer)

        return data if isinstance(data, dict) else None
    except Exception as e:
        logger.warning(f"Failed to resolve file reference {ref_path}: {e}")
        return None


def _resolve_local_ref(ref_path: str, definitions: Dict[str, Field]) -> Optional[Dict[str, Any]]:
    """Resolve a local #/ reference within definitions."""
    if not ref_path.startswith("#/definitions/"):
        return None

    # Remove the #/definitions/ prefix
    path_after_definitions = ref_path[len("#/definitions/"):]

    # Check for simple case: #/definitions/name
    if "/" not in path_after_definitions:
        if path_after_definitions in definitions:
            definition = definitions[path_after_definitions]
            return {attr: getattr(definition, attr, None) for attr in Field.model_fields.keys()}
        return None

    # Complex case: #/definitions/name/fields/field_name
    parts = path_after_definitions.split("/")
    def_name = parts[0]

    if def_name not in definitions:
        return None

    definition = definitions[def_name]

    # Navigate remaining path
    remaining_path = "/" + "/".join(parts[1:])
    data = {attr: getattr(definition, attr, None) for attr in Field.model_fields.keys()}
    # Convert fields dict to nested structure for navigation
    if definition.fields:
        data["fields"] = {name: _field_to_dict(f) for name, f in definition.fields.items()}

    return _navigate_path(data, remaining_path)


def _field_to_dict(field: Field) -> Dict[str, Any]:
    """Convert a Field object to a dictionary."""
    return {attr: getattr(field, attr, None) for attr in Field.model_fields.keys()}


def _navigate_path(data: Any, path: str) -> Optional[Dict[str, Any]]:
    """Navigate a JSON pointer-like path within data."""
    if not path or path == "/":
        return data if isinstance(data, dict) else None

    # Remove leading slash and split
    parts = path.lstrip("/").split("/")

    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None

    return current if isinstance(current, dict) else None


def _convert_field_to_property(
    field_name: str, field: Field, primary_key_position: int = None, definitions: Dict[str, Field] = None
) -> SchemaProperty:
    """Convert a DCS field to an ODCS property."""
    # Resolve $ref if present
    field = _resolve_field_ref(field, definitions)

    prop = SchemaProperty(name=field_name)

    # Preserve original type as physicalType and convert to logicalType
    if field.type:
        prop.physicalType = field.type
        prop.logicalType = _convert_type_to_logical_type(field.type)

    # Copy direct attributes
    if field.description:
        prop.description = field.description
    if field.required is not None:
        prop.required = field.required
    if field.unique is not None:
        prop.unique = field.unique
    # Set primaryKey from field-level or model-level primaryKey
    if field.primaryKey is not None:
        prop.primaryKey = field.primaryKey
    elif primary_key_position is not None:
        prop.primaryKey = True
        prop.primaryKeyPosition = primary_key_position
    if field.title:
        prop.businessName = field.title
    if field.classification:
        prop.classification = field.classification
    if field.tags:
        prop.tags = field.tags

    # Convert constraints to logicalTypeOptions
    logical_type_options = {}
    if field.minLength is not None:
        logical_type_options["minLength"] = field.minLength
    if field.maxLength is not None:
        logical_type_options["maxLength"] = field.maxLength
    if field.pattern:
        logical_type_options["pattern"] = field.pattern
    if field.minimum is not None:
        logical_type_options["minimum"] = field.minimum
    if field.maximum is not None:
        logical_type_options["maximum"] = field.maximum
    if field.exclusiveMinimum is not None:
        logical_type_options["exclusiveMinimum"] = field.exclusiveMinimum
    if field.exclusiveMaximum is not None:
        logical_type_options["exclusiveMaximum"] = field.exclusiveMaximum
    if field.format:
        logical_type_options["format"] = field.format

    if logical_type_options:
        prop.logicalTypeOptions = logical_type_options

    # Convert config to customProperties
    custom_properties = []
    # Handle enum as quality rule (invalidValues with validValues, mustBe: 0)
    quality_rules = []
    if field.enum:
        quality_rules.append(
            DataQuality(
                type="library",
                metric="invalidValues",
                arguments={"validValues": field.enum},
                mustBe=0,
            )
        )
    if field.pii is not None:
        custom_properties.append(CustomProperty(property="pii", value=str(field.pii)))
    if field.precision is not None:
        custom_properties.append(CustomProperty(property="precision", value=str(field.precision)))
    if field.scale is not None:
        custom_properties.append(CustomProperty(property="scale", value=str(field.scale)))
    if field.config:
        # Server-specific type overrides physicalType
        server_type_keys = ["oracleType", "snowflakeType", "postgresType", "bigqueryType", "databricksType", "sqlserverType", "trinoType", "physicalType"]
        for key in server_type_keys:
            if key in field.config:
                prop.physicalType = field.config[key]
                break

        for key, value in field.config.items():
            # Use JSON serialization for lists and dicts to preserve structure
            if isinstance(value, (list, dict)):
                custom_properties.append(CustomProperty(property=key, value=json.dumps(value)))
            else:
                custom_properties.append(CustomProperty(property=key, value=str(value)))

    # Convert references to relationships
    if field.references:
        prop.relationships = [Relationship(type="foreignKey", to=field.references)]

    # Convert nested fields (for object types)
    if field.fields:
        prop.properties = _convert_fields_to_properties(field.fields, None, definitions)

    # Convert items (for array types)
    if field.items:
        prop.items = _convert_field_to_property("item", field.items, None, definitions)

    # Convert keys/values (for map types) - store types in customProperties
    if field.keys or field.values:
        if field.keys and field.keys.type:
            custom_properties.append(CustomProperty(property="mapKeyType", value=_convert_type_to_logical_type(field.keys.type)))
        if field.values and field.values.type:
            custom_properties.append(CustomProperty(property="mapValueType", value=_convert_type_to_logical_type(field.values.type)))
            # For map with struct values, store the value fields in properties
            if field.values.fields:
                prop.properties = _convert_fields_to_properties(field.values.fields, None, definitions)

    # Set customProperties after all have been added
    if custom_properties:
        prop.customProperties = custom_properties

    # Convert quality rules (merge enum quality rule with field-level quality)
    if field.quality:
        quality_rules.extend(_convert_quality_list(field.quality))
    if quality_rules:
        prop.quality = quality_rules

    # Convert lineage
    if field.lineage:
        if hasattr(field.lineage, 'inputFields') and field.lineage.inputFields:
            prop.transformSourceObjects = [f"{f.namespace}.{f.name}.{f.field}" if hasattr(f, 'namespace') and f.namespace else f"{f.name}.{f.field}" for f in field.lineage.inputFields]
        if hasattr(field.lineage, 'transformationDescription') and field.lineage.transformationDescription:
            prop.transformDescription = field.lineage.transformationDescription
        if hasattr(field.lineage, 'transformationType') and field.lineage.transformationType:
            prop.transformLogic = field.lineage.transformationType

    return prop


def _convert_type_to_logical_type(dcs_type: str) -> str:
    """Convert DCS type to ODCS logical type."""
    if dcs_type is None:
        return "string"

    t = dcs_type.lower()

    # Map DCS types to ODCS logical types
    type_mapping = {
        "string": "string",
        "text": "string",
        "varchar": "string",
        "char": "string",
        "integer": "integer",
        "int": "integer",
        "long": "integer",
        "bigint": "integer",
        "float": "number",
        "double": "number",
        "decimal": "number",
        "numeric": "number",
        "number": "number",
        "boolean": "boolean",
        "bool": "boolean",
        "timestamp": "timestamp",
        "timestamp_tz": "timestamp",
        "timestamp_ntz": "timestamp",
        "date": "date",
        "time": "string",   # not supported in ODCS
        "datetime": "timestamp",
        "array": "array",
        "object": "object",
        "record": "object",
        "struct": "object",
        "map": "object",
        "bytes": "string",   # not supported in ODCS
        "binary": "string",  # not supported in ODCS
        "null": "string",    # not supported in ODCS
    }

    return type_mapping.get(t, t)


def _convert_quality_list(quality_list: list) -> List[DataQuality]:
    """Convert DCS quality list to ODCS DataQuality list."""
    if not quality_list:
        return []

    result = []
    for q in quality_list:
        if q is None:
            continue
        dq = DataQuality(type=getattr(q, "type", None))
        if hasattr(q, "description") and q.description:
            dq.description = q.description
        if hasattr(q, "query") and q.query:
            dq.query = q.query
        if hasattr(q, "metric") and q.metric:
            dq.metric = q.metric
        if hasattr(q, "mustBe") and q.mustBe is not None:
            dq.mustBe = q.mustBe
        if hasattr(q, "mustNotBe") and q.mustNotBe is not None:
            dq.mustNotBe = q.mustNotBe
        if hasattr(q, "mustBeGreaterThan") and q.mustBeGreaterThan is not None:
            dq.mustBeGreaterThan = q.mustBeGreaterThan
        if hasattr(q, "mustBeGreaterOrEqualTo") and q.mustBeGreaterOrEqualTo is not None:
            dq.mustBeGreaterOrEqualTo = q.mustBeGreaterOrEqualTo
        if hasattr(q, "mustBeGreaterThanOrEqualTo") and q.mustBeGreaterThanOrEqualTo is not None:
            dq.mustBeGreaterOrEqualTo = q.mustBeGreaterThanOrEqualTo
        if hasattr(q, "mustBeLessThan") and q.mustBeLessThan is not None:
            dq.mustBeLessThan = q.mustBeLessThan
        if hasattr(q, "mustBeLessOrEqualTo") and q.mustBeLessOrEqualTo is not None:
            dq.mustBeLessOrEqualTo = q.mustBeLessOrEqualTo
        if hasattr(q, "mustBeLessThanOrEqualTo") and q.mustBeLessThanOrEqualTo is not None:
            dq.mustBeLessOrEqualTo = q.mustBeLessThanOrEqualTo
        if hasattr(q, "mustBeBetween") and q.mustBeBetween is not None:
            dq.mustBeBetween = q.mustBeBetween
        if hasattr(q, "mustNotBeBetween") and q.mustNotBeBetween is not None:
            dq.mustNotBeBetween = q.mustNotBeBetween
        if hasattr(q, "engine") and q.engine:
            dq.engine = q.engine
        if hasattr(q, "implementation") and q.implementation:
            dq.implementation = q.implementation

        result.append(dq)

    return result


def _convert_servicelevels(servicelevels: Any) -> List[ServiceLevelAgreementProperty]:
    """Convert DCS service levels to ODCS SLA properties."""
    sla_properties = []

    if hasattr(servicelevels, "availability") and servicelevels.availability:
        sla_properties.append(
            ServiceLevelAgreementProperty(
                property="generalAvailability",
                value=servicelevels.availability.description if hasattr(servicelevels.availability, "description") else str(servicelevels.availability),
            )
        )

    if hasattr(servicelevels, "retention") and servicelevels.retention:
        retention = servicelevels.retention
        period = retention.period if hasattr(retention, "period") else str(retention)
        element = retention.timestampField if hasattr(retention, "timestampField") else None
        sla_properties.append(
            ServiceLevelAgreementProperty(
                property="retention",
                value=period,
                element=element,
            )
        )

    if hasattr(servicelevels, "freshness") and servicelevels.freshness:
        freshness = servicelevels.freshness
        if hasattr(freshness, "threshold") and freshness.threshold and hasattr(freshness, "timestampField") and freshness.timestampField:
            value, unit = _parse_iso8601_duration(freshness.threshold)
            if value is not None and unit is not None:
                sla_properties.append(
                    ServiceLevelAgreementProperty(
                        property="freshness",
                        value=value,
                        unit=unit,
                        element=freshness.timestampField,
                    )
                )

    if hasattr(servicelevels, "latency") and servicelevels.latency:
        latency = servicelevels.latency
        if hasattr(latency, "threshold") and latency.threshold:
            value, unit = _parse_iso8601_duration(latency.threshold)
            if value is not None and unit is not None:
                element = None
                if hasattr(latency, "sourceTimestampField") and latency.sourceTimestampField:
                    element = latency.sourceTimestampField
                sla_properties.append(
                    ServiceLevelAgreementProperty(
                        property="latency",
                        value=value,
                        unit=unit,
                        element=element,
                    )
                )

    if hasattr(servicelevels, "frequency") and servicelevels.frequency:
        frequency = servicelevels.frequency
        freq_value = frequency.interval if hasattr(frequency, "interval") and frequency.interval else (frequency.cron if hasattr(frequency, "cron") else None)
        if freq_value:
            sla_properties.append(
                ServiceLevelAgreementProperty(
                    property="frequency",
                    value=freq_value,
                )
            )

    if hasattr(servicelevels, "support") and servicelevels.support:
        support = servicelevels.support
        support_value = support.time if hasattr(support, "time") and support.time else (support.description if hasattr(support, "description") else None)
        if support_value:
            sla_properties.append(
                ServiceLevelAgreementProperty(
                    property="support",
                    value=support_value,
                )
            )

    if hasattr(servicelevels, "backup") and servicelevels.backup:
        backup = servicelevels.backup
        backup_value = backup.interval if hasattr(backup, "interval") and backup.interval else (backup.cron if hasattr(backup, "cron") else None)
        if backup_value:
            sla_properties.append(
                ServiceLevelAgreementProperty(
                    property="backup",
                    value=backup_value,
                )
            )

    return sla_properties


def _parse_iso8601_duration(duration: str) -> tuple:
    """Parse ISO 8601 duration (e.g., PT1H, P1D) to value and unit."""
    import re

    if not duration:
        return None, None

    # Remove P and T prefixes
    duration = duration.upper().replace("P", "").replace("T", "")

    # Match patterns like 1H, 30M, 1D
    match = re.match(r"(\d+)([DHMS])", duration)
    if match:
        value = int(match.group(1))
        unit_char = match.group(2)
        unit_map = {"D": "d", "H": "h", "M": "m", "S": "s"}
        return value, unit_map.get(unit_char, "d")

    return None, None
