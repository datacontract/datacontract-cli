from open_data_contract_standard.model import OpenDataContractStandard, Server

from datacontract.config import Config
from datacontract.engines.hana.hana_check_selection import CheckSelection
from datacontract.engines.hana.hana_connection import get_connection
from datacontract.engines.hana.hana_quality_check import run_quality_checks, run_sla_checks
from datacontract.engines.hana.hana_schema_check import DRY_RUN_REASON, METADATA_ONLY_REASON, run_schema_checks
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum, Run


def check_hana_execute(
    run: Run,
    data_contract: OpenDataContractStandard,
    server: Server,
    schema_name: str = "all",
    check_categories: set[str] | None = None,
    dry_run: bool = False,
    metadata_only: bool = False,
    model_filters: dict[str, str] | None = None,
    dimensions: set[str] | None = None,
    quality_ids: set[str] | None = None,
    tags: set[str] | None = None,
    config: Config | None = None,
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
        run.dryRun = dry_run
        if not dry_run:
            connection = get_connection(server, config)
        skip_reason = METADATA_ONLY_REASON if metadata_only else DRY_RUN_REASON if dry_run else None
        selection = CheckSelection.of(dimensions=dimensions, quality_ids=quality_ids, tags=tags)
        checks_before = len(run.checks)

        for schema_object in data_contract.schema_ or []:
            if schema_name != "all" and schema_object.name != schema_name:
                continue
            row_filter = (model_filters or {}).get(schema_object.physicalName or schema_object.name)
            if check_categories is None or "schema" in check_categories:
                run.checks.extend(
                    run_schema_checks(
                        connection,
                        server_schema,
                        schema_object,
                        dry_run=dry_run,
                        metadata_only=metadata_only,
                        row_filter=row_filter,
                        selection=selection,
                    )
                )
            if check_categories is None or "quality" in check_categories:
                run.checks.extend(
                    run_quality_checks(
                        connection,
                        server_schema,
                        schema_object,
                        skip_reason=skip_reason,
                        row_filter=row_filter,
                        selection=selection,
                    )
                )

        if check_categories is None or "servicelevel" in check_categories:
            run.checks.extend(
                run_sla_checks(
                    connection,
                    server_schema,
                    data_contract,
                    schema_filter=schema_name,
                    skip_reason=skip_reason,
                    model_filters=model_filters,
                    selection=selection,
                )
            )

        if len(run.checks) == checks_before:
            if check_categories is not None:
                run.log_warn(f"No checks found for categories: {', '.join(sorted(check_categories))}")
            if selection:
                run.log_warn(f"No checks found for {selection.describe()}")

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
