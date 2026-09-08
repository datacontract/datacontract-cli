"""ODCS constraints that JSON Schema cannot express."""

from datacontract.model.exceptions import DataContractException


def enum_value_errors(contract: dict) -> list[DataContractException]:
    """Require unique values, independently of labels/IDs, throughout the property tree.

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
