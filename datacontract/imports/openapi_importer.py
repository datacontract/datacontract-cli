"""Import the response of one GET operation of an OpenAPI 3.x document."""

import logging
import re
from urllib.parse import urlsplit

import yaml
from open_data_contract_standard.model import OpenDataContractStandard

from datacontract.imports.importer import Importer
from datacontract.imports.jsonschema_importer import SchemaResolver, to_schema_object
from datacontract.imports.odcs_helper import create_odcs, create_server
from datacontract.lint.resolve import _SafeLoaderNoTimestamp
from datacontract.model.exceptions import DataContractException

logger = logging.getLogger(__name__)

# the media types `datacontract test` reads from an API response
JSON_MEDIA_TYPE = re.compile(r"^application/(.+\+)?json$")
YAML_MEDIA_TYPE = re.compile(r"^(application|text)/(x-)?yaml$")


def _schema_error(reason: str) -> DataContractException:
    return DataContractException(type="schema", name="Import OpenAPI", reason=reason, engine="datacontract-cli")


class OpenApiImporter(Importer):
    def import_source(self, source: str, import_args: dict) -> OpenDataContractStandard:
        return import_openapi(source, import_args.get("openapi_operation"))


def import_openapi(source: str, operation: str | None = None) -> OpenDataContractStandard:
    """The contract of the response of one GET operation, with an API server for each server of the document."""
    try:
        with open(source, "r", encoding="utf-8") as file:
            spec = yaml.load(file, Loader=_SafeLoaderNoTimestamp)
    except (OSError, yaml.YAMLError) as e:
        raise _schema_error(f"Failed to read OpenAPI document {source}: {e}") from e
    if not isinstance(spec, dict) or not str(spec.get("openapi", "")).startswith("3."):
        raise _schema_error(f"{source} is not an OpenAPI 3.x document.")

    resolver = SchemaResolver(spec)
    path, path_item, get = _select_operation(spec, operation)
    schema = _response_schema(resolver, path, get)
    resolver.warn()
    # an array response holds the records, which the schema describes
    record = schema["items"] if schema.get("type") == "array" and isinstance(schema.get("items"), dict) else schema
    if not record.get("properties"):
        logger.warning(f"The response of GET {path} has no object properties, so the schema has no properties.")

    name = get.get("operationId") or "_".join(re.findall(r"[A-Za-z0-9]+", path)) or "root"
    odcs = create_odcs(name=spec.get("info", {}).get("title") or name)
    if spec.get("info", {}).get("version"):
        odcs.version = str(spec["info"]["version"])
    odcs.schema_ = [
        to_schema_object(
            {**_to_json_schema(record), "type": "object"}, name, get.get("summary") or get.get("description")
        )
    ]
    odcs.servers = _servers(spec, _endpoint(resolver, path, path_item, get)) or None
    return odcs


def _select_operation(spec: dict, operation: str | None) -> tuple[str, dict, dict]:
    """The path, path item, and GET operation that --operation names, or the only GET operation."""
    gets = [
        (path, item, item["get"])
        for path, item in (spec.get("paths") or {}).items()
        if isinstance(item, dict) and isinstance(item.get("get"), dict)
    ]
    if operation is not None:
        matches = [g for g in gets if operation in (g[2].get("operationId"), g[0], f"GET {g[0]}")]
    else:
        matches = gets if len(gets) == 1 else []
    if len(matches) == 1:
        return matches[0]
    available = ", ".join(f"{g[2]['operationId']} (GET {g[0]})" if g[2].get("operationId") else g[0] for g in gets)
    if not gets:
        raise _schema_error("The OpenAPI document has no GET operation.")
    if operation is None:
        raise _schema_error(f"Select one GET operation with --operation, by operationId or path: {available}")
    raise _schema_error(f"No GET operation {operation!r}. Available: {available}")


def _response_schema(resolver: SchemaResolver, path: str, get: dict) -> dict:
    """The resolved schema of the first success response with a JSON or YAML body."""
    responses = get.get("responses") or {}
    # 200 first, then the other success codes and the 2XX range
    for code in sorted((c for c in map(str, responses) if c.startswith("2")), key=lambda c: (c != "200", c)):
        response = resolver.resolve(responses.get(code) if code in responses else responses.get(int(code)))
        for media_type, body in (response.get("content") or {}).items():
            if JSON_MEDIA_TYPE.match(media_type) or YAML_MEDIA_TYPE.match(media_type):
                if isinstance(body, dict) and isinstance(body.get("schema"), dict):
                    return resolver.resolve(body["schema"])
    raise _schema_error(f"GET {path} has no success response with a JSON or YAML schema.")


def _to_json_schema(schema):
    """The schema with OpenAPI 3.0's `example` and `nullable` as JSON Schema, and nullable properties optional,
    as ODCS's `required` means not null."""
    if not isinstance(schema, dict):
        return schema
    schema = dict(schema)
    if "example" in schema and "examples" not in schema:
        schema["examples"] = [schema["example"]]
    if schema.get("nullable") is True and isinstance(schema.get("type"), str):
        schema["type"] = [schema["type"], "null"]
    if isinstance(schema.get("properties"), dict):
        schema["properties"] = {name: _to_json_schema(child) for name, child in schema["properties"].items()}
        nullable = {name for name, child in schema["properties"].items() if _admits_null(child)}
        if isinstance(schema.get("required"), list):
            schema["required"] = [name for name in schema["required"] if name not in nullable]
    for key in ("items", "additionalProperties"):
        if key in schema:
            schema[key] = _to_json_schema(schema[key])
    for key in ("anyOf", "oneOf"):
        if isinstance(schema.get(key), list):
            schema[key] = [_to_json_schema(branch) for branch in schema[key]]
    return schema


def _admits_null(schema) -> bool:
    if not isinstance(schema, dict):
        return False
    types = schema.get("type")
    branches = (schema.get("anyOf") or []) + (schema.get("oneOf") or [])
    return (isinstance(types, list) and "null" in types) or any(
        isinstance(b, dict) and b.get("type") == "null" for b in branches
    )


def _parameters(resolver: SchemaResolver, path_item: dict, get: dict) -> dict:
    """The parameters of the operation by (in, name); the operation's own replace those of its path."""
    parameters = {}
    for parameter in (path_item.get("parameters") or []) + (get.get("parameters") or []):
        parameter = resolver.resolve(parameter)
        if isinstance(parameter, dict) and "name" in parameter:
            parameters[(parameter.get("in"), parameter["name"])] = parameter
    return parameters


def _variable(parameter: dict) -> str:
    """A ${VAR} reference for the parameter's value, defaulting to its example or default value."""
    name = re.sub(r"\W", "_", parameter["name"])
    name = name if re.match(r"[A-Za-z_]", name) else f"_{name}"
    schema = parameter.get("schema") if isinstance(parameter.get("schema"), dict) else {}
    value = next(
        (v for v in (parameter.get("example"), schema.get("default"), schema.get("example")) if v is not None), None
    )
    return f"${{{name}}}" if value is None else f"${{{name}:-{value}}}"


def _endpoint(resolver: SchemaResolver, path: str, path_item: dict, get: dict) -> str:
    """The path with its parameters as variables, followed by the required query parameters."""
    parameters = _parameters(resolver, path_item, get)
    # every placeholder, even one without a declared parameter
    path = re.sub(r"\{([^}]+)\}", lambda m: _variable(parameters.get(("path", m.group(1)), {"name": m.group(1)})), path)
    query = [
        f"{name}={_variable(parameter)}"
        for (where, name), parameter in parameters.items()
        if where == "query" and parameter.get("required")
    ]
    return path + ("?" + "&".join(query) if query else "")


def _servers(spec: dict, endpoint: str) -> list:
    """An API server for each absolute server URL of the document, located at the endpoint."""
    servers = []
    for index, server in enumerate(spec.get("servers") or []):
        url = server.get("url", "") if isinstance(server, dict) else ""
        # server variables take their default, which OpenAPI requires
        for variable, definition in (server.get("variables") or {}).items():
            url = url.replace(f"{{{variable}}}", str((definition or {}).get("default", "")))
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            logger.warning(f"Skipped the server {url!r}: only absolute http(s) URLs can be tested.")
            continue
        name = "-".join(re.findall(r"[a-z0-9]+", (server.get("description") or "").lower())) or parsed.hostname
        if name in (s.server for s in servers):
            name = f"{name}-{index + 1}"
        odcs_server = create_server(name=name, server_type="api", location=url.rstrip("/") + endpoint)
        if server.get("description"):
            odcs_server.description = server["description"]
        servers.append(odcs_server)
    if not servers:
        logger.warning("The OpenAPI document has no absolute server URL, so the contract has no server to test.")
    return servers
