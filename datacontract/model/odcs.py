def is_open_data_contract_standard(odcs: dict) -> bool:
    """
    Check if the given dictionary is an OpenDataContractStandard.

    Args:
        odcs (dict): The dictionary to check.

    Returns:
        bool: True if the dictionary is an OpenDataContractStandard, False otherwise.
    """
    return odcs.get("kind") == "DataContract" and odcs.get("apiVersion", "").startswith("v3")
