"""Variable references in string values, per ODCS v3.2.0 (RFC 0050).

Any string value in a data contract may contain ``${VAR_NAME}`` or, with an
inline default, ``${VAR_NAME:-default}``. References are resolved from the
process environment (which includes a loaded ``.env`` file) at the moment a
value is *used*: when a connection is opened or a quality query is executed.
The loaded contract itself is never mutated, so ``export`` and ``publish``
write the references back verbatim.

A reference to an unset or empty variable without a default is an error;
an empty string is never substituted silently.
An untrusted contract resolves only the allow-listed part of the environment.
"""

import fnmatch
import os
import re
from typing import Iterable, Mapping, Optional

from open_data_contract_standard.model import Server
from pydantic import BaseModel

_VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")

CONTRACT_VARIABLES_ENV = "DATACONTRACT_CLI_API_CONTRACT_VARIABLES"


class VariableError(ValueError):
    """A ``${VAR}`` reference could not be turned into a usable value."""


class UnresolvedVariableError(VariableError):
    """A ``${VAR}`` reference names a variable that is unset and has no default."""

    def __init__(self, name: str, source: str = "", restricted: bool = False):
        self.name = name
        where = f" in {source}" if source else ""
        # "Not listed" must read like "not set", or the message enumerates the host's environment.
        if restricted:
            reason = "is not available. Check if the API permits the resolution (--contract-variables needs to be set)."
        else:
            reason = f"is not set. Set it in the environment or a .env file, or use ${{{name}:-default}}."
        super().__init__(f"Variable {name} referenced{where} {reason}")


def allowed_environment(patterns: Iterable[str]) -> dict[str, str]:
    """The environment entries whose names match one of the ``fnmatch`` ``patterns``."""
    globs = [pattern.strip() for pattern in patterns if pattern and pattern.strip()]
    return {name: value for name, value in os.environ.items() if any(fnmatch.fnmatchcase(name, glob) for glob in globs)}


# The ODCS enums a reference must resolve into, by (model, field); a test keeps them in step with the schema.
_ENUM_VALUES: dict[tuple[str, str], frozenset[str]] = {
    ("Server", "type"): frozenset(
        {
            "api",
            "athena",
            "azure",
            "bigquery",
            "btrieve",
            "clickhouse",
            "databricks",
            "denodo",
            "dremio",
            "duckdb",
            "exasol",
            "fastobjects",
            "glue",
            "hana",
            "cloudsql",
            "db2",
            "hive",
            "iceberg",
            "impala",
            "informix",
            "ingres",
            "kafka",
            "kinesis",
            "local",
            "mysql",
            "oracle",
            "poet",
            "postgresql",
            "postgres",
            "presto",
            "pubsub",
            "redshift",
            "s3",
            "sftp",
            "snowflake",
            "sqlserver",
            "synapse",
            "teradata",
            "trino",
            "vectorwise",
            "versant",
            "vertica",
            "zen",
            "custom",
        }
    ),
    ("DataQuality", "metric"): frozenset(
        {"nullValues", "missingValues", "invalidValues", "duplicateValues", "rowCount"}
    ),
    ("DataQuality", "type"): frozenset({"text", "library", "sql", "custom"}),
    ("DataQuality", "dimension"): frozenset(
        {"accuracy", "completeness", "conformity", "consistency", "coverage", "timeliness", "uniqueness"}
    ),
    ("SchemaObject", "logicalType"): frozenset({"object", "blob"}),
    ("SchemaProperty", "logicalType"): frozenset(
        {
            "string",
            "date",
            "timestamp",
            "time",
            "number",
            "integer",
            "boolean",
            "object",
            "array",
            "map",
            "vector",
        }
    ),
}


class InvalidVariableValueError(VariableError):
    """A reference resolved outside the field's enum. Never quotes the value: it may be a secret."""

    def __init__(self, reference: str, source: str, allowed: frozenset[str]):
        super().__init__(
            f"{source} resolved {reference} into an invalid value. Expected one of: {', '.join(sorted(allowed))}."
        )


def _checked(original, resolved, owner: str, field: str, source: str):
    """Reject a resolved value the field's ODCS enum does not accept."""
    allowed = _ENUM_VALUES.get((owner, field))
    if allowed is None or not contains_variables(original) or resolved in allowed:
        return resolved
    raise InvalidVariableValueError(original, source, allowed)


def contains_variables(value) -> bool:
    """True if ``value`` is a string holding at least one ``${VAR}`` reference."""
    return isinstance(value, str) and _VARIABLE.search(value) is not None


def resolve_variables(value, source: str = "", variables: Optional[Mapping[str, str]] = None):
    """Return ``value`` with every ``${VAR}`` reference replaced.

    Non-string values pass through unchanged. ``source`` names the value in
    the error message (``"server 'prod' host"``, ``"config file x.yaml"``).
    ``variables`` replaces the process environment for an untrusted contract.
    """
    if not isinstance(value, str):
        return value
    environment = os.environ if variables is None else variables

    def replace(match: re.Match) -> str:
        name, default = match.group(1), match.group(2)
        env_value = environment.get(name)
        if env_value:
            return env_value
        if default is not None:
            return default
        raise UnresolvedVariableError(name, source, restricted=variables is not None)

    return _VARIABLE.sub(replace, value)


def resolve_server_variables(server: Server, variables: Optional[Mapping[str, str]] = None) -> Server:
    """Return a copy of ``server`` with the references in its string fields resolved.

    ``port`` may hold a reference (the schema allows a string there for that
    reason); a resolved all-digit port becomes an int again. Custom property
    values are resolved too. The contract's server is not mutated.
    """
    updates = {}
    for field in Server.model_fields:
        value = getattr(server, field)
        if contains_variables(value):
            source = f"server '{server.server}' {_field_name(field)}"
            updates[field] = _checked(
                value, resolve_variables(value, source=source, variables=variables), "Server", field, source
            )
    port = updates.get("port", server.port)
    if isinstance(port, str) and port.isdigit():
        updates["port"] = int(port)
    if server.customProperties:
        custom_properties = []
        changed = False
        for prop in server.customProperties:
            if contains_variables(prop.value):
                changed = True
                prop = prop.model_copy(
                    update={
                        "value": resolve_variables(
                            prop.value,
                            source=f"server '{server.server}' custom property '{prop.property}'",
                            variables=variables,
                        )
                    }
                )
            custom_properties.append(prop)
        if changed:
            updates["customProperties"] = custom_properties
    return server.model_copy(update=updates) if updates else server


def _field_name(field: str) -> str:
    return "schema" if field == "schema_" else field


# These fields document the contract rather than supply test inputs. SQL queries
# resolve separately, after the engine substitutes its ${model}/${field} tokens;
# servers resolve separately, after configuration overrides and server selection.
_DEFERRED_FIELDS = {
    "authoritativeDefinitions",
    "businessName",
    "context",
    "description",
    "examples",
    "implementation",
    "query",
    "servers",
    "synonyms",
    "transformLogic",
    "transformSourceObjects",
}


def resolve_runtime_variables(value, source: str = "contract", variables: Optional[Mapping[str, str]] = None):
    """Copy test inputs with variables resolved, recursively, without altering the contract.

    Handles property names/types, enum values, logical type options, library
    quality arguments, SLA values, and nested array/map definitions. Dictionary
    keys are structural identifiers and are never interpolated.
    """
    if isinstance(value, BaseModel):
        owner = type(value).__name__
        updates = {}
        for field in type(value).model_fields:
            if field in _DEFERRED_FIELDS:
                continue
            original = getattr(value, field)
            field_source = f"{source}.{_field_name(field)}"
            resolved = resolve_runtime_variables(original, field_source, variables)
            updates[field] = _checked(original, resolved, owner, field, field_source)
        return value.model_copy(update=updates)
    if isinstance(value, dict):
        return {key: resolve_runtime_variables(item, f"{source}.{key}", variables) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_runtime_variables(item, f"{source}[{index}]", variables) for index, item in enumerate(value)]
    return resolve_variables(value, source=source, variables=variables)
