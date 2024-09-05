import logging

from soda.scan import Scan

from datacontract.engines.soda.connections.bigquery import to_bigquery_soda_configuration
from datacontract.engines.soda.connections.databricks import to_databricks_soda_configuration
from datacontract.engines.soda.connections.duckdb import get_duckdb_connection
from datacontract.engines.soda.connections.kafka import create_spark_session, read_kafka_topic
from datacontract.engines.soda.connections.postgres import to_postgres_soda_configuration
from datacontract.engines.soda.connections.snowflake import to_snowflake_soda_configuration
from datacontract.engines.soda.connections.sqlserver import to_sqlserver_soda_configuration
from datacontract.engines.soda.connections.trino import to_trino_soda_configuration
from datacontract.export.sodacl_converter import to_sodacl_yaml
from datacontract.model.data_contract_specification import DataContractSpecification, Server
from datacontract.model.run import Run, Check, Log


def check_soda_execute(run: Run, data_contract: DataContractSpecification, server: Server, spark, tmp_dir):
    if data_contract is None:
        run.log_warn("Cannot run engine soda-core, as data contract is invalid")
        return

    run.log_info("Running engine soda-core")
    scan = Scan()

    if server.type in ["s3", "gcs", "azure", "local"]:
        if server.format in ["json", "parquet", "csv", "delta"]:
            con = get_duckdb_connection(data_contract, server, run)
            scan.add_duckdb_connection(duckdb_connection=con, data_source_name=server.type)
            scan.set_data_source_name(server.type)
        else:
            run.checks.append(
                Check(
                    type="general",
                    name="Check that format is supported",
                    result="warning",
                    reason=f"Format {server.format} not yet supported by datacontract CLI",
                    engine="datacontract",
                )
            )
            run.log_warn(f"Format {server.format} not yet supported by datacontract CLI")
            return
    elif server.type == "snowflake":
        soda_configuration_str = to_snowflake_soda_configuration(server)
        scan.add_configuration_yaml_str(soda_configuration_str)
        scan.set_data_source_name(server.type)
    elif server.type == "bigquery":
        soda_configuration_str = to_bigquery_soda_configuration(server)
        scan.add_configuration_yaml_str(soda_configuration_str)
        scan.set_data_source_name(server.type)
    elif server.type == "postgres":
        soda_configuration_str = to_postgres_soda_configuration(server)
        scan.add_configuration_yaml_str(soda_configuration_str)
        scan.set_data_source_name(server.type)
    elif server.type == "databricks":
        if spark is not None:
            logging.info("Use Spark to connect to data source")
            scan.add_spark_session(spark, data_source_name=server.type)
            scan.set_data_source_name(server.type)
            spark.sql(f"USE {server.catalog}.{server.schema_}")
        else:
            soda_configuration_str = to_databricks_soda_configuration(server)
            scan.add_configuration_yaml_str(soda_configuration_str)
            scan.set_data_source_name(server.type)
    elif server.type == "dataframe":
        if spark is None:
            run.log_warn(
                "Server type dataframe only works with the Python library and requires a Spark session, "
                "please provide one with the DataContract class"
            )
            return
        else:
            logging.info("Use Spark to connect to data source")
            scan.add_spark_session(spark, data_source_name="datacontract-cli")
            scan.set_data_source_name("datacontract-cli")
    elif server.type == "kafka":
        if spark is None:
            spark = create_spark_session(tmp_dir)
        read_kafka_topic(spark, data_contract, server, tmp_dir)
        scan.add_spark_session(spark, data_source_name=server.type)
        scan.set_data_source_name(server.type)
    elif server.type == "sqlserver":
        soda_configuration_str = to_sqlserver_soda_configuration(server)
        scan.add_configuration_yaml_str(soda_configuration_str)
        scan.set_data_source_name(server.type)
    elif server.type == "trino":
        soda_configuration_str = to_trino_soda_configuration(server)
        scan.add_configuration_yaml_str(soda_configuration_str)
        scan.set_data_source_name(server.type)

    else:
        run.checks.append(
            Check(
                type="general",
                name="Check that server type is supported",
                result="warning",
                reason=f"Server type {server.type} not yet supported by datacontract CLI",
                engine="datacontract-cli",
            )
        )
        run.log_warn(f"Server type {server.type} not yet supported by datacontract CLI")
        return

    # Don't check types for json format, as they are checked with json schema
    # Don't check types for avro format, as they are checked with avro schema
    # Don't check types for csv format, as they are hard to detect
    server_type = server.type
    check_types = server.format != "json" and server.format != "csv" and server.format != "avro"

    sodacl_yaml_str = to_sodacl_yaml(data_contract, server_type, check_types)
    # print("sodacl_yaml_str:\n" + sodacl_yaml_str)
    scan.add_sodacl_yaml_str(sodacl_yaml_str)

    # Execute the scan
    logging.info("Starting soda scan")
    scan.execute()
    logging.info("Finished soda scan")

    # pprint.PrettyPrinter(indent=2).pprint(scan.build_scan_results())

    scan_results = scan.get_scan_results()
    for c in scan_results.get("checks"):
        check = Check(
            type="schema",
            result=to_result(c),
            reason=", ".join(c.get("outcomeReasons")),
            name=c.get("name"),
            model=c.get("table"),
            field=c.get("column"),
            engine="soda-core",
            diagnostics=c.get("diagnostics"),
        )
        update_reason(check, c)
        run.checks.append(check)

    for log in scan_results.get("logs"):
        run.logs.append(
            Log(
                timestamp=log.get("timestamp"),
                level=log.get("level"),
                message=log.get("message"),
            )
        )

    if scan.has_error_logs():
        run.log_warn("Engine soda-core has errors. See the logs for details.")
        run.checks.append(
            Check(
                type="general",
                name="Execute quality checks",
                result="warning",
                reason="Engine soda-core has errors. See the logs for details.",
                engine="soda-core",
            )
        )
        return


def to_result(c) -> str:
    soda_outcome = c.get("outcome")
    if soda_outcome == "pass":
        return "passed"
    elif soda_outcome == "fail":
        return "failed"
    else:
        return soda_outcome


def update_reason(check, c):
    """Try to find a reason in diagnostics"""
    if check.result == "passed":
        return
    if check.reason is not None and check.reason != "":
        return
    for block in c["diagnostics"]["blocks"]:
        if block["title"] == "Diagnostics":
            # Extract and print the 'text' value
            diagnostics_text = block["text"]
            print(diagnostics_text)
            diagnostics_text_split = diagnostics_text.split(":icon-fail: ")
            if len(diagnostics_text_split) > 1:
                check.reason = diagnostics_text_split[1].strip()
                print(check.reason)
            break  # Exit the loop once the desired block is found
