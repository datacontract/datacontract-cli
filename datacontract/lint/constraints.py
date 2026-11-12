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
    """Require unique schema, property, server and role names, and unique ids.

    JSON Schema cannot express uniqueness by a key. Invalid shapes are left to JSON Schema.
    """
    errors = []

    def check(entries, path, key, label):
        seen = {}
        for index, entry in enumerate(entries if isinstance(entries, list) else []):
            value = entry.get(key) if isinstance(entry, dict) else None
            if not isinstance(value, str):
                continue
            if value in seen:
                errors.append(
                    DataContractException(
                        type="lint",
                        name=f"Check that {label} are unique",
                        reason=f"{path}[{index}].{key} duplicates {path}[{seen[value]}].{key} ({value!r})",
                    )
                )
            else:
                seen[value] = index

    def visit(node, path):
        if not isinstance(node, dict):
            return
        properties = node.get("properties")
        check(properties, f"{path}.properties", "name", "property names")
        for index, prop in enumerate(properties if isinstance(properties, list) else []):
            visit(prop, f"{path}.properties[{index}]")
        visit(node.get("items"), f"{path}.items")
        mapping = node.get("map")
        if isinstance(mapping, dict):
            for side in ("key", "value"):
                visit(mapping.get(side), f"{path}.map.{side}")

    schemas = contract.get("schema")
    check(schemas, "schema", "name", "schema names")
    for index, schema in enumerate(schemas if isinstance(schemas, list) else []):
        visit(schema, f"schema[{index}]")
    check(contract.get("servers"), "servers", "server", "server names")
    check(contract.get("roles"), "roles", "role", "role names")

    def collect_ids(node, path):
        if isinstance(node, list):
            seen = {}  # ids only need to be unique within their containing array
            for index, item in enumerate(node):
                item_path = f"{path}[{index}]"
                value = item.get("id") if isinstance(item, dict) else None
                if isinstance(value, str):
                    if value in seen:
                        errors.append(
                            DataContractException(
                                type="lint",
                                name="Check that ids are unique",
                                reason=f"{item_path}.id duplicates {seen[value]}.id ({value!r})",
                            )
                        )
                    else:
                        seen[value] = item_path
                collect_ids(item, item_path)
        elif isinstance(node, dict):
            for key, child in node.items():
                # These hold the user's own data, where an id is not an ODCS stable id
                if key not in ("value", "examples", "arguments", "implementation"):
                    collect_ids(child, f"{path}.{key}" if path else key)

    collect_ids(contract, "")
    return errors
