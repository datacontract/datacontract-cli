import typing

if typing.TYPE_CHECKING:
    from pyspark.sql import SparkSession

from datacontract.engines.datacontract.check_that_datacontract_contains_valid_servers_configuration import (
    check_that_datacontract_contains_valid_server_configuration,
)
from datacontract.engines.fastjsonschema.check_jsonschema import check_jsonschema
from datacontract.engines.soda.check_soda_execute import check_soda_execute
from datacontract.model.data_contract_specification import DataContractSpecification
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Run


def test_data_contract(
    data_contract: DataContractSpecification,
    run: Run,
    server_name: str = None,
    spark: "SparkSession" = None,
):
    if data_contract.models is None or len(data_contract.models) == 0:
        raise DataContractException(
            type="lint",
            name="Check that data contract contains models",
            result="warning",
            reason="Models block is missing. Skip executing tests.",
            engine="datacontract",
        )
    check_that_datacontract_contains_valid_server_configuration(run, data_contract, server_name)
    if server_name:
        server = data_contract.servers.get(server_name)
    else:
        server_name = list(data_contract.servers.keys())[0]
        server = data_contract.servers.get(server_name)
    run.log_info(f"Running tests for data contract {data_contract.id} with server {server_name}")
    run.dataContractId = data_contract.id
    run.dataContractVersion = data_contract.info.version
    run.dataProductId = server.dataProductId
    run.outputPortId = server.outputPortId
    run.server = server_name
    # TODO check server is supported type for nicer error messages
    # TODO check server credentials are complete for nicer error messages
    if server.format == "json" and server.type != "kafka":
        check_jsonschema(run, data_contract, server)
    check_soda_execute(run, data_contract, server, spark)
