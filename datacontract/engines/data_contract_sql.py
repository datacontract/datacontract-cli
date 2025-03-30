import os
import typing

import pandas
from duckdb.duckdb import DuckDBPyConnection

from datacontract.engines.data_contract_test import get_server
from datacontract.engines.soda.connections.duckdb_connection import get_duckdb_connection

if typing.TYPE_CHECKING:
    from pyspark.sql import SparkSession

from datacontract.model.data_contract_specification import DataContractSpecification, Server
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum, Run


def execute_sql(
    data_contract: DataContractSpecification,
    query: str,
    server_name: str = None,
    spark: "SparkSession" = None,
    duckdb_connection: DuckDBPyConnection = None,
) -> pandas.DataFrame | None:
    if data_contract.models is None or len(data_contract.models) == 0:
        raise DataContractException(
            type="lint",
            name="Check that data contract contains models",
            result=ResultEnum.warning,
            reason="Models block is missing. Skip executing tests.",
            engine="datacontract",
        )
    server = get_server(data_contract, server_name)

    if server.type in ["s3", "gcs", "azure", "local"] and server.format in ["json", "parquet", "csv", "delta"]:
        dummy_run = Run.create_run()
        con = get_duckdb_connection(data_contract, server, dummy_run, duckdb_connection)
        return con.sql(query).df()
    elif server.type == "snowflake":
        con = get_snowflake_connection(server)
        return con.cursor().execute(query).fetch_pandas_all()
    else:
        raise DataContractException(
            type="sql",
            name="Server format not supported",
            result=ResultEnum.warning,
            reason=f"Server {server.type} with format {server.format} not yet supported to run SQL queries",
            engine="datacontract",
        )


def get_snowflake_connection(server: Server):
    import snowflake.connector

    prefix = "DATACONTRACT_SNOWFLAKE_"
    snowflake_params = {k.replace(prefix, "").lower(): v for k, v in os.environ.items() if k.startswith(prefix)}

    conn_params = {
        "account": server.account,
        "database": server.database,
        "schema": server.schema_,
        **snowflake_params,
    }

    return snowflake.connector.connect(**conn_params)
