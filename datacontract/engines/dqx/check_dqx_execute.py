import typing
import uuid

import yaml
from open_data_contract_standard.model import OpenDataContractStandard, Server

if typing.TYPE_CHECKING:
    from pyspark.sql import SparkSession

from datacontract.engines.data_contract_checks import to_schema_name
from datacontract.export.dqx_exporter import extract_quality_rules
from datacontract.model.run import Check, ResultEnum, Run


def _get_rule_check_name(dqx_rule: dict, index: int) -> str:
    check_metadata = dqx_rule.get("check") or {}
    function_name = check_metadata.get("function") or "dqx_rule"
    return dqx_rule.get("name") or f"{function_name}_{index + 1}"


def check_dqx_execute(
    run: Run,
    data_contract: OpenDataContractStandard,
    server: Server,
    spark: "SparkSession" = None,
):
    if data_contract is None:
        run.log_warn("Cannot run engine dqx, as data contract is invalid")
        return

    if server.type != "databricks":
        run.log_info(
            f"DQX execution is only available for server type 'databricks'. "
            f"Configured server type is '{server.type}'. Skipping DQX checks."
        )
        return

    rules_by_schema: list[tuple[str, list[dict]]] = []
    for schema_obj in data_contract.schema_ or []:
        schema_name = to_schema_name(schema_obj, server.type)
        dqx_rules = extract_quality_rules(schema_obj)
        if dqx_rules:
            rules_by_schema.append((schema_name, dqx_rules))

    try:
        from databricks.labs.dqx.engine import DQEngine
        from databricks.sdk import WorkspaceClient
        from pyspark.sql import SparkSession
    except ImportError:
        run.log_warn(
            "Cannot run engine dqx, dependencies are missing. "
            "Install datacontract-cli[dqx] to enable DQX execution."
        )
        for schema_name, dqx_rules in rules_by_schema:
            for index, dqx_rule in enumerate(dqx_rules):
                check_name = _get_rule_check_name(dqx_rule, index)
                run.checks.append(
                    Check(
                        id=str(uuid.uuid4()),
                        key=f"{schema_name}__{check_name}__dqx",
                        category="quality",
                        type="custom",
                        name=check_name,
                        model=schema_name,
                        engine="dqx",
                        language="python",
                        implementation=yaml.dump(dqx_rule, sort_keys=False),
                        result=ResultEnum.error,
                        reason="DQX dependencies are missing. Install datacontract-cli[dqx] to enable DQX execution.",
                    )
                )
        return

    # Resolve or create a Spark session.
    # Priority:
    #   1. Explicitly provided Spark session (programmatic API).
    #   2. Existing active session (e.g. running on Databricks cluster).
    #   3. Databricks Connect session (if databricks-connect is installed).
    #   4. Fallback SparkSession.builder.getOrCreate() (e.g. local Spark).
    spark_session = spark or SparkSession.getActiveSession()

    if spark_session is None:
        # Try Databricks Connect first (optional dependency).
        try:
            from databricks.connect import DatabricksSession  # type: ignore[import-not-found]

            run.log_info("Creating Spark session via Databricks Connect (DatabricksSession).")
            spark_session = DatabricksSession.builder.getOrCreate()
        except Exception:
            spark_session = None

    if spark_session is None:
        try:
            run.log_info("Creating Spark session via SparkSession.builder.getOrCreate().")
            spark_session = SparkSession.builder.getOrCreate()
        except Exception:
            spark_session = None

    if spark_session is None:
        run.log_warn("Cannot run engine dqx, as no active Spark session is available.")
        for schema_name, dqx_rules in rules_by_schema:
            for index, dqx_rule in enumerate(dqx_rules):
                check_name = _get_rule_check_name(dqx_rule, index)
                run.checks.append(
                    Check(
                        id=str(uuid.uuid4()),
                        key=f"{schema_name}__{check_name}__dqx",
                        category="quality",
                        type="custom",
                        name=check_name,
                        model=schema_name,
                        engine="dqx",
                        language="python",
                        implementation=yaml.dump(dqx_rule, sort_keys=False),
                        result=ResultEnum.error,
                        reason="No active Spark session is available to execute DQX checks.",
                    )
                )
        return

    run.log_info("Running engine dqx")
    dq_engine = DQEngine(workspace_client=WorkspaceClient(), spark=spark_session)

    for schema_name, dqx_rules in rules_by_schema:

        run.log_info(f"Running {len(dqx_rules)} DQX checks for model {schema_name}")

        try:
            model_df = spark_session.read.table(schema_name)
        except Exception as exc:
            run.log_error(str(exc))
            for index, dqx_rule in enumerate(dqx_rules):
                check_name = _get_rule_check_name(dqx_rule, index)
                run.checks.append(
                    Check(
                        id=str(uuid.uuid4()),
                        key=f"{schema_name}__{check_name}__dqx",
                        category="quality",
                        type="custom",
                        name=check_name,
                        model=schema_name,
                        engine="dqx",
                        language="python",
                        implementation=yaml.dump(dqx_rule, sort_keys=False),
                        result=ResultEnum.error,
                        reason=str(exc),
                    )
                )
            continue

        for index, dqx_rule in enumerate(dqx_rules):
            check_name = _get_rule_check_name(dqx_rule, index)
            check_key = f"{schema_name}__{check_name}__dqx"

            try:
                passed_df, invalid_df = dq_engine.apply_checks_by_metadata_and_split(model_df, [dqx_rule])
                violations = invalid_df.count()

                criticality = str(dqx_rule.get("criticality", "error")).lower()
                if violations == 0:
                    result = ResultEnum.passed
                    reason = f"all {passed_df.count()} row(s) passed the DQX rule"
                elif criticality == "warn":
                    result = ResultEnum.warning
                    reason = f"{violations} row(s) violated the warning DQX rule"
                else:
                    result = ResultEnum.failed
                    reason = f"{violations} row(s) violated the DQX rule"

                run.checks.append(
                    Check(
                        id=str(uuid.uuid4()),
                        key=check_key,
                        category="quality",
                        type="custom",
                        name=check_name,
                        model=schema_name,
                        engine="dqx",
                        language="python",
                        implementation=yaml.dump(dqx_rule, sort_keys=False),
                        result=result,
                        reason=reason,
                    )
                )
            except Exception as exc:
                run.log_error(str(exc))
                run.checks.append(
                    Check(
                        id=str(uuid.uuid4()),
                        key=check_key,
                        category="quality",
                        type="custom",
                        name=check_name,
                        model=schema_name,
                        engine="dqx",
                        language="python",
                        implementation=yaml.dump(dqx_rule, sort_keys=False),
                        result=ResultEnum.error,
                        reason=str(exc),
                    )
                )
