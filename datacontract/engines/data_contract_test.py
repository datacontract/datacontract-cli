import atexit
import os
import tempfile
import typing

import requests
from open_data_contract_standard.model import OpenDataContractStandard, Server

from datacontract.engines.data_contract_checks import create_checks

if typing.TYPE_CHECKING:
    from duckdb.duckdb import DuckDBPyConnection
    from pyspark.sql import SparkSession

from datacontract.engines.datacontract.check_that_datacontract_contains_valid_servers_configuration import (
    check_that_datacontract_contains_valid_server_configuration,
)
from datacontract.engines.fastjsonschema.check_jsonschema import check_jsonschema
from datacontract.engines.soda.check_soda_execute import check_soda_execute
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum, Run


def execute_data_contract_test(
    data_contract: OpenDataContractStandard,
    run: Run,
    server_name: str = None,
    spark: "SparkSession" = None,
    duckdb_connection: "DuckDBPyConnection" = None,
    schema_name: str = "all",
    check_categories: set[str] | None = None,
):
    if data_contract.schema_ is None or len(data_contract.schema_) == 0:
        raise DataContractException(
            type="lint",
            name="Check that data contract contains models",
            result=ResultEnum.warning,
            reason="Schema block is missing. Skip executing tests.",
            engine="datacontract",
        )
    if server_name is None and data_contract.servers is not None and len(data_contract.servers) > 0:
        server_name = data_contract.servers[0].server
    server = get_server(data_contract, server_name)
    run.log_info(f"Running tests for data contract {data_contract.id} with server {server_name}")
    run.dataContractId = data_contract.id
    run.dataContractVersion = data_contract.version
    run.dataProductId = data_contract.dataProduct
    run.outputPortId = None  # ODCS doesn't have outputPortId
    run.server = server_name

    if schema_name != "all":
        schema_names = {s.name for s in data_contract.schema_} if data_contract.schema_ else set()
        if schema_name not in schema_names:
            raise DataContractException(
                type="lint",
                name="Check that schema name exists",
                result=ResultEnum.failed,
                reason=f"Schema '{schema_name}' not found in data contract. Available schemas: {sorted(schema_names)}",
                engine="datacontract",
            )

    if server.type == "api":
        server = process_api_response(run, server)

    checks = create_checks(data_contract, server, schema_name=schema_name)
    if check_categories is not None:
        checks = [c for c in checks if c.category in check_categories]
        if not checks:
            run.log_warn(f"No checks found for categories: {', '.join(sorted(check_categories))}")
    run.checks.extend(checks)

    # TODO check server is supported type for nicer error messages
    # TODO check server credentials are complete for nicer error messages
    if server.format == "json" and server.type != "kafka":
        if check_categories is None or "schema" in check_categories:
            check_jsonschema(run, data_contract, server, schema_name=schema_name)
    check_soda_execute(
        run, data_contract, server, spark, duckdb_connection, schema_name=schema_name, check_categories=check_categories
    )


def get_server(data_contract: OpenDataContractStandard, server_name: str = None) -> Server | None:
    """Get the server configuration from the data contract.

    Args:
        data_contract: The data contract
        server_name: Optional name of the server to use. If not provided, uses the first server.

    Returns:
        The selected server configuration
    """

    check_that_datacontract_contains_valid_server_configuration(data_contract, server_name)

    if data_contract.servers is None:
        return None

    if server_name is not None:
        server = next((s for s in data_contract.servers if s.server == server_name), None)
    else:
        server = data_contract.servers[0] if data_contract.servers else None
    return server


def process_api_response(run, server):
    tmp_dir = tempfile.TemporaryDirectory(prefix="datacontract_cli_api_")
    atexit.register(tmp_dir.cleanup)
    headers = {}
    if os.getenv("DATACONTRACT_API_HEADER_AUTHORIZATION") is not None:
        headers["Authorization"] = os.getenv("DATACONTRACT_API_HEADER_AUTHORIZATION")
    try:
        response = requests.get(server.location, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise DataContractException(
            type="connection",
            name="API server connection error",
            result=ResultEnum.error,
            reason=f"Failed to fetch API response from {server.location}: {e}",
            engine="datacontract",
        )
    with open(f"{tmp_dir.name}/api_response.json", "w") as f:
        f.write(response.text)
    run.log_info(f"Saved API response to {tmp_dir.name}/api_response.json")
    new_server = Server(
        server="api_local",
        type="local",
        format="json",
        path=f"{tmp_dir.name}/api_response.json",
    )
    return new_server
