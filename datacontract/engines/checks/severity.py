"""Result severity for a quality rule whose threshold was violated."""

from datacontract.model.run import ResultEnum

_WARNING_SEVERITIES = {"info", "warning", "warn", "low", "minor", "trivial"}


def failure_result(severity: str | None) -> ResultEnum:
    if (severity or "").strip().lower() in _WARNING_SEVERITIES:
        return ResultEnum.warning
    return ResultEnum.failed
