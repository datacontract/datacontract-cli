import decimal
import logging
import typing
import uuid
from datetime import date, datetime, time
from typing import Any

import yaml

from datacontract.engines.soda.connections.athena import to_athena_soda_configuration
from datacontract.engines.soda.connections.oracle import initialize_client_and_create_soda_configuration

if typing.TYPE_CHECKING:
    from duckdb.duckdb import DuckDBPyConnection
    from pyspark.sql import SparkSession

from open_data_contract_standard.model import OpenDataContractStandard, Server

from datacontract.engines.soda.connections.bigquery import to_bigquery_soda_configuration
from datacontract.engines.soda.connections.databricks import to_databricks_soda_configuration
from datacontract.engines.soda.connections.duckdb_connection import get_duckdb_connection
from datacontract.engines.soda.connections.impala import to_impala_soda_configuration
from datacontract.engines.soda.connections.kafka import create_spark_session, read_kafka_topic
from datacontract.engines.soda.connections.mysql import to_mysql_soda_configuration
from datacontract.engines.soda.connections.postgres import to_postgres_soda_configuration
from datacontract.engines.soda.connections.snowflake import to_snowflake_soda_configuration
from datacontract.engines.soda.connections.sqlserver import to_sqlserver_soda_configuration
from datacontract.engines.soda.connections.trino import to_trino_soda_configuration
from datacontract.export.sodacl_exporter import to_sodacl_yaml
from datacontract.model.run import Check, Log, ResultEnum, Run

FAILED_ROWS_SAMPLES_LIMIT = 5


def check_soda_execute(
    run: Run,
    data_contract: OpenDataContractStandard,
    server: Server,
    spark: "SparkSession" = None,
    duckdb_connection: "DuckDBPyConnection" = None,
    schema_name: str = "all",
    check_categories: set[str] | None = None,
):
    from soda.common.config_helper import ConfigHelper

    ConfigHelper.get_instance().upsert_value("send_anonymous_usage_stats", False)
    from soda.scan import Scan

    if data_contract is None:
        run.log_warn("Cannot run engine soda-core, as data contract is invalid")
        return

    run.log_info("Running engine soda-core")
    scan = Scan()

    if server.type in ["s3", "gcs", "azure", "local"]:
        if server.format in ["json", "parquet", "csv", "delta"]:
            run.log_info(f"Configuring engine soda-core to connect to {server.type} {server.format} with duckdb")
            con = get_duckdb_connection(data_contract, server, run, duckdb_connection, schema_name=schema_name)
            scan.add_duckdb_connection(duckdb_connection=con, data_source_name=server.type)
            scan.set_data_source_name(server.type)
        else:
            run.checks.append(
                Check(
                    type="general",
                    name="Check that format is supported",
                    result=ResultEnum.warning,
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
    elif server.type == "mysql":
        soda_configuration_str = to_mysql_soda_configuration(server)
        scan.add_configuration_yaml_str(soda_configuration_str)
        scan.set_data_source_name(server.type)
    elif server.type == "databricks":
        if spark is not None:
            run.log_info("Connecting to databricks via spark")
            scan.add_spark_session(spark, data_source_name=server.type)
            scan.set_data_source_name(server.type)
            database_name = ".".join(filter(None, [server.catalog, server.schema_]))
            spark.sql(f"USE {database_name}")
        else:
            run.log_info("Connecting to databricks directly")
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

    # ------------------------------------------------------------------
    # NEW: native Impala server type
    # ------------------------------------------------------------------
    elif server.type == "impala":
        run.log_info("Connecting to Impala via Soda engine")
        soda_configuration_str = to_impala_soda_configuration(server)
        scan.add_configuration_yaml_str(soda_configuration_str)
        # data source name must match what we configure in to_impala_soda_configuration
        scan.set_data_source_name("impala")

    elif server.type == "kafka":
        if spark is None:
            spark = create_spark_session()
        read_kafka_topic(spark, data_contract, server)
        scan.add_spark_session(spark, data_source_name=server.type)
        scan.set_data_source_name(server.type)
    elif server.type == "sqlserver":
        soda_configuration_str = to_sqlserver_soda_configuration(server)
        scan.add_configuration_yaml_str(soda_configuration_str)
        scan.set_data_source_name(server.type)
    elif server.type == "oracle":
        soda_configuration_str = initialize_client_and_create_soda_configuration(server)
        scan.add_configuration_yaml_str(soda_configuration_str)
        scan.set_data_source_name(server.type)
    elif server.type == "trino":
        soda_configuration_str = to_trino_soda_configuration(server)
        scan.add_configuration_yaml_str(soda_configuration_str)
        scan.set_data_source_name(server.type)
    elif server.type == "athena":
        soda_configuration_str = to_athena_soda_configuration(server)
        scan.add_configuration_yaml_str(soda_configuration_str)
        scan.set_data_source_name(server.type)

    else:
        run.checks.append(
            Check(
                type="general",
                name="Check that server type is supported",
                result=ResultEnum.warning,
                reason=f"Server type {server.type} not yet supported by datacontract CLI",
                engine="datacontract-cli",
            )
        )
        run.log_warn(f"Server type {server.type} not yet supported by datacontract CLI")
        return

    sodacl_yaml_str = _inject_samples_limit(to_sodacl_yaml(run), FAILED_ROWS_SAMPLES_LIMIT)
    scan.add_sodacl_yaml_str(sodacl_yaml_str)

    # Execute the scan
    logging.info("Starting soda scan with checks:\n" + sodacl_yaml_str)
    scan.execute()
    logging.info("Finished soda scan")

    # pprint.PrettyPrinter(indent=2).pprint(scan.build_scan_results())

    scan_results = scan.get_scan_results()
    for scan_result in scan_results.get("checks"):
        name = scan_result.get("name")
        check = get_check(run, scan_result)
        if check is None:
            if check_categories is not None and "custom" not in check_categories:
                continue
            check = Check(
                id=str(uuid.uuid4()),
                category="custom",
                type="custom",
                name=name,
                engine="soda-core",
            )
            run.checks.append(check)
        check.result = to_result(scan_result)
        check.reason = ", ".join(scan_result.get("outcomeReasons"))
        check.diagnostics = scan_result.get("diagnostics")
        if check.result == ResultEnum.failed:
            check.failed_rows_samples = _fetch_failed_rows_samples(scan, scan_result, scan_results)
        update_reason(check, scan_result)

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
                name="Data Contract Tests",
                result=ResultEnum.warning,
                reason="Engine soda-core has errors. See the logs for details.",
                engine="soda-core",
            )
        )
        return


def get_check(run, scan_result) -> Check | None:
    check_by_name = next((c for c in run.checks if c.key == scan_result.get("name")), None)
    if check_by_name is not None:
        return check_by_name

    return None


def to_result(c) -> ResultEnum:
    soda_outcome = c.get("outcome")
    if soda_outcome == "pass":
        return ResultEnum.passed
    elif soda_outcome == "fail":
        return ResultEnum.failed
    else:
        return ResultEnum.unknown


def update_reason(check, c):
    """Try to find a reason in diagnostics"""
    if check.result == "passed":
        return
    base_reason: str | None = None
    if check.reason:
        base_reason = check.reason
    else:
        for block in c["diagnostics"]["blocks"]:
            if block["title"] == "Diagnostics":
                diagnostics_text_split = block["text"].split(":icon-fail: ")
                if len(diagnostics_text_split) > 1:
                    base_reason = diagnostics_text_split[1].strip()
                break
        if not base_reason and "fail" in c["diagnostics"]:
            base_reason = f"Value: {c['diagnostics']['value']} Fail: {c['diagnostics']['fail']}"

    sample_summary = _format_sample_summary(check.failed_rows_samples)
    if base_reason and sample_summary:
        check.reason = f"{base_reason}. {sample_summary}"
    elif sample_summary:
        check.reason = sample_summary
    else:
        check.reason = base_reason


def _inject_samples_limit(sodacl_yaml_str: str, limit: int) -> str:
    """Add `samples limit: N` to every `invalid_count(...)` check so Soda
    runs the follow-up SELECT that lists failing rows. The rows themselves
    aren't persisted by Soda, but the SQL surfaces in scan_results['queries']
    and we can re-execute it via Soda's own connection.
    """
    try:
        sodacl_dict = yaml.safe_load(sodacl_yaml_str)
    except yaml.YAMLError:
        return sodacl_yaml_str
    if not isinstance(sodacl_dict, dict):
        return sodacl_yaml_str
    for checks in sodacl_dict.values():
        if not isinstance(checks, list):
            continue
        for check in checks:
            if not isinstance(check, dict):
                continue
            for check_key, check_config in check.items():
                if isinstance(check_config, dict) and str(check_key).startswith("invalid_count"):
                    check_config.setdefault("samples limit", limit)
    return yaml.dump(sodacl_dict)


def _fetch_failed_rows_samples(scan, scan_result: dict, scan_results: dict) -> list[dict] | None:
    """Re-execute the `failing_sql` query Soda built for this check, via
    Soda's own data source connection, and return the rows as JSON-safe dicts.

    Returns None if no matching query exists (e.g. non-SQL backend), or if the
    connection can't be reached for any reason. Errors are logged but never
    raised — sample capture is best-effort.
    """
    data_source_name = scan_result.get("dataSource")
    if not data_source_name:
        return None

    table = scan_result.get("table")
    column = scan_result.get("column")
    failing_query_name = _extract_failing_query_name(scan_result)
    queries = scan_results.get("queries") or []

    failed_rows_sql: str | None = None
    if failing_query_name:
        failed_rows_sql = next(
            (q.get("sql") for q in queries if q.get("name") == failing_query_name),
            None,
        )
    if not failed_rows_sql and table and column:
        prefix = f".{data_source_name}.{table}.{column}.failed_rows["
        failed_rows_sql = next(
            (
                q.get("sql")
                for q in queries
                if prefix in q.get("name", "").replace('"', "") and q.get("name", "").endswith(".failing_sql")
            ),
            None,
        )
    if not failed_rows_sql:
        return None

    try:
        data_source = scan._data_source_manager.get_data_source(data_source_name)
        connection = data_source.connection
        cursor = connection.cursor()
        try:
            cursor.execute(failed_rows_sql)
            columns = [d[0] for d in cursor.description]
            rows = cursor.fetchall()
        finally:
            cursor.close()
    except Exception as e:
        logging.warning(f"Could not fetch failed-rows sample for {table}.{column}: {e}")
        return None

    return [{col: _json_safe(val) for col, val in zip(columns, row)} for row in rows]


def _extract_failing_query_name(scan_result: dict) -> str | None:
    """Soda puts the exact failing-rows query name in the diagnostics block,
    already quoted the way the dialect needs. Prefer that over rebuilding it."""
    diagnostics = scan_result.get("diagnostics") or {}
    for block in diagnostics.get("blocks") or []:
        if block.get("type") == "failedRowsAnalysis":
            name = block.get("failingRowsQueryName")
            if name:
                return name
    return None


def _json_safe(value: Any) -> Any:
    """Coerce database values (Decimal, datetime, bytes, etc.) into JSON-safe
    primitives so Pydantic / json.dumps don't choke on them later."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray, memoryview)):
        try:
            return bytes(value).decode("utf-8")
        except UnicodeDecodeError:
            return bytes(value).hex()
    return str(value)


def _format_sample_summary(samples: list[dict] | None) -> str | None:
    if not samples:
        return None
    first = samples[0]
    rendered = ", ".join(f"{k}={v}" for k, v in first.items())
    if len(samples) == 1:
        return f"Sample failing row: {rendered}"
    return f"Sample failing row (1 of {len(samples)}): {rendered}"
