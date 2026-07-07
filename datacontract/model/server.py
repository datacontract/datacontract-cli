from typing import List, Optional, Tuple

from open_data_contract_standard.model import CustomProperty, Server

# datacontract-CLI supports server types that are not part of the ODCS
# `Server.type` enum (e.g. a Spark `dataframe`). To stay compliant with the
# ODCS standard, such a server is written as `type: custom` and the real
# datacontract-CLI type is carried in this custom property.
CUSTOM_SERVER_TYPE_PROPERTY = "customType"

# Server types datacontract-CLI supports but ODCS does not define.
NON_ODCS_SERVER_TYPES = {"dataframe"}


def to_odcs_server_type(server_type: Optional[str]) -> Tuple[Optional[str], Optional[List[CustomProperty]]]:
    """Map a datacontract-CLI server type to a standard-compliant ODCS server.

    Types outside the ODCS enum become ``custom`` with the real type stored in
    the ``customType`` custom property. ODCS-native types pass through unchanged.

    Returns a ``(type, customProperties)`` tuple; ``customProperties`` is
    ``None`` for native types.
    """
    if server_type in NON_ODCS_SERVER_TYPES:
        return "custom", [CustomProperty(property=CUSTOM_SERVER_TYPE_PROPERTY, value=server_type)]
    return server_type, None


def get_server_type(server: Optional[Server]) -> Optional[str]:
    """Return the effective datacontract-CLI server type.

    Resolves the standard-compliant ``type: custom`` + ``customType`` custom
    property back to the real datacontract-CLI type (e.g. ``dataframe``).
    Servers carrying a literal type (the in-memory object path that bypasses
    JSON-schema validation) are returned unchanged.
    """
    if server is None:
        return None
    if server.type == "custom":
        custom_type = _get_custom_property(server, CUSTOM_SERVER_TYPE_PROPERTY)
        if custom_type:
            return custom_type
    return server.type


def _get_custom_property(server: Server, name: str) -> Optional[str]:
    for prop in server.customProperties or []:
        if prop.property == name:
            return prop.value
    return None
