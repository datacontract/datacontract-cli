"""Contract constraints that the ODCS JSON Schema cannot express."""

from datacontract.model.exceptions import DataContractException


def enum_value_errors(contract: dict) -> list[DataContractException]:
    """Require unique values, independently of labels/IDs, and no null in a required property's enum.

    JSON numbers compare by value (1 equals 1.0), but booleans and strings are
    distinct types. Unlike uniqueItems, metadata does not participate in equality.
    Invalid shapes are left to JSON Schema, including in --all-errors mode.
    """
    errors = []

    def visit(node, path):
        if not isinstance(node, dict):
            return
        seen = {}
        entries = node.get("enum")
        for index, entry in enumerate(entries if isinstance(entries, list) else []):
            if not isinstance(entry, dict) or "value" not in entry:
                continue
            value = entry["value"]
            if value is None and node.get("required") is True:
                errors.append(
                    DataContractException(
                        type="lint",
                        name="Check that the enum of a required property has no null",
                        reason=f"{path}.enum[{index}].value is null, but the property is required: "
                        "remove the null entry, required already rules out missing values",
                    )
                )
            if isinstance(value, (dict, list)):
                continue
            kind = "number" if type(value) in (int, float) else type(value).__name__
            key = (kind, value)
            if key in seen:
                errors.append(
                    DataContractException(
                        type="lint",
                        name="Check that enum values are unique",
                        reason=f"{path}.enum[{index}].value duplicates enum[{seen[key]}].value ({value!r})",
                    )
                )
            else:
                seen[key] = index
        properties = node.get("properties")
        for index, prop in enumerate(properties if isinstance(properties, list) else []):
            visit(prop, f"{path}.properties[{index}]")
        visit(node.get("items"), f"{path}.items")
        mapping = node.get("map")
        if isinstance(mapping, dict):
            for side in ("key", "value"):
                visit(mapping.get(side), f"{path}.map.{side}")

    schemas = contract.get("schema")
    for index, schema in enumerate(schemas if isinstance(schemas, list) else []):
        visit(schema, f"schema[{index}]")
    return errors


def duplicate_name_errors(contract: dict) -> list[DataContractException]:
    """Require unique schema, property, server, role, support channel, team member and SLA entries, and unique ids.

    JSON Schema cannot express uniqueness by a key. Invalid shapes are left to JSON Schema.
    """
    errors = []

    def check(entries, path, keys, label):
        seen = {}
        for index, entry in enumerate(entries if isinstance(entries, list) else []):
            if not isinstance(entry, dict):
                continue
            key = tuple(entry.get(k) for k in keys)
            if not isinstance(key[0], str) or not all(v is None or isinstance(v, str) for v in key):
                continue
            if key in seen:
                value = ", ".join(repr(v) for v in key if v is not None)
                errors.append(
                    DataContractException(
                        type="lint",
                        name=f"Check that {label} are unique",
                        reason=f"{path}[{index}].{keys[0]} duplicates {path}[{seen[key]}].{keys[0]} ({value})",
                    )
                )
            else:
                seen[key] = index

    def visit(node, path):
        if not isinstance(node, dict):
            return
        properties = node.get("properties")
        check(properties, f"{path}.properties", ("name",), "property names")
        for index, prop in enumerate(properties if isinstance(properties, list) else []):
            visit(prop, f"{path}.properties[{index}]")
        visit(node.get("items"), f"{path}.items")
        mapping = node.get("map")
        if isinstance(mapping, dict):
            for side in ("key", "value"):
                visit(mapping.get(side), f"{path}.map.{side}")

    schemas = contract.get("schema")
    check(schemas, "schema", ("name",), "schema names")
    for index, schema in enumerate(schemas if isinstance(schemas, list) else []):
        visit(schema, f"schema[{index}]")
    check(contract.get("servers"), "servers", ("server",), "server names")
    check(contract.get("roles"), "roles", ("role",), "role names")
    check(contract.get("support"), "support", ("channel",), "support channels")
    check(contract.get("slaProperties"), "slaProperties", ("property", "element"), "SLA properties")
    team = contract.get("team")
    check(team.get("members") if isinstance(team, dict) else team, "team.members", ("username",), "team members")

    ids = {}

    def collect_ids(node, path, list_item=False):
        if isinstance(node, list):
            for index, item in enumerate(node):
                collect_ids(item, f"{path}[{index}]", True)
        elif isinstance(node, dict):
            value = node.get("id")
            if list_item and isinstance(value, str):
                if value in ids:
                    errors.append(
                        DataContractException(
                            type="lint",
                            name="Check that ids are unique",
                            reason=f"{path}.id duplicates {ids[value]}.id ({value!r})",
                        )
                    )
                else:
                    ids[value] = path
            for key, child in node.items():
                collect_ids(child, f"{path}.{key}" if path else key)

    collect_ids(contract, "")
    return errors
