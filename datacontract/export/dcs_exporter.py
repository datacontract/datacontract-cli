"""DCS Exporter - Exports ODCS to Data Contract Specification format for backward compatibility."""

from typing import Optional

from datacontract_specification.model import (
    Availability,
    Contact,
    DataContractSpecification,
    Field,
    Info,
    Model,
    Retention,
    Terms,
)
from datacontract_specification.model import (
    Server as DCSServer,
)
from open_data_contract_standard.model import (
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
)
from open_data_contract_standard.model import (
    Server as ODCSServer,
)

from datacontract.export.exporter import Exporter


class DcsExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> dict:
        return to_dcs_yaml(data_contract)


def to_dcs_yaml(data_contract: OpenDataContractStandard) -> str:
    """Convert ODCS to DCS and return as YAML."""
    dcs = to_dcs(data_contract)
    return dcs.to_yaml()


def to_dcs(data_contract: OpenDataContractStandard) -> DataContractSpecification:
    """Convert an ODCS data contract to a DCS data contract."""
    # Basic info
    info = Info(
        title=data_contract.name,
        version=data_contract.version,
        description=data_contract.description,
        status=data_contract.status,
    )

    # Team/owner
    if data_contract.team:
        info.owner = data_contract.team.name

    # Contact
    if data_contract.support:
        for support in data_contract.support:
            if support.channel == "email" and support.url:
                # Extract email from mailto:
                email = support.url.replace("mailto:", "") if support.url.startswith("mailto:") else None
                if email:
                    info.contact = Contact(email=email)
                    break
            elif support.channel == "other" and support.url:
                info.contact = Contact(url=support.url)

    # Create DCS spec
    dcs = DataContractSpecification(
        id=data_contract.id,
        info=info,
    )

    # Convert servers
    if data_contract.servers:
        dcs.servers = {}
        for odcs_server in data_contract.servers:
            dcs_server = _convert_server(odcs_server)
            dcs.servers[odcs_server.server] = dcs_server

    # Convert schema_ to models
    if data_contract.schema_:
        dcs.models = {}
        for schema_obj in data_contract.schema_:
            model = _convert_schema_to_model(schema_obj)
            dcs.models[schema_obj.name] = model

    # Convert description to terms
    if data_contract.description:
        terms = Terms()
        # Check for structured description
        if hasattr(data_contract, 'description') and data_contract.description:
            if isinstance(data_contract.description, str):
                terms.description = data_contract.description
            elif hasattr(data_contract.description, 'purpose'):
                terms.description = data_contract.description.purpose
                terms.usage = getattr(data_contract.description, 'usage', None)
                terms.limitations = getattr(data_contract.description, 'limitations', None)
        dcs.terms = terms

    # Convert SLA properties to service levels
    if data_contract.slaProperties:
        for sla in data_contract.slaProperties:
            if sla.property == "generalAvailability":
                if dcs.servicelevels is None:
                    dcs.servicelevels = {}
                dcs.servicelevels["availability"] = Availability(description=sla.value)
            elif sla.property == "retention":
                if dcs.servicelevels is None:
                    dcs.servicelevels = {}
                dcs.servicelevels["retention"] = Retention(period=sla.value)

    return dcs


def _convert_server(odcs_server: ODCSServer) -> DCSServer:
    """Convert an ODCS server to a DCS server."""
    dcs_server = DCSServer(type=odcs_server.type)

    # Copy common attributes
    if odcs_server.environment:
        dcs_server.environment = odcs_server.environment
    if odcs_server.account:
        dcs_server.account = odcs_server.account
    if odcs_server.database:
        dcs_server.database = odcs_server.database
    if odcs_server.schema_:
        dcs_server.schema_ = odcs_server.schema_
    if odcs_server.format:
        dcs_server.format = odcs_server.format
    if odcs_server.project:
        dcs_server.project = odcs_server.project
    if odcs_server.dataset:
        dcs_server.dataset = odcs_server.dataset
    if odcs_server.path:
        dcs_server.path = odcs_server.path
    if odcs_server.delimiter:
        dcs_server.delimiter = odcs_server.delimiter
    if odcs_server.endpointUrl:
        dcs_server.endpointUrl = odcs_server.endpointUrl
    if odcs_server.location:
        dcs_server.location = odcs_server.location
    if odcs_server.host:
        dcs_server.host = odcs_server.host
    if odcs_server.port:
        dcs_server.port = odcs_server.port
    if odcs_server.catalog:
        dcs_server.catalog = odcs_server.catalog
    if odcs_server.topic:
        dcs_server.topic = odcs_server.topic
    if odcs_server.http_path:
        dcs_server.http_path = odcs_server.http_path
    if odcs_server.driver:
        dcs_server.driver = odcs_server.driver

    return dcs_server


def _convert_schema_to_model(schema_obj: SchemaObject) -> Model:
    """Convert an ODCS SchemaObject to a DCS Model."""
    model = Model(type=schema_obj.physicalType or "table")

    if schema_obj.description:
        model.description = schema_obj.description

    # Convert properties to fields
    if schema_obj.properties:
        model.fields = {}
        for prop in schema_obj.properties:
            field = _convert_property_to_field(prop)
            model.fields[prop.name] = field

    return model


def _convert_property_to_field(prop: SchemaProperty) -> Field:
    """Convert an ODCS SchemaProperty to a DCS Field."""
    # Convert logical type back to DCS type
    dcs_type = _convert_logical_to_dcs_type(prop.logicalType, prop.physicalType)

    field = Field(type=dcs_type)

    if prop.description:
        field.description = prop.description
    if prop.required is not None:
        field.required = prop.required
    if prop.unique is not None:
        field.unique = prop.unique
    if prop.primaryKey:
        field.primaryKey = prop.primaryKey
    if prop.businessName:
        field.title = prop.businessName
    if prop.classification:
        field.classification = prop.classification
    if prop.tags:
        field.tags = prop.tags

    # Convert logical type options
    if prop.logicalTypeOptions:
        opts = prop.logicalTypeOptions
        if "minLength" in opts:
            field.minLength = opts["minLength"]
        if "maxLength" in opts:
            field.maxLength = opts["maxLength"]
        if "pattern" in opts:
            field.pattern = opts["pattern"]
        if "minimum" in opts:
            field.minimum = opts["minimum"]
        if "maximum" in opts:
            field.maximum = opts["maximum"]
        if "exclusiveMinimum" in opts:
            field.exclusiveMinimum = opts["exclusiveMinimum"]
        if "exclusiveMaximum" in opts:
            field.exclusiveMaximum = opts["exclusiveMaximum"]
        if "enum" in opts:
            field.enum = opts["enum"]
        if "format" in opts:
            field.format = opts["format"]

    # Convert custom properties
    if prop.customProperties:
        field.config = {}
        for cp in prop.customProperties:
            if cp.property == "pii":
                field.pii = cp.value
            else:
                field.config[cp.property] = cp.value

    # Convert nested properties (for object types)
    if prop.properties:
        field.fields = {}
        for nested_prop in prop.properties:
            nested_field = _convert_property_to_field(nested_prop)
            field.fields[nested_prop.name] = nested_field

    # Convert items (for array types)
    if prop.items:
        field.items = _convert_property_to_field(prop.items)

    return field


def _convert_logical_to_dcs_type(logical_type: Optional[str], physical_type: Optional[str]) -> str:
    """Convert ODCS logical type back to a DCS field type."""
    if physical_type:
        # Use physical type if available (more specific)
        pt = physical_type.lower()
        # Common physical types
        if pt in ["varchar", "text", "char", "nvarchar"]:
            return "string"
        if pt in ["int", "integer", "int32"]:
            return "integer"
        if pt in ["bigint", "int64", "long"]:
            return "long"
        if pt in ["float", "real", "float32"]:
            return "float"
        if pt in ["double", "float64"]:
            return "double"
        if pt in ["decimal", "numeric"]:
            return "decimal"
        if pt in ["timestamp", "datetime", "timestamptz"]:
            return "timestamp"
        if pt in ["date"]:
            return "date"
        if pt in ["bool", "boolean"]:
            return "boolean"
        if pt in ["bytes", "binary", "bytea"]:
            return "bytes"
        if pt in ["array"]:
            return "array"
        if pt in ["object", "struct", "record", "map", "json", "jsonb"]:
            return "object"
        # Return the physical type as-is if no mapping found
        return physical_type

    if logical_type is None:
        return "string"

    lt = logical_type.lower()
    if lt == "string":
        return "string"
    elif lt == "integer":
        return "integer"
    elif lt == "number":
        return "decimal"
    elif lt == "boolean":
        return "boolean"
    elif lt == "date":
        return "timestamp"
    elif lt == "array":
        return "array"
    elif lt == "object":
        return "object"
    else:
        return logical_type
