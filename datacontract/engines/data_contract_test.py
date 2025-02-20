import typing

from datacontract.engines.data_contract_checks import create_checks

if typing.TYPE_CHECKING:
    from pyspark.sql import SparkSession

from datacontract.engines.datacontract.check_that_datacontract_contains_valid_servers_configuration import (
    check_that_datacontract_contains_valid_server_configuration,
)
from datacontract.engines.fastjsonschema.check_jsonschema import check_jsonschema
from datacontract.engines.soda.check_soda_execute import check_soda_execute
from datacontract.model.data_contract_specification import DataContractSpecification
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum, Run


def execute_data_contract_test(
    data_contract_specification: DataContractSpecification,
    run: Run,
    server_name: str = None,
    spark: "SparkSession" = None,
):
    if data_contract_specification.models is None or len(data_contract_specification.models) == 0:
        raise DataContractException(
            type="lint",
            name="Check that data contract contains models",
            result=ResultEnum.warning,
            reason="Models block is missing. Skip executing tests.",
            engine="datacontract",
        )
    check_that_datacontract_contains_valid_server_configuration(run, data_contract_specification, server_name)
    if server_name:
        server = data_contract_specification.servers.get(server_name)
    else:
        server_name = list(data_contract_specification.servers.keys())[0]
        server = data_contract_specification.servers.get(server_name)
    run.log_info(f"Running tests for data contract {data_contract_specification.id} with server {server_name}")
    run.dataContractId = data_contract_specification.id
    run.dataContractVersion = data_contract_specification.info.version
    run.dataProductId = server.dataProductId
    run.outputPortId = server.outputPortId
    run.server = server_name

    run.checks.extend(create_checks(data_contract_specification, server))

    # TODO check server is supported type for nicer error messages
    # TODO check server credentials are complete for nicer error messages
    if server.format == "json" and server.type != "kafka":
        check_jsonschema(run, data_contract_specification, server)
    check_soda_execute(run, data_contract_specification, server, spark)
