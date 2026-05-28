import importlib.resources as resources
import logging
import re
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

import fastjsonschema
import requests
import yaml
from fastjsonschema import JsonSchemaValueException
from jsonschema import validators
from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty
from pydantic import ConfigDict

from datacontract.lint.resources import read_resource
from datacontract.lint.schema import fetch_schema
from datacontract.model.exceptions import DataContractException, DataContractValidationErrors
from datacontract.model.odcs import is_open_data_contract_standard, is_open_data_product_standard
from datacontract.model.run import ResultEnum


class _LaxOpenDataContractStandard(OpenDataContractStandard):
    """ODCS variant that accepts unknown top-level fields.

    Used when the contract is validated against a user-supplied JSON schema
    (`--json-schema`): the custom schema is the source of truth, so the
    Pydantic step must not re-reject extras the schema already accepted.
    """

    model_config = ConfigDict(extra="allow")


class _SafeLoaderNoTimestamp(yaml.SafeLoader):
    """SafeLoader that keeps dates/timestamps as strings instead of converting to datetime objects."""

    pass


# Remove the timestamp implicit resolver so dates like 2022-01-15 stay as strings
_SafeLoaderNoTimestamp.yaml_implicit_resolvers = {
    k: [(tag, regexp) for tag, regexp in v if tag != "tag:yaml.org,2002:timestamp"]
    for k, v in _SafeLoaderNoTimestamp.yaml_implicit_resolvers.copy().items()
}


def _resolve_jsonschema_compliance_error_message_path(yaml_str, message):
    matches = re.findall(r"\[(\d+)\]", message)
    schema_index = matches[0] if len(matches) > 0 else None
    property_index = matches[1] if len(matches) > 1 else None
    except_message = message
    if schema_index is not None and "schema" in yaml_str and int(schema_index) < len(yaml_str["schema"]):
        except_message = except_message.replace(
            f"schema[{schema_index}]", f"schema.{yaml_str['schema'][int(schema_index)]['name']}"
        )

    if (
        property_index is not None
        and "schema" in yaml_str
        and int(schema_index) < len(yaml_str["schema"])
        and "properties" in yaml_str["schema"][int(schema_index)]
        and int(property_index) < len(yaml_str["schema"][int(schema_index)]["properties"])
    ):
        except_message = except_message.replace(
            f"properties[{property_index}]",
            f"properties.{yaml_str['schema'][int(schema_index)]['properties'][int(property_index)]['name']}",
        )
    return except_message


def resolve_data_contract_dict(
    data_contract_location: str = None,
    data_contract_str: str = None,
    data_contract: OpenDataContractStandard = None,
) -> dict:
    """Resolve a data contract and return it as a dictionary."""
    if data_contract_location is not None:
        return _to_yaml(read_resource(data_contract_location))
    elif data_contract_str is not None:
        return _to_yaml(data_contract_str)
    elif data_contract is not None:
        return data_contract.model_dump()
    else:
        raise DataContractException(
            type="lint",
            result=ResultEnum.failed,
            name="Check that data contract YAML is valid",
            reason="Data contract needs to be provided",
            engine="datacontract",
        )


def resolve_data_contract(
    data_contract_location: str = None,
    data_contract_str: str = None,
    data_contract: OpenDataContractStandard = None,
    schema_location: str = None,
    inline_references: bool = False,
    all_errors: bool = False,
) -> OpenDataContractStandard:
    """Resolve and parse a data contract from various sources."""
    if data_contract_location is not None:
        return resolve_data_contract_from_location(
            data_contract_location, schema_location, inline_references, all_errors
        )
    elif data_contract_str is not None:
        return _resolve_data_contract_from_str(data_contract_str, schema_location, inline_references, all_errors)
    elif data_contract is not None:
        return data_contract
    else:
        raise DataContractException(
            type="lint",
            result=ResultEnum.failed,
            name="Check that data contract YAML is valid",
            reason="Data contract needs to be provided",
            engine="datacontract",
        )


def resolve_data_contract_from_location(
    location, schema_location: str = None, inline_references: bool = False, all_errors: bool = False
) -> OpenDataContractStandard:
    data_contract_str = read_resource(location)
    return _resolve_data_contract_from_str(data_contract_str, schema_location, inline_references, all_errors)


# Precedence-ordered: a property with both semantics and definition references
# resolves through semantics (matches the editor's useInheritedDefinition).
# "semantic" (singular) is accepted for back-compat with contracts written
# before the entropy-data type migration.
_RESOLVABLE_AUTHORITATIVE_TYPES = ("semantics", "semantic", "definition")

# `name` and `id` are the property's own; `authoritativeDefinitions` is the link itself;
# `properties`/`items` are the contract author's structure.
_NON_MERGEABLE_FIELDS = frozenset({"id", "name", "authoritativeDefinitions", "properties", "items"})

# Per-process success-only cache: transient failures aren't cached so they
# can retry on the next run.
_definition_cache: dict[str, SchemaProperty] = {}


def clear_definition_cache() -> None:
    """Drop the per-process definition cache. Used by tests."""
    _definition_cache.clear()


def inline_definitions_into_data_contract(data_contract: OpenDataContractStandard):
    """Resolve `authoritativeDefinitions[type in {semantics, definition}]` on
    every property.

    In-memory only. Inline values always win. Resolution failures raise
    `DataContractException` -- a broken reference rejects the contract.
    """
    if data_contract.schema_ is None:
        return

    for schema_obj in data_contract.schema_:
        if schema_obj.properties:
            for prop in schema_obj.properties:
                inline_definition_into_property(prop)


def inline_definition_into_property(prop: SchemaProperty):
    """Resolve and inline; recurse into nested properties and array items."""
    if prop.items is not None:
        inline_definition_into_property(prop.items)
    if prop.properties is not None:
        for nested_prop in prop.properties:
            inline_definition_into_property(nested_prop)

    resolved = _resolvable_reference(prop)
    if resolved is None:
        return

    type_, url = resolved
    definition = _resolve_definition(url, type_)
    _apply_definition_to_property(prop, definition)


def _resolvable_reference(prop: SchemaProperty) -> tuple[str, str] | None:
    """`(type, url)` of the highest-precedence resolvable authoritativeDefinition
    on `prop`, or None. Precedence: semantics > semantic > definition."""
    for wanted_type in _RESOLVABLE_AUTHORITATIVE_TYPES:
        for ad in prop.authoritativeDefinitions or []:
            if ad.type == wanted_type and ad.url:
                return wanted_type, ad.url
    return None


def _resolve_definition(url: str, type_: str) -> SchemaProperty:
    """Fetch and parse the definition or semantic concept at `url`.

    `type_` controls how an absolute URL on a different host is handled:
    a `semantics`/`semantic` URL whose host differs from the configured
    entropy-data host is treated as an IRI and routed through
    `/api/semantics?iri=...`; a `definition` URL is fetched directly
    (anonymously, so the API key never leaks). The `x-api-key` is only
    ever sent to the configured host.

    Cached per URL after a successful fetch; failures aren't cached.
    """
    if url in _definition_cache:
        return _definition_cache[url]

    target_url, headers = _build_request(url, type_)

    try:
        response = requests.get(target_url, headers=headers, timeout=10)
    except requests.RequestException as e:
        raise _definition_resolution_error(url, target_url, str(e), original_exception=e)

    if response.status_code != 200:
        raise _definition_resolution_error(url, target_url, f"HTTP {response.status_code} {response.reason}")

    try:
        definition = SchemaProperty.model_validate_json(response.content)
    except Exception as e:
        raise _definition_resolution_error(
            url, target_url, f"response body is not a valid ODCS property: {e}", original_exception=e
        )

    _definition_cache[url] = definition
    return definition


def _build_request(url: str, type_: str) -> tuple[str, dict[str, str]]:
    """Return the URL to fetch and the headers to use for a given reference.

    Three cases:
      - URL on the configured host (relative path or matching absolute URL):
        fetched directly, x-api-key sent when configured.
      - Off-host `definition` URL: fetched directly and anonymously -- a
        contract may legitimately reference a third-party REST URL, and the
        API key must never leak across hosts.
      - Off-host `semantics`/`semantic` URL: treated as an IRI and routed
        through `/api/semantics?iri=...` on the configured host. Requires an
        API key (that endpoint is API-key only).
    """
    from datacontract.integration.entropy_data import _get_api_key_or_none, _get_host

    configured_host = _get_host()
    # urljoin keeps absolute URLs as-is and joins leading-slash paths onto
    # the host -- covers both shapes ODCS allows for `url`.
    direct_url = urljoin(configured_host, url)
    headers = {"Accept": "application/vnd.entropydata.odcs+json"}

    if _hosts_match(direct_url, configured_host):
        api_key = _get_api_key_or_none()
        if api_key is not None:
            headers["x-api-key"] = api_key
        return direct_url, headers

    if type_ == "definition":
        # Third-party REST URL: fetch anonymously, no IRI fallback.
        return direct_url, headers

    # Off-host semantics reference: IRI lookup against the configured host.
    api_key = _get_api_key_or_none()
    if api_key is None:
        raise _definition_resolution_error(
            url,
            f"{configured_host.rstrip('/')}/api/semantics",
            "the reference looks like an IRI (host does not match the configured "
            "entropy-data host); resolving an IRI goes through /api/semantics which "
            "requires an API key (set ENTROPY_DATA_API_KEY)",
        )
    headers["x-api-key"] = api_key
    lookup_url = f"{configured_host.rstrip('/')}/api/semantics?iri={quote(url, safe='')}"
    return lookup_url, headers


def _apply_definition_to_property(prop: SchemaProperty, definition: SchemaProperty):
    """Inline the definition's set fields where the property left them unset.

    "Set" follows pydantic's `model_fields_set`, so `description: ""`
    counts as set and is preserved.
    """
    author_set = set(prop.model_fields_set)
    for field in definition.model_fields_set:
        if field in _NON_MERGEABLE_FIELDS or field in author_set:
            continue
        setattr(prop, field, getattr(definition, field))


def _hosts_match(url: str, host: str) -> bool:
    """True when both URLs have the same netloc (host + port if specified)."""
    return urlparse(url).netloc == urlparse(host).netloc


def _definition_resolution_error(
    url: str, target_url: str, detail: str, original_exception: Exception | None = None
) -> DataContractException:
    reason = f"Could not resolve business definition '{url}' from {target_url}: {detail}"
    logging.warning(reason)
    return DataContractException(
        type="lint",
        result=ResultEnum.failed,
        name="Resolve business definition",
        reason=reason,
        engine="datacontract",
        original_exception=original_exception,
    )


def _resolve_data_contract_from_str(
    data_contract_str, schema_location: str = None, inline_references: bool = False, all_errors: bool = False
) -> OpenDataContractStandard:
    yaml_dict = _to_yaml(data_contract_str)

    if is_open_data_product_standard(yaml_dict):
        logging.info("Cannot import ODPS, as not supported")
        raise DataContractException(
            type="schema",
            result=ResultEnum.failed,
            name="Parse ODCS contract",
            reason="Cannot parse ODPS product",
            engine="datacontract",
        )

    if is_open_data_contract_standard(yaml_dict):
        logging.info("Importing ODCS v3")
        # When a custom JSON schema is provided, treat it as the source of
        # truth and accept extra top-level fields the standard ODCS Pydantic
        # class would reject.
        custom_schema = schema_location is not None
        if schema_location is None:
            schema_location = resources.files("datacontract").joinpath("schemas", "odcs-3.1.0.schema.json")
        _validate_json_schema(yaml_dict, schema_location, all_errors=all_errors)

        odcs = _parse_odcs_from_dict(yaml_dict, lax=custom_schema)
        if inline_references:
            inline_definitions_into_data_contract(odcs)
        return odcs

    # For DCS format, we need to convert it to ODCS
    logging.info("Importing DCS format - converting to ODCS")
    from datacontract.imports.dcs_importer import convert_dcs_to_odcs, parse_dcs_from_dict

    dcs = parse_dcs_from_dict(yaml_dict)
    odcs = convert_dcs_to_odcs(dcs)
    if inline_references:
        inline_definitions_into_data_contract(odcs)
    return odcs


def _parse_odcs_from_dict(yaml_dict: dict, lax: bool = False) -> OpenDataContractStandard:
    """Parse ODCS from a dictionary."""
    cls = _LaxOpenDataContractStandard if lax else OpenDataContractStandard
    try:
        return cls(**yaml_dict)
    except Exception as e:
        raise DataContractException(
            type="schema",
            name="Parse ODCS contract",
            reason=f"Failed to parse ODCS contract: {str(e)}",
            engine="datacontract",
            original_exception=e,
        )


def _to_yaml(data_contract_str) -> dict:
    try:
        return yaml.load(data_contract_str, Loader=_SafeLoaderNoTimestamp)
    except Exception as e:
        logging.warning(f"Cannot parse YAML. Error: {str(e)}")
        raise DataContractException(
            type="lint",
            result="failed",
            name="Check that data contract YAML is valid",
            reason=f"Cannot parse YAML. Error: {str(e)}",
            engine="datacontract",
        )


def _validation_error_to_exception(error_message: str, original_exception=None) -> DataContractException:
    return DataContractException(
        type="lint",
        result=ResultEnum.failed,
        name="Check that data contract YAML is valid",
        reason=error_message,
        engine="datacontract",
        original_exception=original_exception,
    )


def _validate_json_schema(yaml_str, schema_location: str | Path = None, all_errors: bool = False):
    logging.debug(f"Linting data contract with schema at {schema_location}")
    schema = fetch_schema(schema_location)
    if all_errors:
        validator_cls = validators.validator_for(schema)
        validator_cls.check_schema(schema)
        validator = validator_cls(schema=schema)
        errors = sorted(validator.iter_errors(yaml_str), key=lambda error: list(error.path))
        if errors:
            logging.warning(f"Data Contract YAML is invalid. Validation errors: {len(errors)}")
            raise DataContractValidationErrors(
                [_validation_error_to_exception(error.message, original_exception=error) for error in errors]
            )
        logging.debug("YAML data is valid.")
        return
    try:
        fastjsonschema.validate(schema, yaml_str, use_default=False)
        logging.debug("YAML data is valid.")
    except JsonSchemaValueException as e:
        try:
            except_message = _resolve_jsonschema_compliance_error_message_path(yaml_str, e.message)
        except Exception:
            logging.warning("YAML doesn't conform to JSON schema. Attempting to resolve error message path.")
            except_message = e.message
        finally:
            logging.warning(f"Data Contract YAML is invalid. Validation error: {except_message}")
            raise _validation_error_to_exception(except_message, original_exception=e)
    except Exception as e:
        logging.warning(f"Data Contract YAML is invalid. Validation error: {str(e)}")
        raise _validation_error_to_exception(str(e), original_exception=e)
