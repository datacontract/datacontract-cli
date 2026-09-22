"""Import structural properties of OData 4.x EntitySets from CSDL XML or JSON."""

import json
import logging
import re
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit
from xml.etree import ElementTree
from xml.etree.ElementTree import ParseError, TreeBuilder

import requests
from open_data_contract_standard.model import CustomProperty, OpenDataContractStandard, SchemaObject

from datacontract.config import Config
from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import create_odcs, create_property, create_schema_object, create_server
from datacontract.model.exceptions import DataContractException

logger = logging.getLogger(__name__)

EDMX = "{http://docs.oasis-open.org/odata/ns/edmx}"
EDM = "{http://docs.oasis-open.org/odata/ns/edm}"
ODATA_4_TYPES = {
    "Edm.String": "string",
    "Edm.Guid": "string",
    "Edm.Byte": "integer",
    "Edm.SByte": "integer",
    "Edm.Int16": "integer",
    "Edm.Int32": "integer",
    "Edm.Int64": "integer",
    "Edm.Decimal": "number",
    "Edm.Single": "number",
    "Edm.Double": "number",
    "Edm.Boolean": "boolean",
    "Edm.Date": "date",
    "Edm.DateTimeOffset": "timestamp",
    "Edm.TimeOfDay": "time",
}


def _schema_error(reason: str) -> DataContractException:
    return DataContractException(type="schema", name="Import OData metadata", reason=reason)


class _MetadataTreeBuilder(TreeBuilder):
    """Reject DTDs before the parser processes their entity declarations."""

    def doctype(self, name: str, pubid: str | None, system: str | None) -> None:
        raise ParseError("DTD declarations are not allowed in OData metadata.")


class ODataImporter(Importer):
    def import_source(self, source: str, import_args: dict, config: Config | None = None) -> OpenDataContractStandard:
        config = Config.resolve(config)
        metadata_url = import_args.get("odata_metadata_url")
        metadata_file = import_args.get("odata_metadata_file")
        service_file = import_args.get("odata_service_root_file")
        selected_names = import_args.get("odata_entity_set")
        if metadata_url is not None and metadata_file is not None:
            raise _schema_error("--metadata-url and --metadata-file are mutually exclusive.")
        _validate_http_url(source, "service-root-url", root=True)
        if selected_names is not None and (
            not isinstance(selected_names, list)
            or not selected_names
            or any(not isinstance(name, str) or not name.strip() for name in selected_names)
        ):
            raise _schema_error("--entity-set must be a non-empty list of EntitySet names.")
        root_url = source.rstrip("/") + "/"
        header_version = None
        if metadata_file is not None:
            content = _read_file(metadata_file, "metadata")
        else:
            if metadata_url is None:
                metadata_url = root_url + "$metadata"
            _validate_http_url(metadata_url, "metadata-url")
            response = _fetch_document(metadata_url, "metadata", "application/xml, application/json;q=0.9", config)
            content = response.content
            header_version = response.headers.get("OData-Version")

        # Inspect the first non-whitespace character; leave XML's encoding declaration to its parser.
        prefix = content.decode(json.detect_encoding(content), errors="ignore").lstrip("\ufeff \t\r\n")
        document = _read_xml(content) if prefix.startswith("<") else _read_json(content)
        version = _odata_version(document["version"], header_version)
        if selected_names is not None:
            selections = [(name, None) for name in selected_names]
        else:
            document_base = root_url
            if service_file is not None:
                content = _read_file(service_file, "service document")
            else:
                response = _fetch_document(root_url, "service document", "application/json", config)
                content = response.content
                # Redirects can change the base for relative context URLs.
                document_base = response.url
                service_version = response.headers.get("OData-Version")
                if service_version is not None:
                    _odata_version(service_version.strip(), service_version)
            selections = _read_service_document(content, document_base)
        if not selections:
            raise _schema_error("No EntitySets selected: the service document contains no EntitySets.")
        schemas = []
        seen = set()
        for name, entity_url in selections:
            schema = _odata_4_schema(document, name)
            if schema.name in seen:
                if selected_names is not None:
                    continue
                raise _schema_error(f"Duplicate EntitySet {schema.name!r} in the service document.")
            seen.add(schema.name)
            schema.customProperties = [
                CustomProperty(property="odataEntitySet", value=schema.name),
                CustomProperty(
                    property="odataEntitySetUrl", value=entity_url or root_url + quote(schema.name, safe="")
                ),
            ]
            schemas.append(schema)
        contract = create_odcs(name=schemas[0].name if len(schemas) == 1 else document["container_name"])
        contract.schema_ = schemas
        server = create_server(name="source", server_type="api", location=root_url)
        server.customProperties = [
            CustomProperty(property="apiType", value="odata"),
            CustomProperty(property="odataVersion", value=version),
            CustomProperty(property="odataMetadataFile", value=str(metadata_file))
            if metadata_file is not None
            else CustomProperty(property="odataMetadataUrl", value=metadata_url),
            # ODCS API servers do not allow a top-level format field.
            CustomProperty(property="format", value="json"),
        ]
        contract.servers = [server]
        return contract


def _validate_http_url(url: str, label: str, *, root: bool = False) -> None:
    try:
        parsed = urlsplit(url) if isinstance(url, str) else None
        valid = (
            parsed is not None
            and parsed.scheme in ("http", "https")
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and not any(char.isspace() for char in url)
        )
        if valid:
            parsed.port  # Validate a supplied port as well as the hostname.
        if root and valid and ("?" in url or "#" in url):
            valid = False
    except ValueError:
        valid = False
    if not valid:
        raise _schema_error(
            f"Invalid {label}: expected an HTTP(S) URL without embedded credentials. "
            "The service root must not contain a query or fragment."
        )


def _read_file(path: str | Path, label: str) -> bytes:
    try:
        return Path(path).read_bytes()
    except (OSError, ValueError) as exc:
        raise _schema_error(f"Failed to read OData {label} file {path}: {exc}") from exc


class _ODataSession(requests.Session):
    """Keep Requests' redirect policy without introducing .netrc credentials."""

    def rebuild_auth(self, prepared_request: requests.PreparedRequest, response: requests.Response) -> None:
        if self.should_strip_auth(response.request.url, prepared_request.url):
            prepared_request.headers.pop("Authorization", None)


def _fetch_document(url: str, label: str, accept: str, config: Config) -> requests.Response:
    headers = {"Accept": accept}
    authorization = config.get_api_header_authorization()
    if authorization is not None:
        headers["Authorization"] = authorization
    try:
        with _ODataSession() as session:
            response = session.get(
                url,
                headers=headers,
                timeout=30,
                # Prevent .netrc from replacing the header on the initial request.
                auth=lambda request: request,
            )
            response.raise_for_status()
        return response
    except requests.RequestException as exc:
        detail = type(exc).__name__
        if exc.response is not None:
            detail += f" (HTTP {exc.response.status_code})"
        # InvalidHeader and other transport errors may include credentials in their text.
        raise DataContractException(
            type="connection",
            name=f"Fetch OData {label}",
            reason=f"Failed to fetch OData {label}: {detail}.",
        ) from None


def _context_base(obj: dict, base: str) -> str:
    context = obj.get("@odata.context", obj.get("@context"))
    if "@odata.context" not in obj and "@context" not in obj:
        return base
    if not isinstance(context, str) or not context:
        raise _schema_error("Invalid context URL in OData service document.")
    if "@odata.context" in obj and "@context" in obj and obj["@odata.context"] != obj["@context"]:
        raise _schema_error("Conflicting context URLs in OData service document.")
    try:
        result = urljoin(base, context)
    except ValueError as exc:
        raise _schema_error(f"Invalid context URL in OData service document: {exc}") from exc
    _validate_http_url(result, "service document context")
    return result


def _read_service_document(content: bytes, base: str) -> list[tuple[str, str]]:
    document = _json_object(_load_json(content, "service document"), "the service document")
    if "@odata.context" not in document and "@context" not in document:
        raise _schema_error("Expected an OData service document with a context URL and a value array.")
    base = _context_base(document, base)
    entries = document.get("value")
    if not isinstance(entries, list):
        raise _schema_error("Expected a value array in the OData service document.")
    selections, names = [], set()
    for entry in entries:
        entry = _json_object(entry, "service document entry")
        kind = entry.get("kind", "EntitySet")
        if not isinstance(kind, str):
            raise _schema_error("Invalid kind in OData service document: expected a string.")
        if kind != "EntitySet":
            continue  # Singletons, operations and linked services are not imported.
        name, url = entry.get("name"), entry.get("url")
        if not isinstance(name, str) or not name.strip() or not isinstance(url, str) or not url.strip():
            raise _schema_error("Each service document EntitySet must have a non-empty string name and url.")
        if name in names:
            raise _schema_error(f"Duplicate EntitySet {name!r} in the service document.")
        names.add(name)
        try:
            entity_url = urljoin(_context_base(entry, base), url)
        except ValueError as exc:
            raise _schema_error(f"Invalid service document URL for EntitySet {name!r}: {exc}") from exc
        _validate_http_url(entity_url, f"EntitySet {name!r} URL")
        selections.append((name, entity_url))
    return selections


def _odata_version(document_version: object, header: str | None) -> str:
    """Select the supported protocol family independently of its schema mapping."""
    version = header.strip() if header is not None else document_version
    if any(
        not isinstance(value, str) or re.fullmatch(r"4\.[0-9]+", value) is None for value in (document_version, version)
    ):
        raise _schema_error(
            f"Unsupported OData version (header={header!r}, document={document_version!r}); "
            "expected an OData 4.x version in the form 4.[0-9]+."
        )
    if version != document_version:
        raise _schema_error(f"Conflicting OData versions: header={version}, document={document_version}.")
    return version


def _read_xml(content: bytes) -> dict:
    try:
        root = ElementTree.fromstring(content, parser=ElementTree.XMLParser(target=_MetadataTreeBuilder()))
    except (ParseError, LookupError, ValueError) as exc:
        raise _schema_error(f"Invalid or unsafe OData XML metadata: {exc}") from exc
    if root.tag != f"{EDMX}Edmx":
        raise _schema_error("Expected an OData 4 Edmx document with the OData 4 XML namespace.")
    containers = root.findall(f"{EDMX}DataServices/{EDM}Schema/{EDM}EntityContainer")
    if len(containers) != 1 or not containers[0].get("Name"):
        raise _schema_error(
            "The XML service EntityContainer is not found or ambiguous; expected exactly one named container."
        )
    document = {
        "version": root.get("Version"),
        "container_name": containers[0].get("Name"),
        "entity_sets": [],
        "types": [],
    }
    for schema in root.findall(f"{EDMX}DataServices/{EDM}Schema"):
        for container in schema.findall(f"{EDM}EntityContainer"):
            for entity_set in container.findall(f"{EDM}EntitySet"):
                document["entity_sets"].append(
                    {
                        "name": entity_set.get("Name"),
                        "type": entity_set.get("EntityType"),
                        "extends": container.get("Extends"),
                    }
                )
        for entity_type in schema.findall(f"{EDM}EntityType"):
            fields = []
            for field in entity_type.findall(f"{EDM}Property"):
                facets = {}
                for key in ("MaxLength", "Precision", "Scale"):
                    value = field.get(key)
                    if value is not None:
                        try:
                            value = int(value)
                        except ValueError:
                            pass  # Preserve symbolic values for validation during mapping.
                        facets[key] = value
                if field.get("Type") == "Edm.Decimal":
                    facets.setdefault("Scale", 0)
                fields.append(
                    {
                        "name": field.get("Name"),
                        "type": field.get("Type"),
                        "nullable": {"true": True, "false": False}.get(
                            field.get("Nullable", "true"), field.get("Nullable")
                        ),
                        "collection": False,
                        "facets": facets,
                    }
                )
            document["types"].append(
                {
                    "names": {
                        f"{prefix}.{entity_type.get('Name')}"
                        for prefix in (schema.get("Namespace"), schema.get("Alias"))
                        if prefix
                    },
                    "base_type": entity_type.get("BaseType"),
                    "keys": [key.get("Name") for key in entity_type.findall(f"{EDM}Key/{EDM}PropertyRef")],
                    "fields": fields,
                    "navigation": [prop.get("Name") for prop in entity_type.findall(f"{EDM}NavigationProperty")],
                }
            )
    return document


def _json_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise _schema_error(f"Duplicate JSON key {key!r} in OData JSON document.")
        result[key] = value
    return result


def _json_object(value: object, context: str) -> dict:
    if not isinstance(value, dict):
        raise _schema_error(f"Expected a JSON object for {context} in OData metadata.")
    return value


def _load_json(content: bytes, label: str) -> object:
    def reject_constant(value: str):
        raise _schema_error(f"Invalid JSON constant {value!r} in OData metadata.")

    try:
        return json.loads(content, object_pairs_hook=_json_pairs, parse_constant=reject_constant)
    except (ValueError, UnicodeError) as exc:
        raise _schema_error(f"Invalid or unsafe OData JSON {label}: {exc}") from exc


def _read_json(content: bytes) -> dict:
    root = _json_object(_load_json(content, "metadata"), "the CSDL document")
    if "$Version" not in root and "value" in root and ("@odata.context" in root or "@context" in root):
        raise _schema_error(
            "This is an OData service/data document, not CSDL metadata. Supply the $metadata document with field definitions."
        )
    container_name = root.get("$EntityContainer")
    if not isinstance(container_name, str) or "." not in container_name:
        raise _schema_error("CSDL JSON metadata requires a namespace-qualified $EntityContainer.")
    namespace, _, local_name = container_name.rpartition(".")
    container_schema = _json_object(root.get(namespace), f"schema {namespace!r}")
    container = _json_object(container_schema.get(local_name), f"$EntityContainer {container_name!r}")
    if container.get("$Kind") != "EntityContainer":
        raise _schema_error(f"{container_name!r} must have $Kind EntityContainer.")
    if "$Extends" in container:
        raise _schema_error(f"EntityContainer {container_name!r} uses unsupported inheritance ($Extends).")
    document = {"version": root.get("$Version"), "container_name": local_name, "entity_sets": [], "types": []}
    for name, member in container.items():
        if name.startswith("$") or "@" in name:
            continue
        member = _json_object(member, f"container member {name!r}")
        collection = member.get("$Collection", False)
        if type(collection) is not bool:
            raise _schema_error(f"Invalid $Collection for container member {name!r}: expected a boolean.")
        if collection:
            document["entity_sets"].append({"name": name, "type": member.get("$Type"), "extends": None})
    for namespace, schema in root.items():
        if namespace.startswith("$") or "@" in namespace:
            continue
        schema = _json_object(schema, f"schema {namespace!r}")
        alias = schema.get("$Alias")
        if "$Alias" in schema and not isinstance(alias, str):
            raise _schema_error(f"Invalid $Alias in schema {namespace!r}: expected a string.")
        for type_name, entity_type in schema.items():
            if type_name.startswith("$") or "@" in type_name:
                continue
            # Action/function overloads are arrays; only entity types are needed.
            if not isinstance(entity_type, dict) or entity_type.get("$Kind") != "EntityType":
                continue
            if "$BaseType" in entity_type and not isinstance(entity_type["$BaseType"], str):
                raise _schema_error(f"Invalid $BaseType for {namespace}.{type_name}: expected a qualified type name.")
            fields, navigation = [], []
            for field_name, field in entity_type.items():
                if field_name.startswith("$") or "@" in field_name:
                    continue
                field = _json_object(field, f"field {namespace}.{type_name}.{field_name}")
                kind = field.get("$Kind", "Property")
                if kind == "NavigationProperty":
                    navigation.append(field_name)
                    continue
                facets = {key: field[f"${key}"] for key in ("MaxLength", "Precision", "Scale") if f"${key}" in field}
                if field.get("$Type") == "Edm.Decimal":
                    facets.setdefault("Scale", "variable")
                fields.append(
                    {
                        "name": field_name,
                        "type": field.get("$Type", "Edm.String"),
                        "nullable": field.get("$Nullable", False),
                        "collection": field.get("$Collection", False),
                        "facets": facets,
                        "kind": kind,
                    }
                )
            document["types"].append(
                {
                    "names": {f"{prefix}.{type_name}" for prefix in (namespace, alias) if prefix},
                    "base_type": entity_type.get("$BaseType"),
                    "keys": entity_type.get("$Key", []),
                    "fields": fields,
                    "navigation": navigation,
                }
            )
    return document


def _odata_4_schema(document: dict, requested_name: str) -> SchemaObject:
    entity_sets = document["entity_sets"]
    matches = [entity_set for entity_set in entity_sets if entity_set["name"] == requested_name]
    if not matches:
        matches = [
            entity_set
            for entity_set in entity_sets
            if (entity_set["name"] or "").casefold() == requested_name.casefold()
        ]
    if len(matches) != 1:
        raise _schema_error(
            f"EntitySet {requested_name!r} is {'ambiguous' if matches else 'not found'} in the metadata."
        )
    entity_set = matches[0]
    name, type_name = entity_set["name"], entity_set["type"]
    if entity_set["extends"]:
        raise _schema_error(f"EntitySet {name!r} uses unsupported container inheritance (Extends).")
    if not isinstance(type_name, str):
        raise _schema_error(f"Invalid EntityType for EntitySet {name!r}: expected a qualified type name.")
    types = [entity_type for entity_type in document["types"] if type_name in entity_type["names"]]
    if len(types) != 1:
        raise _schema_error(
            f"EntityType {type_name!r} for EntitySet {name!r} must resolve uniquely within this metadata document. "
            "External metadata references are not fetched."
        )
    entity_type = types[0]
    if entity_type["base_type"] is not None:
        raise _schema_error(f"EntityType {type_name!r} uses unsupported inheritance (BaseType).")
    key_names, fields = entity_type["keys"], entity_type["fields"]
    field_names = [field["name"] for field in fields]
    if any(not name for name in field_names) or len(set(field_names)) != len(field_names):
        raise _schema_error(f"EntityType {type_name!r} has missing or duplicate property names.")
    if (
        not isinstance(key_names, list)
        or any(not isinstance(key, str) for key in key_names)
        or len(set(key_names)) != len(key_names)
        or any(key not in field_names for key in key_names)
    ):
        raise _schema_error(f"EntityType {type_name!r} has invalid or unsupported key references: {key_names}.")
    properties = []
    for field in fields:
        field_name, field_type = field["name"], field["type"]
        if field.get("kind", "Property") != "Property":
            raise _schema_error(f"Unsupported $Kind for field {name}.{field_name}: {field['kind']!r}.")
        if type(field["collection"]) is not bool:
            raise _schema_error(f"Invalid $Collection for field {name}.{field_name}: expected a boolean.")
        if not isinstance(field_type, str) or field_type not in ODATA_4_TYPES or field["collection"]:
            raise _schema_error(
                f"Unsupported OData type {field_type!r} for field {name}.{field_name}. "
                "Only supported primitive types can be imported; complex, collection, enum types and type definitions "
                "are not supported."
            )
        nullable = field["nullable"]
        if type(nullable) is not bool:
            raise _schema_error(f"Invalid Nullable value {nullable!r} for field {name}.{field_name}.")
        is_key = field_name in key_names
        if is_key and nullable:
            raise _schema_error(f"Key field {name}.{field_name} must declare Nullable=false.")
        facets = {}
        for facet, value in field["facets"].items():
            if facet == "MaxLength" and value == "max":
                continue
            if facet == "Scale" and isinstance(value, str) and value.lower() in ("variable", "floating"):
                facets["custom_properties"] = {"scale": value.lower()}
                continue
            if type(value) is not int or value < 0 or (facet == "MaxLength" and value == 0):
                raise _schema_error(f"Invalid {facet} value {value!r} for field {name}.{field_name}.")
            facets[{"MaxLength": "max_length", "Precision": "precision", "Scale": "scale"}[facet]] = value
        properties.append(
            create_property(
                name=field_name,
                logical_type=ODATA_4_TYPES[field_type],
                physical_type=field_type,
                required=not nullable,
                primary_key=is_key,
                primary_key_position=key_names.index(field_name) + 1 if is_key else None,
                format="uuid" if field_type == "Edm.Guid" else None,
                **facets,
            )
        )
    for navigation in entity_type["navigation"]:
        logger.warning("Omitting OData navigation property %s.%s from the imported schema.", name, navigation)
    return create_schema_object(name=name, physical_type="object", properties=properties)
