import logging

from soda.scan import Scan

from datacontract.engines.soda.connections.duckdb import get_duckdb_connection
from datacontract.engines.soda.connections.snowflake import \
    to_snowflake_soda_configuration
from datacontract.export.sodacl_converter import to_sodacl
from datacontract.model.data_contract_specification import \
    DataContractSpecification, Server
from datacontract.model.run import \
    Run, Check, Log


def check_soda_execute(run: Run, data_contract: DataContractSpecification, server: Server):
    if data_contract is None:
        run.log_warn("Cannot run engine soda-core, as data contract is invalid")
        return

    run.log_info("Running engine soda-core")
    scan = Scan()

    if server.type == "s3" or server.type == "local":
        if server.format in ["json", "parquet", "csv"]:
            con = get_duckdb_connection(data_contract, server)
            scan.add_duckdb_connection(duckdb_connection=con, data_source_name=server.type)
            scan.set_data_source_name(server.type)
        else:
            run.checks.append(Check(
                type="general",
                name="Check that format is supported",
                result="warning",
                reason=f"Format {server.format} not yet supported by datacontract CLI",
                engine="datacontract",
            ))
            run.log_warn(f"Format {server.format} not yet supported by datacontract CLI")
            return
    elif server.type == "snowflake":
        soda_configuration_str = to_snowflake_soda_configuration(server)
        scan.add_configuration_yaml_str(soda_configuration_str)
        scan.set_data_source_name(server.type)
    else:
        run.checks.append(Check(
            type="general",
            name="Check that server type is supported",
            result="warning",
            reason=f"Server type {server.type} not yet supported by datacontract CLI",
            engine="datacontract-cli",
        ))
        run.log_warn(f"Server type {server.type} not yet supported by datacontract CLI")
        return

    # Don't check types for json format, as they are checked with json schema
    check_types = server.format != "json"
    sodacl_yaml_str = to_sodacl(data_contract, check_types)
    # print("sodacl_yaml_str:\n" + sodacl_yaml_str)
    scan.add_sodacl_yaml_str(sodacl_yaml_str)

    # Execute the scan
    logging.info("Starting soda scan")
    scan.execute()
    logging.info("Finished soda scan")

    # pprint.PrettyPrinter(indent=2).pprint(scan.build_scan_results())

    scan_results = scan.get_scan_results()
    for c in scan_results.get("checks"):
        check = Check(type="schema", result="passed" if c.get("outcome") == "pass" else "failed" if c.get(
            "outcome") == "fail" else c.get("outcome"), reason=', '.join(c.get("outcomeReasons")), name=c.get("name"),
                      model=c.get("table"), field=c.get("column"), engine="soda-core", )
        update_reason(check, c)
        run.checks.append(check)

    for log in scan_results.get("logs"):
        run.logs.append(Log(
            timestamp=log.get("timestamp"),
            level=log.get("level"),
            message=log.get("message"),
        ))

    if scan.has_error_logs():
        run.log_warn("Engine soda-core has errors. See the logs for details.")
        run.checks.append(Check(
            type="general",
            name="Execute quality checks",
            result="warning",
            reason=f"Engine soda-core has errors. See the logs for details.",
            engine="soda-core",
        ))
        return


def update_reason(check, c):
    """Try to find a reason in diagnostics"""
    if check.result == "passed":
        return
    if check.reason is not None and check.reason != "":
        return
    for block in c['diagnostics']['blocks']:
        if block['title'] == 'Diagnostics':
            # Extract and print the 'text' value
            diagnostics_text = block['text']
            print(diagnostics_text)
            diagnostics_text_split = diagnostics_text.split(":icon-fail: ")
            if len(diagnostics_text_split) > 1:
                check.reason = diagnostics_text_split[1].strip()
                print(check.reason)
            break  # Exit the loop once the desired block is found
