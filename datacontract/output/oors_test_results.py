import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from datacontract.integration.entropy_data import row_counts
from datacontract.model.run import Check, ResultEnum, Run

# The Open Observability Results Standard (OORS) version written. Experimental until OORS v1.0.0.
OORS_API_VERSION = "v0.8.1"
VENDOR = "datacontract-cli"

_STATUS = {
    ResultEnum.passed: "pass",
    ResultEnum.warning: "warn",
    ResultEnum.failed: "fail",
    ResultEnum.error: "error",
    ResultEnum.skipped: "skip",
    ResultEnum.info: "unknown",
    ResultEnum.unknown: "unknown",
}

# Our metric names that have an ODCS library metric equivalent.
_ODCS_METRICS = {
    "row_count": "rowCount",
    "missing_count": "missingValues",
    "invalid_count": "invalidValues",
    "duplicate_count": "duplicateValues",
}

# Threshold.describe() operators and their ODCS equivalents.
_ODCS_OPERATORS = {
    "=": "mustBe",
    "!=": "mustNotBe",
    ">": "mustBeGreaterThan",
    ">=": "mustBeGreaterOrEqualTo",
    "<": "mustBeLessThan",
    "<=": "mustBeLessOrEqualTo",
}


def write_oors_test_results(run: Run, output_path: Path):
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        if not output_path.parent.is_dir():
            raise
    document = to_oors(run)
    with open(output_path, "w", encoding="utf-8") as f:
        if output_path.suffix.lower() in (".yaml", ".yml"):
            yaml.safe_dump(document, f, sort_keys=False, allow_unicode=True)
        else:
            f.write(json.dumps(document, indent=2, ensure_ascii=False))


def to_oors(run: Run) -> dict:
    """The test results of `run` as an OORS document."""
    document = {
        "apiVersion": OORS_API_VERSION,
        "kind": "ObservabilityResults",
        "id": str(run.runId),
        "observedAt": (run.timestampEnd or datetime.now(timezone.utc)).isoformat(),
        "source": {"process": "datacontract test", "runId": str(run.runId), "vendor": VENDOR},
    }
    if run.timestampStart:
        document["run"] = {"state": "completed", "startedAt": run.timestampStart.isoformat()}
    if run.dataContractId:
        document["contract"] = _without_none(
            {
                "contractId": run.dataContractId,
                "standard": "ODCS",
                "version": run.dataContractVersion,
                "server": run.server,
            }
        )
    document["results"] = [_to_result(run, check, index) for index, check in enumerate(run.checks or [])]
    document["status"] = _STATUS[run.result]
    custom_properties = _custom_properties(
        datacontractCliVersion=run.datacontractCliVersion,
        dataProductId=run.dataProductId,
        outputPortId=run.outputPortId,
        dryRun=run.dryRun or None,
    )
    if custom_properties:
        document["customProperties"] = custom_properties
    return document


def _to_result(run: Run, check: Check, index: int) -> dict:
    diagnostics = check.diagnostics or {}
    result = {
        "id": check.key or check.id or f"{check.type}-{index}",
        "type": "check",
        "name": check.name or check.type,
        "status": _STATUS[check.result or ResultEnum.unknown],
        "relatesTo": _relates_to(check),
        "severity": diagnostics.get("severity"),
        "dimension": check.dimension,
    }
    if check.model:
        result["target"] = _without_none(
            {
                "resourceType": "column" if check.field else "table",
                "resourceIdentifier": f"{check.model}.{check.field}" if check.field else check.model,
                "filter": (run.filters or {}).get(check.model),
            }
        )
    measure = _measure(diagnostics)
    if measure:
        result["measure"] = measure
    result["message"] = check.reason
    result["tags"] = check.tags
    result["customProperties"] = _custom_properties(
        checkType=check.type,
        category=check.category,
        engine=check.engine if check.engine != VENDOR else None,
    )
    return _without_none(result)


def _relates_to(check: Check) -> str | None:
    """The path of the contract element the check comes from, following the OORS examples."""
    if check.category == "servicelevel":
        return f"slaProperties/{check.qualityId}" if check.qualityId else None
    if not check.model:
        return None
    path = f"schema/{check.model}"
    if check.field:
        path += f"/properties/{check.field}"
    if check.qualityId:
        path += f"/quality/{check.qualityId}"
    return path


def _measure(diagnostics: dict) -> dict | None:
    metric = diagnostics.get("metric")
    if metric is None:
        return None
    counts = row_counts(diagnostics)
    is_percent = diagnostics.get("unit") == "percent"
    measure = _without_none(
        {
            "metric": _ODCS_METRICS.get(metric, metric),
            # A percent threshold compares the failed percentage, not the count.
            "value": diagnostics.get("percent") if is_percent else diagnostics.get("value"),
            "threshold": _threshold(diagnostics.get("threshold")),
            "unit": diagnostics.get("unit"),
            "rowCount": counts.get("totalNumber"),
            "failedRowCount": counts.get("failedNumber"),
        }
    )
    # OORS values are numbers or strings.
    if not isinstance(measure.get("value"), (int, float, str)):
        measure.pop("value", None)
    return measure


def _threshold(expression) -> dict | None:
    """The ODCS operator for a threshold written by Threshold.describe(), e.g. `= 0` or `between 1 and 5`."""
    if not isinstance(expression, str):
        return None
    between = re.fullmatch(r"(not )?between (\S+) and (\S+)", expression)
    if between:
        operator = "mustNotBeBetween" if between[1] else "mustBeBetween"
        return {operator: [_number(between[2]), _number(between[3])]}
    symbol, _, value = expression.partition(" ")
    operator = _ODCS_OPERATORS.get(symbol)
    return {operator: _number(value)} if operator and value else None


def _number(value: str):
    for convert in (int, float):
        try:
            return convert(value)
        except ValueError:
            pass
    return value


def _custom_properties(**properties) -> list[dict] | None:
    return [
        {"property": name, "value": value, "vendor": VENDOR} for name, value in properties.items() if value is not None
    ] or None


def _without_none(values: dict) -> dict:
    return {name: value for name, value in values.items() if value is not None}
