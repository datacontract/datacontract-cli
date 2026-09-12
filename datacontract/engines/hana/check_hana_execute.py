from open_data_contract_standard.model import OpenDataContractStandard, Server

from datacontract.engines.hana.hana_connection import get_connection
from datacontract.engines.hana.hana_quality_check import run_quality_checks, run_sla_checks
from datacontract.engines.hana.hana_schema_check import run_schema_checks
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum, Run


def check_hana_execute(
    run: Run,
    data_contract: OpenDataContractStandard,
    server: Server,
    schema_name: str = "all",
    check_categories: set[str] | None = None,
):
    connection = None
    try:
        run.log_info("Running engine hana")
        server_schema = server.schema_
        if not server_schema:
            raise DataContractException(
                type="hana-connection",
                name="Missing SAP HANA schema",
                result=ResultEnum.failed,
                reason="Server schema is required for SAP HANA Cloud.",
                engine="hana",
            )
        connection = get_connection(server)
        checks_before = len(run.checks)

        for schema_object in data_contract.schema_ or []:
            if schema_name != "all" and schema_object.name != schema_name:
                continue
            if check_categories is None or "schema" in check_categories:
                run.checks.extend(run_schema_checks(connection, server_schema, schema_object))
            if check_categories is None or "quality" in check_categories:
                run.checks.extend(run_quality_checks(connection, server_schema, schema_object))

        if check_categories is None or "servicelevel" in check_categories:
            run.checks.extend(run_sla_checks(connection, server_schema, data_contract, schema_filter=schema_name))

        if check_categories is not None and len(run.checks) == checks_before:
            run.log_warn(f"No checks found for categories: {', '.join(sorted(check_categories))}")

    except DataContractException:
        raise
    except Exception as e:
        raise DataContractException(
            type="hana",
            name="SAP HANA Cloud test execution error",
            result=ResultEnum.error,
            reason=str(e),
            engine="hana",
            original_exception=e,
        )
    finally:
        if connection is not None:
            connection.close()
