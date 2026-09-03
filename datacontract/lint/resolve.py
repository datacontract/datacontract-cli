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

from datacontract.config import Config
from datacontract.lint.resources import read_resource
from datacontract.lint.schema import fetch_schema
from datacontract.model.exceptions import (
    DataContractException,
    DataContractValidationErrors,
    DefinitionResolutionError,
)
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
    except_message = message

    try:
        matches = re.findall(r"\[(\d+)\]", message)
        schema_index = matches[0] if len(matches) > 0 else None
        property_index = matches[1] if len(matches) > 1 else None
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
    except Exception:
        logging.warning("YAML doesn't conform to JSON schema. Could not resolve indexed schema or property names.")
        except_message = message

    return except_message


def resolve_data_contract_dict(
    data_contract_location: str = None,
    data_contract_str: str = None,
    data_contract: OpenDataContractStandard = None,
    config: "Config | None" = None,
) -> dict:
    """Resolve a data contract and return it as a dictionary."""
    if data_contract_location is not None:
        return _to_yaml(read_resource(data_contract_location, config))
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
            engine="datacontract-cli",
        )


def resolve_data_contract(
    data_contract_location: str = None,
    data_contract_str: str = None,
    data_contract: OpenDataContractStandard = None,
    schema_location: str = None,
    inline_references: bool = False,
    all_errors: bool = False,
    config: "Config | None" = None,
) -> OpenDataContractStandard:
    """Resolve and parse a data contract from various sources."""
    if data_contract_location is not None:
        return resolve_data_contract_from_location(
            data_contract_location, schema_location, inline_references, all_errors, config
        )
    elif data_contract_str is not None:
        return _resolve_data_contract_from_str(
            data_contract_str, schema_location, inline_references, all_errors, config
        )
    elif data_contract is not None:
        return data_contract
    else:
        raise DataContractException(
            type="lint",
            result=ResultEnum.failed,
            name="Check that data contract YAML is valid",
            reason="Data contract needs to be provided",
            engine="datacontract-cli",
        )


def resolve_data_contract_from_location(
    location,
    schema_location: str = None,
    inline_references: bool = False,
    all_errors: bool = False,
    config: "Config | None" = None,
) -> OpenDataContractStandard:
    data_contract_str = read_resource(location, config)
    return _resolve_data_contract_from_str(
        data_contract_str, schema_location, inline_references, all_errors, config, base_location=location
    )


# Precedence-ordered: a property with both semantics and definition references
# resolves through semantics (matches the editor's useInheritedDefinition).
# "semantic" (singular) is accepted for back-compat with contracts written
# before the entropy-data type migration. `businessDefinition` is the ODCS type
# for "the business meaning of this field lives over there" -- it resolves like
# the others, and whether the target is a file or a URL is decided by the url's
# own shape, not by the type.
_RESOLVABLE_AUTHORITATIVE_TYPES = ("semantics", "semantic", "definition", "businessDefinition")

# A fragment-less url with one of these suffixes is read from disk. Everything
# else without a fragment stays a path on the configured host.
_DEFINITION_FILE_SUFFIXES = frozenset({".yaml", ".yml", ".json"})

# `name` and `id` are the property's own; `authoritativeDefinitions` is the link itself;
# `properties`/`items` are the contract author's structure.
_NON_MERGEABLE_FIELDS = frozenset({"id", "name", "authoritativeDefinitions", "properties", "items"})

# Per-process success-only caches: transient failures aren't cached so they
# can retry on the next run.
_definition_cache: dict[str, SchemaProperty] = {}
_local_contract_cache: dict[str, OpenDataContractStandard] = {}
_local_definition_cache: dict[str, SchemaProperty] = {}


def clear_definition_cache() -> None:
    """Drop the per-process definition caches. Used by tests."""
    _definition_cache.clear()
    _local_contract_cache.clear()
    _local_definition_cache.clear()


def inline_definitions_into_data_contract(
    data_contract: OpenDataContractStandard,
    config: "Config | None" = None,
    base_location: str | None = None,
    visited: frozenset[str] = frozenset(),
):
    """Resolve `authoritativeDefinitions[type in {semantics, definition,
    businessDefinition}]` on every property.

    `base_location` is the location the contract itself was read from; local
    file references resolve relative to it. `visited` carries the chain of files
    already being resolved, so a reference cycle is reported instead of
    recursing forever.

    In-memory only. Inline values always win. Resolution failures raise
    `DataContractException` -- a broken reference rejects the contract.
    """
    if data_contract.schema_ is None:
        return

    for schema_obj in data_contract.schema_:
        if schema_obj.properties:
            for prop in schema_obj.properties:
                inline_definition_into_property(prop, config, base_location, visited)


def inline_definition_into_property(
    prop: SchemaProperty,
    config: "Config | None" = None,
    base_location: str | None = None,
    visited: frozenset[str] = frozenset(),
):
    """Resolve and inline; recurse into nested properties and array items."""
    if prop.items is not None:
        inline_definition_into_property(prop.items, config, base_location, visited)
    if prop.properties is not None:
        for nested_prop in prop.properties:
            inline_definition_into_property(nested_prop, config, base_location, visited)

    resolved = _resolvable_reference(prop)
    if resolved is None:
        return

    type_, url = resolved
    if _is_local_reference(url):
        definition = _resolve_local_definition(url, base_location, visited, config)
    else:
        definition = _resolve_definition(url, type_, config)
    _apply_definition_to_property(prop, definition)


def _is_local_reference(url: str) -> bool:
    """True for references into a file on disk, in either of its two shapes:
    `<contract>#<fragment>`, and a bare `<file>` that is itself the definition.

    The route is chosen by the URL's shape, not by the link's type: any
    resolvable type may point at either a file or a URL, so the same syntax
    works everywhere.

    A bare file is recognized by its suffix, because a fragment-less url with
    no scheme is otherwise a path on the configured host (`url: /definitions/…`),
    which must keep resolving over HTTP.
    """
    if url.startswith("http://") or url.startswith("https://"):
        return False
    if "#" in url:
        return True
    return Path(url).suffix.lower() in _DEFINITION_FILE_SUFFIXES


def _resolvable_reference(prop: SchemaProperty) -> tuple[str, str] | None:
    """`(type, url)` of the highest-precedence resolvable authoritativeDefinition
    on `prop`, or None. Precedence: semantics > semantic > definition >
    businessDefinition."""
    for wanted_type in _RESOLVABLE_AUTHORITATIVE_TYPES:
        for ad in prop.authoritativeDefinitions or []:
            if ad.type == wanted_type and ad.url:
                return wanted_type, ad.url
    return None


def _resolve_local_definition(
    url: str, base_location: str | None, visited: frozenset[str], config: "Config | None" = None
) -> SchemaProperty:
    """Resolve a reference to a file on disk, in either of its two shapes:

      - `<contract>#schema/<schema>/properties/<property>` addresses one property
        inside a contract file.
      - `<file>` without a fragment: the file *is* the definition and holds the
        property's own elements (`businessName`, `description`, `examples`, …)
        at the top level.

    The file path is relative to the contract that holds the reference, so a set
    of files stays resolvable wherever the directory is checked out. Cached per
    resolved path, and per `path#fragment` where there is a fragment.
    """
    path_part, hash_, fragment = url.partition("#")
    if not path_part:
        raise _local_resolution_error(url, "the reference must name a contract file before the '#'")
    if hash_ and not fragment:
        raise _local_resolution_error(url, "the reference must name a fragment after the '#'")

    target_path = _resolve_local_path(url, path_part, base_location)
    cache_key = f"{target_path}#{fragment}" if fragment else str(target_path)
    if cache_key in _local_definition_cache:
        return _local_definition_cache[cache_key]

    if fragment:
        contract = _load_local_contract(url, target_path, visited, config)
        definition = _lookup_fragment(url, contract, fragment)
    else:
        definition = _load_local_property(url, target_path, visited, config)

    _local_definition_cache[cache_key] = definition
    return definition


def _resolve_local_path(url: str, path_part: str, base_location: str | None) -> Path:
    """Absolute path of the referenced file, relative to the referencing file."""
    if base_location is None:
        raise _local_resolution_error(
            url,
            "the contract was not read from a file, so there is no directory to resolve the reference against; "
            "pass the contract by file location, or use an absolute URL",
        )
    if base_location.startswith("http://") or base_location.startswith("https://"):
        raise _local_resolution_error(
            url,
            f"the contract was read from '{base_location}', and file references are only resolved for contracts "
            "read from the local file system",
        )
    return (Path(base_location).parent / path_part).resolve()


def _load_local_contract(
    url: str, contract_path: Path, visited: frozenset[str], config: "Config | None" = None
) -> OpenDataContractStandard:
    """Parse the referenced contract and resolve its own references first, so a
    chain (technical field -> business attribute -> semantic concept) resolves.
    """
    key = str(contract_path)
    if key in _local_contract_cache:
        return _local_contract_cache[key]
    if key in visited:
        raise _local_resolution_error(url, f"'{key}' is already being resolved, so the references form a cycle")
    if not contract_path.is_file():
        raise _local_resolution_error(url, f"the file '{key}' does not exist")

    try:
        contract = _resolve_data_contract_from_str(read_resource(key, config))
    except DataContractException as e:
        raise _local_resolution_error(url, f"'{key}' is not a valid data contract: {e.reason}", original_exception=e)

    inline_definitions_into_data_contract(contract, config, base_location=key, visited=visited | {key})
    _local_contract_cache[key] = contract
    return contract


def _load_local_property(
    url: str, property_path: Path, visited: frozenset[str], config: "Config | None" = None
) -> SchemaProperty:
    """Parse a file that is a definition on its own: no fragment, so the document
    holds the property's elements directly instead of a whole contract.

    Its own `authoritativeDefinitions` are resolved first, so a chain of files
    resolves the same way a chain of contracts does.
    """
    key = str(property_path)
    if key in visited:
        raise _local_resolution_error(url, f"'{key}' is already being resolved, so the references form a cycle")
    if not property_path.is_file():
        raise _local_resolution_error(url, f"the file '{key}' does not exist")

    try:
        document = _to_yaml(read_resource(key, config))
    except DataContractException as e:
        raise _local_resolution_error(url, f"'{key}' is not valid YAML: {e.reason}", original_exception=e)

    if isinstance(document, dict) and is_open_data_contract_standard(document):
        raise _local_resolution_error(
            url,
            f"'{key}' is a data contract, not a single property; add a fragment such as "
            "'#schema/<schema>/properties/<property>' to say which property is meant",
        )

    try:
        definition = SchemaProperty.model_validate(document)
    except Exception as e:
        raise _local_resolution_error(url, f"'{key}' is not a valid ODCS property: {e}", original_exception=e)

    inline_definition_into_property(definition, config, base_location=key, visited=visited | {key})
    return definition


def _lookup_fragment(url: str, contract: OpenDataContractStandard, fragment: str) -> SchemaProperty:
    """Walk `schema/<schema>/properties/<property>[/properties/<nested>|/items]…`.

    Each step matches on `id` first and falls back to `name`: contracts that
    carry stable ids use them as the referencing anchor, while `name` keeps the
    syntax usable for contracts that don't.
    """
    segments = [segment for segment in fragment.split("/") if segment]
    if len(segments) < 2 or segments[0] != "schema":
        raise _local_resolution_error(
            url, f"the fragment '{fragment}' must start with 'schema/<schema>' and end at a property"
        )

    schema_objects = contract.schema_ or []
    current = _match_by_id_or_name(schema_objects, segments[1])
    if current is None:
        raise _local_resolution_error(
            url, f"no schema object '{segments[1]}' in the contract{_available(schema_objects)}"
        )

    index = 2
    while index < len(segments):
        step = segments[index]
        if step == "items":
            if current.items is None:
                raise _local_resolution_error(url, f"'{segments[index - 1]}' has no 'items'")
            current = current.items
            index += 1
            continue
        if step != "properties" or index + 1 >= len(segments):
            raise _local_resolution_error(
                url, f"the fragment '{fragment}' must continue with 'properties/<property>' or 'items'"
            )
        wanted = segments[index + 1]
        candidates = current.properties or []
        match = _match_by_id_or_name(candidates, wanted)
        if match is None:
            raise _local_resolution_error(
                url, f"no property '{wanted}' in '{segments[index - 1]}'{_available(candidates)}"
            )
        current = match
        index += 2

    if not isinstance(current, SchemaProperty):
        raise _local_resolution_error(
            url, f"the fragment '{fragment}' points at a schema object; it must point at a property"
        )
    return current


def _match_by_id_or_name(candidates, wanted: str):
    for candidate in candidates:
        if getattr(candidate, "id", None) == wanted:
            return candidate
    for candidate in candidates:
        if candidate.name == wanted:
            return candidate
    return None


def _available(candidates) -> str:
    names = [getattr(c, "id", None) or c.name for c in candidates]
    return f" (available: {', '.join(names)})" if names else ""


def _local_resolution_error(
    url: str, detail: str, original_exception: Exception | None = None
) -> DefinitionResolutionError:
    reason = f"Could not resolve business definition '{url}': {detail}"
    logging.warning(reason)
    return DefinitionResolutionError(url=url, reason=reason, original_exception=original_exception)


def _resolve_definition(url: str, type_: str, config: "Config | None" = None) -> SchemaProperty:
    """Fetch and parse the definition or semantic concept at `url`.

    `type_` controls how an absolute URL on a different host is handled:
    a `semantics`/`semantic` URL whose host differs from the configured
    entropy-data host is treated as an IRI and routed through
    `/api/semantics?iri=...`; every other type is fetched directly
    (anonymously, so the API key never leaks). The `x-api-key` is only
    ever sent to the configured host.

    Cached per URL after a successful fetch; failures aren't cached.
    """
    if url in _definition_cache:
        return _definition_cache[url]

    target_url, headers, host_hint = _build_request(url, type_, config)

    try:
        response = requests.get(target_url, headers=headers, timeout=10)
    except requests.RequestException as e:
        raise _definition_resolution_error(url, target_url, str(e), original_exception=e, hint=host_hint)

    if response.status_code != 200:
        # 401/403 here almost always means the configured host is the wrong
        # deployment for this IRI, so surface the ENTROPY_DATA_HOST hint.
        hint = host_hint if response.status_code in (401, 403) else None
        raise _definition_resolution_error(url, target_url, f"HTTP {response.status_code} {response.reason}", hint=hint)

    try:
        definition = SchemaProperty.model_validate_json(response.content)
    except Exception as e:
        raise _definition_resolution_error(
            url, target_url, f"response body is not a valid ODCS property: {e}", original_exception=e
        )

    _definition_cache[url] = definition
    return definition


def _build_request(url: str, type_: str, config: "Config | None" = None) -> tuple[str, dict[str, str], str | None]:
    """Return the URL to fetch, the headers to use, and an optional host hint.

    The third element is a copy-pasteable ENTROPY_DATA_HOST suggestion that
    callers append to any auth/transport error from the lookup. It is only set
    for the off-host semantics IRI case below, where a host mismatch is the most
    common reason the lookup fails (401/403); it is None otherwise.

    Three cases:
      - URL on the configured host (relative path or matching absolute URL):
        fetched directly, x-api-key sent when configured.
      - Off-host `definition`/`businessDefinition` URL: fetched directly and
        anonymously -- a contract may legitimately reference a third-party REST
        URL, and the API key must never leak across hosts.
      - Off-host `semantics`/`semantic` URL: treated as an IRI and routed
        through `/api/semantics?iri=...` on the configured host. Requires an
        API key (that endpoint is API-key only). Only these two types name
        concepts by IRI; everything else is an address.
    """
    from datacontract.integration.entropy_data import _get_api_key_or_none, _get_host

    configured_host = _get_host(config)
    # urljoin keeps absolute URLs as-is and joins leading-slash paths onto
    # the host -- covers both shapes ODCS allows for `url`.
    direct_url = urljoin(configured_host, url)
    headers = {"Accept": "application/vnd.entropydata.odcs+json"}

    if _hosts_match(direct_url, configured_host):
        api_key = _get_api_key_or_none(config)
        if api_key is not None:
            headers["x-api-key"] = api_key
        return direct_url, headers, None

    if type_ not in ("semantics", "semantic"):
        # Third-party REST URL: fetch anonymously, no IRI fallback.
        return direct_url, headers, None

    # Off-host semantics reference: IRI lookup against the configured host.
    host_hint = _host_mismatch_hint(url, configured_host)
    api_key = _get_api_key_or_none(config)
    if api_key is None:
        raise _definition_resolution_error(
            url,
            f"{configured_host.rstrip('/')}/api/semantics",
            "the reference looks like an IRI, so it is resolved through /api/semantics, "
            "which requires an API key: set ENTROPY_DATA_API_KEY",
            hint=host_hint,
        )
    headers["x-api-key"] = api_key
    lookup_url = f"{configured_host.rstrip('/')}/api/semantics?iri={quote(url, safe='')}"
    return lookup_url, headers, host_hint


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


def _host_mismatch_hint(url: str, configured_host: str) -> str:
    """Actionable hint for the usual cause of a failed IRI lookup: the
    configured entropy-data host (default https://api.entropy-data.com) is not
    the deployment that serves this IRI. Names the exact ENTROPY_DATA_HOST value
    to set -- derived from the IRI's own host -- so the fix is copy-pasteable
    instead of leaving the user to guess that the host, not the API key, is wrong.
    """
    iri = urlparse(url)
    suggested = f"{iri.scheme}://{iri.netloc}" if iri.scheme and iri.netloc else iri.netloc
    return (
        f"the IRI's host '{iri.netloc}' does not match the configured entropy-data host "
        f"'{urlparse(configured_host).netloc}'; if your contract is served from "
        f"'{iri.netloc}', set ENTROPY_DATA_HOST={suggested} so the /api/semantics lookup "
        f"and your API key target that deployment"
    )


def _definition_resolution_error(
    url: str, target_url: str, detail: str, original_exception: Exception | None = None, hint: str | None = None
) -> DefinitionResolutionError:
    reason = f"Could not resolve business definition '{url}' from {target_url}: {detail}"
    if hint:
        reason = f"{reason} — {hint}"
    logging.warning(reason)
    return DefinitionResolutionError(url=url, reason=reason, original_exception=original_exception)


def _resolve_data_contract_from_str(
    data_contract_str,
    schema_location: str = None,
    inline_references: bool = False,
    all_errors: bool = False,
    config: "Config | None" = None,
    base_location: str | None = None,
) -> OpenDataContractStandard:
    yaml_dict = _to_yaml(data_contract_str)

    if not isinstance(yaml_dict, dict):
        raise DataContractException(
            type="schema",
            result=ResultEnum.failed,
            name="Parse data contract",
            reason="The data contract is empty or not a YAML mapping.",
            engine="datacontract-cli",
        )

    if is_open_data_product_standard(yaml_dict):
        logging.info("Cannot import ODPS, as not supported")
        raise DataContractException(
            type="schema",
            result=ResultEnum.failed,
            name="Parse ODCS contract",
            reason="Cannot parse ODPS product",
            engine="datacontract-cli",
        )

    if is_open_data_contract_standard(yaml_dict):
        logging.info("Importing ODCS v3")
        # When a custom JSON schema is provided, treat it as the source of
        # truth and accept extra top-level fields the standard ODCS Pydantic
        # class would reject.
        custom_schema = schema_location is not None
        if schema_location is None:
            schema_location = resources.files("datacontract").joinpath("schemas", "odcs-3.2.0.schema.json")
        _validate_json_schema(yaml_dict, schema_location, all_errors=all_errors)

        odcs = _parse_odcs_from_dict(yaml_dict, lax=custom_schema)
        if inline_references:
            inline_definitions_into_data_contract(
                odcs, config, base_location=base_location, visited=_initial_visited(base_location)
            )
        return odcs

    # For DCS format, we need to convert it to ODCS
    logging.info("Importing DCS format - converting to ODCS")
    from datacontract.imports.dcs_importer import convert_dcs_to_odcs, parse_dcs_from_dict

    dcs = parse_dcs_from_dict(yaml_dict)
    odcs = convert_dcs_to_odcs(dcs)
    if inline_references:
        inline_definitions_into_data_contract(
            odcs, config, base_location=base_location, visited=_initial_visited(base_location)
        )
    return odcs


def _initial_visited(base_location: str | None) -> frozenset[str]:
    """Seed the cycle guard with the contract being resolved, so a file that
    references itself (directly or through a chain) is reported as a cycle."""
    if base_location is None or base_location.startswith("http://") or base_location.startswith("https://"):
        return frozenset()
    return frozenset({str(Path(base_location).resolve())})


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
            engine="datacontract-cli",
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
            engine="datacontract-cli",
        )


def _validation_error_to_exception(error_message: str, original_exception=None) -> DataContractException:
    return DataContractException(
        type="lint",
        result=ResultEnum.failed,
        name="Check that data contract YAML is valid",
        reason=error_message,
        engine="datacontract-cli",
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
        except_message = _resolve_jsonschema_compliance_error_message_path(yaml_str, e.message)

        logging.warning(f"Data Contract YAML is invalid. Validation error: {except_message}")
        raise _validation_error_to_exception(except_message, original_exception=e)
    except Exception as e:
        logging.warning(f"Data Contract YAML is invalid. Validation error: {str(e)}")
        raise _validation_error_to_exception(str(e), original_exception=e)
