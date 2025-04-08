from datacontract.model.data_contract_specification import DataContractSpecification
from datacontract.model.exceptions import DataContractException


def check_that_datacontract_contains_valid_server_configuration(
    data_contract: DataContractSpecification, server_name: str | None
):
    if data_contract.servers is None or len(data_contract.servers) == 0:
        raise DataContractException(
            type="lint",
            name="Check that data contract contains valid server configuration",
            result="warning",
            reason="Servers block is missing. Skip executing tests.",
            engine="datacontract",
        )
    if len(data_contract.servers) > 1 and server_name is None:
        raise DataContractException(
            type="lint",
            name="Check that data contract contains valid server configuration",
            result="warning",
            reason="Data contract contains multiple server configurations. Specify the server you want to test. Skip executing tests.",
            engine="datacontract",
        )
    if server_name is not None and server_name not in data_contract.servers:
        raise DataContractException(
            type="lint",
            name="Check that data contract contains valid servers configuration",
            result="warning",
            reason=f"Cannot find server '{server_name}' in the data contract servers configuration. Skip executing tests.",
            engine="datacontract",
        )


#     TODO check for server.type, if all required fields are present
