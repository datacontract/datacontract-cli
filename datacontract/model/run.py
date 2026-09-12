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
    """The outcome of a check or of a whole test run."""

    passed = "passed"
    warning = "warning"
    failed = "failed"
    error = "error"
    info = "info"
    skipped = "skipped"
    unknown = "unknown"


class Check(BaseModel):
    """A single test that was executed as part of a run."""

    id: str | None = Field(default=None, description="A stable identifier of this check.")
    key: str | None = Field(default=None, description="The key of the check within the test engine.")
    category: str | None = Field(
        default=None,
        description="The category of the check, such as `schema` or `quality`.",
        examples=["schema"],
    )
    type: str = Field(description="The kind of check that was executed.", examples=["field_unique"])
    name: str | None = Field(
        default=None,
        description="A human-readable description of what was checked.",
        examples=["Check that field order_id is unique"],
    )
    model: str | None = Field(  # naming for historic reasons. Should rather be named schema
        default=None,
        description="The name of the schema (table) this check applies to.",
        examples=["orders"],
    )
    field: str | None = Field(  # naming for historic reasons. Should rather be named property
        default=None,
        description="The name of the property (column) this check applies to.",
        examples=["order_id"],
    )
    # The ODCS `quality.id` / `quality.tags` of the rule this check comes from,
    # so a check can be traced back to (and re-run through `test --quality-id`
    # / `test --tag`) the rule that declared it. Empty for built-in checks.
    qualityId: str | None = Field(
        default=None,
        validation_alias=AliasChoices("qualityId", "quality_id"),
        description="The ODCS `quality.id` of the rule this check comes from, or the `slaProperties` "
        "id for a service level check, so it can be traced back to (and re-run through "
        "`test --quality-id`) the declaration it came from. Absent for built-in schema checks.",
    )
    tags: list[str] | None = Field(
        default=None,
        description="The ODCS `quality.tags` of the rule this check comes from.",
    )
    dimension: str | None = Field(
        default=None,
        description="The data quality dimension this check measures, either declared by the rule "
        "(`quality.dimension`) or the one its check type measures.",
        examples=["completeness"],
    )
    qualityDefinition: str | None = Field(
        default=None,
        description="The ODCS quality rule this check comes from, as YAML. Absent for checks that no rule declared.",
    )

    engine: str | None = Field(
        default=None,
        description="The engine that executed the check. By default one of datacontract-cli, jsonschema, or dbt.",
        examples=["datacontract-cli"],
    )
    language: str | None = Field(
        default=None,
        description="The language the check was expressed in.",
        examples=["sql"],
    )
    implementation: str | None = Field(
        default=None,
        description="The check as it was handed to the engine, such as the generated SQL.",
    )

    result: ResultEnum | None = Field(default=None, description="The outcome of this check.")
    reason: str | None = Field(
        default=None,
        description="Why the check did not pass.",
        examples=["Value(s) not unique: 3"],
    )
    diagnostics: dict | None = Field(
        default=None,
        description="Engine-specific details about the check, such as the number of failed rows.",
    )
    # A capped sample of rows that failed this check (only collected when
    # `datacontract test --include-failed-samples` is set). Each entry is a row
    # restricted to identifier + offending columns, with sensitive columns
    # omitted. The full failed count lives in `diagnostics`, not here.
    failedSamples: list | None = Field(
        default=None,
        validation_alias=AliasChoices("failedSamples", "failed_samples"),
        description="A capped sample of rows that failed this check, each restricted to identifier and "
        "offending columns. Only collected when failed samples were explicitly requested. "
        "The full failed count is in `diagnostics`, not here.",
    )

    # Deprecated former names of the two fields above. They still read, write and
    # validate, so `check.failed_samples` and older test-results JSON keep working.
    quality_id = _deprecated_alias("quality_id", "qualityId")
    failed_samples = _deprecated_alias("failed_samples", "failedSamples")

    @model_serializer(mode="wrap")
    def _serialize_with_deprecated_aliases(self, handler: SerializerFunctionWrapHandler):
        """Write a set field under its deprecated name too. Returns a dict.

        The test results are published to the `/api/test-results` API, so a
        consumer still reading `quality_id` / `failed_samples` keeps working. A
        field that is not set stays absent under both names.

        Deliberately left without a return annotation: a `-> dict` here replaces
        the generated JSON Schema of the whole model with a bare object, which
        would leave every check in the API's OpenAPI document untyped.
        """
        data = handler(self)
        for new_name, old_name in _DEPRECATED_CHECK_ALIASES.items():
            if new_name in data and getattr(self, new_name) is not None:
                data[old_name] = data[new_name]
        return data


class Log(BaseModel):
    """A message written while the run was executing."""

    level: str = Field(description="The severity of the message.", examples=["INFO"])
    message: str = Field(description="The message itself.")
    timestamp: datetime = Field(description="When the message was written.")


class Run(BaseModel):
    """The result of testing or linting a data contract."""

    runId: UUID = Field(description="A unique identifier of this run.")
    datacontractCliVersion: str = Field(
        default=_cli_version(),
        description="The version of the Data Contract CLI that executed the run.",
    )
    dataContractId: str | None = Field(
        default=None,
        description="The `id` of the data contract that was tested.",
        examples=["orders"],
    )
    dataContractVersion: str | None = Field(
        default=None,
        description="The `version` of the data contract that was tested.",
        examples=["1.0.0"],
    )
    dataProductId: str | None = Field(default=None, description="The data product the contract belongs to.")
    outputPortId: str | None = Field(default=None, description="The output port the contract describes.")
    server: str | None = Field(
        default=None,
        description="The name of the server the tests ran against.",
        examples=["production"],
    )
    # The row filters applied to this run (--filter / --filters), keyed by the
    # contract's schema name. None when the whole dataset was tested.
    filters: dict[str, str] | None = Field(
        default=None,
        description="The row filters applied to this run, keyed by schema name. "
        "Absent when the whole dataset was tested.",
        examples=[{"orders": "ingested_at >= CURRENT_DATE - 1"}],
    )
    timestampStart: datetime | None = Field(description="When the run started.")
    timestampEnd: datetime | None = Field(description="When the run finished.")
    result: ResultEnum = Field(
        default=ResultEnum.unknown,
        description="The overall outcome, derived from the most severe check result. "
        "`passed` only if every check passed.",
    )
    dryRun: bool = Field(
        default=False,
        description="Whether the run only reported the checks it would execute, without reading any data.",
    )
    checks: List[Check] | None = Field(description="One entry per executed check.")
    logs: List[Log] | None = Field(description="The messages written while the run was executing.")
    # Excluded from serialization: an in-process signal, not part of the published/returned result.
    publish_succeeded: bool | None = Field(
        default=None,
        exclude=True,
        description="Whether publishing the test results succeeded; None if no publish was requested.",
    )

    def has_passed(self):
        self.calculate_result()
        return self.result == ResultEnum.passed

    def finish(self):
        self.timestampEnd = datetime.now(timezone.utc)
        self.calculate_result()

    def calculate_result(self):
        if self.dryRun:
            # A plan asserts nothing, so it can neither pass nor fail. It can
            # still be incomplete, though, and that has to stay visible: a
            # check that could not be planned reports its own result.
            if any(check.result == ResultEnum.error for check in self.checks):
                self.result = ResultEnum.error
            elif any(check.result == ResultEnum.warning for check in self.checks):
                self.result = ResultEnum.warning
            else:
                self.result = ResultEnum.skipped
            return
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
