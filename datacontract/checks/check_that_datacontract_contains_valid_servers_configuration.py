from datacontract.model.data_contract_specification import DataContractSpecification
from datacontract.model.run import Run, Check


def check_that_datacontract_contains_valid_server_configuration(run: Run, data_contract: DataContractSpecification):
    if data_contract.servers is None:
        run.checks.append(Check(
            type="lint",
            name="Check that data contract contains valid server configuration",
            result="failed",
            reason="servers block is missing",
            engine="datacontract-cli",
        ))
        raise Exception("servers block is missing")
