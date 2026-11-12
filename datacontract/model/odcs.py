from open_data_contract_standard.model import SchemaObject


def is_open_data_contract_standard(odcs: dict) -> bool:
    """
    Check if the given dictionary is an OpenDataContractStandard.

    Args:
        odcs (dict): The dictionary to check.

    Returns:
        bool: True if the dictionary is an OpenDataContractStandard, False otherwise.
    """
    return odcs.get("kind") == "DataContract" and odcs.get("apiVersion", "").startswith("v3")


def is_open_data_product_standard(odcs: dict) -> bool:
    """
    Check if the given dictionary is an open data product standard.

    Args:
        odcs (dict): The dictionary to check.

    Returns:
        bool: True if the dictionary is an open data product standard, False otherwise.
    """
    return odcs.get("kind") == "DataProduct" and odcs.get("apiVersion", "").startswith("v1")


def is_closed_schema(schema_object: SchemaObject) -> bool:
    """Whether the schema lists every top-level field of its data: the custom property `additionalProperties: false`."""
    value = next((c.value for c in schema_object.customProperties or [] if c.property == "additionalProperties"), None)
    return value is False or str(value).strip().lower() == "false"
