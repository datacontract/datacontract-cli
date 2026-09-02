"""Variable references in string values, per ODCS v3.2.0 (RFC 0050).

Any string value in a data contract may contain ``${VAR_NAME}`` or, with an
inline default, ``${VAR_NAME:-default}``. References are resolved from the
process environment (which includes a loaded ``.env`` file) at the moment a
value is *used*: when a connection is opened or a quality query is executed.
The loaded contract itself is never mutated, so ``export`` and ``publish``
write the references back verbatim.

A reference to an unset or empty variable without a default is an error;
an empty string is never substituted silently.
"""

import os
import re

from open_data_contract_standard.model import Server

_VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


class UnresolvedVariableError(ValueError):
    """A ``${VAR}`` reference names a variable that is unset and has no default."""

    def __init__(self, name: str, source: str = ""):
        self.name = name
        where = f" in {source}" if source else ""
        super().__init__(f"Variable {name} referenced{where} is not set.")


def contains_variables(value) -> bool:
    """True if ``value`` is a string holding at least one ``${VAR}`` reference."""
    return isinstance(value, str) and _VARIABLE.search(value) is not None


def resolve_variables(value, source: str = ""):
    """Return ``value`` with every ``${VAR}`` reference replaced.

    Non-string values pass through unchanged. ``source`` names the value in
    the error message (``"server 'prod' host"``, ``"config file x.yaml"``).
    """
    if not isinstance(value, str):
        return value

    def replace(match: re.Match) -> str:
        name, default = match.group(1), match.group(2)
        env_value = os.environ.get(name)
        if env_value:
            return env_value
        if default is not None:
            return default
        raise UnresolvedVariableError(name, source)

    return _VARIABLE.sub(replace, value)


def resolve_server_variables(server: Server) -> Server:
    """Return a copy of ``server`` with the references in its string fields resolved.

    ``port`` may hold a reference (the schema allows a string there for that
    reason); a resolved all-digit port becomes an int again. Custom property
    values are resolved too. The contract's server is not mutated.
    """
    updates = {}
    for field in Server.model_fields:
        value = getattr(server, field)
        if contains_variables(value):
            updates[field] = resolve_variables(value, source=f"server '{server.server}' {_field_name(field)}")
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
                            prop.value, source=f"server '{server.server}' custom property '{prop.property}'"
                        )
                    }
                )
            custom_properties.append(prop)
        if changed:
            updates["customProperties"] = custom_properties
    return server.model_copy(update=updates) if updates else server


def _field_name(field: str) -> str:
    return "schema" if field == "schema_" else field
