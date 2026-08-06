import logging
import warnings
from datetime import datetime, timezone
from enum import Enum
from importlib import metadata
from typing import List
from uuid import UUID, uuid4

from pydantic import AliasChoices, BaseModel, Field, SerializerFunctionWrapHandler, model_serializer


def _cli_version() -> str:
    try:
        return metadata.version("datacontract-cli")
    except metadata.PackageNotFoundError:
        return "unknown"


# Check fields renamed to camelCase, mapped to the snake_case name they had
# before. Both spellings are accepted as input, readable on the model, and
# written to the test results.
_DEPRECATED_CHECK_ALIASES = {"qualityId": "quality_id", "failedSamples": "failed_samples"}


def _deprecated_alias(old_name: str, new_name: str) -> property:
    """Read/write access to a renamed check field under its former snake_case name.

    The check fields were renamed to camelCase to match the rest of the
    test-results model (``runId``, ``dataContractId``, ...). Code written against
    the old names keeps working and warns.
    """
    message = f"Check.{old_name} is deprecated, use Check.{new_name} instead."

    def getter(self):
        warnings.warn(message, DeprecationWarning, stacklevel=2)
        return getattr(self, new_name)

    def setter(self, value):
        warnings.warn(message, DeprecationWarning, stacklevel=2)
        setattr(self, new_name, value)

    return property(getter, setter, doc=message)


class ResultEnum(str, Enum):
    passed = "passed"
    warning = "warning"
    failed = "failed"
    error = "error"
    info = "info"
    unknown = "unknown"


class Check(BaseModel):
    id: str | None = None
    key: str | None = None
    category: str | None = None
    type: str
    name: str | None = None
    model: str | None = None  # naming for historic reasons. Should rather be named schema
    field: str | None = None  # naming for historic reasons. Should rather be named property
    # The ODCS `quality.id` / `quality.tags` of the rule this check comes from,
    # so a check can be traced back to (and re-run through `test --quality-id`
    # / `test --tag`) the rule that declared it. Empty for built-in checks.
    qualityId: str | None = Field(default=None, validation_alias=AliasChoices("qualityId", "quality_id"))
    tags: list[str] | None = None

    engine: str | None = None
    language: str | None = None
    implementation: str | None = None

    result: ResultEnum | None = None
    reason: str | None = None
    diagnostics: dict | None = None
    # A capped sample of rows that failed this check (only collected when
    # `datacontract test --include-failed-samples` is set). Each entry is a row
    # restricted to identifier + offending columns, with sensitive columns
    # omitted. The full failed count lives in `diagnostics`, not here.
    failedSamples: list | None = Field(default=None, validation_alias=AliasChoices("failedSamples", "failed_samples"))

    # Deprecated former names of the two fields above. They still read, write and
    # validate, so `check.failed_samples` and older test-results JSON keep working.
    quality_id = _deprecated_alias("quality_id", "qualityId")
    failed_samples = _deprecated_alias("failed_samples", "failedSamples")

    @model_serializer(mode="wrap")
    def _serialize_with_deprecated_aliases(self, handler: SerializerFunctionWrapHandler) -> dict:
        """Write a set field under its deprecated name too.

        The test results are published to the `/api/test-results` API, so a
        consumer still reading `quality_id` / `failed_samples` keeps working. A
        field that is not set stays absent under both names.
        """
        data = handler(self)
        for new_name, old_name in _DEPRECATED_CHECK_ALIASES.items():
            if new_name in data and getattr(self, new_name) is not None:
                data[old_name] = data[new_name]
        return data


class Log(BaseModel):
    level: str
    message: str
    timestamp: datetime


class Run(BaseModel):
    runId: UUID
    datacontractCliVersion: str = _cli_version()
    dataContractId: str | None = None
    dataContractVersion: str | None = None
    dataProductId: str | None = None
    outputPortId: str | None = None
    server: str | None = None
    # The row filters applied to this run (--filter / --filters), keyed by the
    # contract's schema name. None when the whole dataset was tested.
    filters: dict[str, str] | None = None
    timestampStart: datetime | None
    timestampEnd: datetime | None
    result: ResultEnum = ResultEnum.unknown
    checks: List[Check] | None
    logs: List[Log] | None

    def has_passed(self):
        self.calculate_result()
        return self.result == ResultEnum.passed

    def finish(self):
        self.timestampEnd = datetime.now(timezone.utc)
        self.calculate_result()

    def calculate_result(self):
        if any(check.result == ResultEnum.error for check in self.checks):
            self.result = ResultEnum.error
        elif any(check.result == ResultEnum.failed for check in self.checks):
            self.result = ResultEnum.failed
        elif any(check.result == ResultEnum.warning for check in self.checks):
            self.result = ResultEnum.warning
        elif any(check.result == ResultEnum.passed for check in self.checks):
            self.result = ResultEnum.passed
        else:
            self.result = ResultEnum.unknown

    def log_info(self, message: str):
        logging.info(message)
        self.logs.append(Log(level="INFO", message=message, timestamp=datetime.now(timezone.utc)))

    def log_warn(self, message: str):
        logging.warning(message)
        self.logs.append(Log(level="WARN", message=message, timestamp=datetime.now(timezone.utc)))

    def log_error(self, message: str):
        logging.error(message)
        self.logs.append(Log(level="ERROR", message=message, timestamp=datetime.now(timezone.utc)))

    def pretty(self):
        return self.model_dump_json(indent=2)

    def pretty_logs(self) -> str:
        return "\n".join(f"[{log.timestamp.isoformat()}] {log.level}: {log.message}" for log in self.logs)

    @staticmethod
    def create_run():
        """
        Factory method to create a new Run instance.

        :return: An instance of Run.
        """
        run_id = uuid4()
        now = datetime.now(timezone.utc)
        return Run(
            runId=run_id,
            timestampStart=now,
            timestampEnd=now,
            checks=[],
            logs=[],
        )
