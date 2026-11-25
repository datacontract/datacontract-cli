from open_data_contract_standard.model import SchemaObject

TABLE_VALUED_FUNCTION = "table_valued_function"
BIGQUERY_TABLE_VALUED_FUNCTION = "TABLE_VALUED_FUNCTION"  # the type BigQuery gives the routine
ARGUMENTS_PROPERTY = "arguments"


def table_function_arguments(schema_object: SchemaObject) -> list[dict]:
    """The arguments of a table function (`name`, `physicalType`, optional `value`), in call order."""
    for custom_property in schema_object.customProperties or []:
        if custom_property.property == ARGUMENTS_PROPERTY:
            return custom_property.value
    return []


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
