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
