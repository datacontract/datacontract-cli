import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Sequence, cast

from datacontract.model.run import Check

from ..model.data_contract_specification import DataContractSpecification

"""This module contains linter definitions for linting a data contract.

Lints are quality checks that can succeed, fail, or warn. They are
distinct from checks such as "valid yaml" or "file not found", which
will cause the processing of the data contract to stop. Lints can be
ignored, and are high-level requirements on the format of a data
contract."""


class LintSeverity(Enum):
    """The severity of a lint message. Generally, lint messages should be
    emitted with a severity of ERROR. WARNING should be used when the linter
    cannot determine a lint result, for example, when an unsupported model
    type is used.
    """

    ERROR = 2
    WARNING = 1


@dataclass
class LinterMessage:
    """A single linter message with attached severity and optional "model" that
    caused the message.

    Attributes:
       outcome: The outcome of the linting, either ERROR or WARNING. Linting outcomes with level WARNING are discarded for now.
       message: A message describing the error or warning in more detail.
       model: The model that caused the lint to fail. Is optional.

    """

    outcome: LintSeverity
    message: str
    model: Any = None

    @classmethod
    def error(cls, message: str, model=None):
        return LinterMessage(LintSeverity.ERROR, message, model)

    @classmethod
    def warning(cls, message: str, model=None):
        return LinterMessage(LintSeverity.WARNING, message, model)


@dataclass
class LinterResult:
    """Result of linting a contract. Contains multiple LinterResults from
       the same linter or lint phase.

    Attributes:
      linter: The linter that produced these results
      results: A list of linting results. Multiple identical linting
          results can be present in the list. An empty list means that
          the linter ran without producing warnings or errors.
    """

    results: Sequence[LinterMessage] = field(default_factory=list)

    @classmethod
    def erroneous(cls, message, model=None):
        return cls([LinterMessage.error(message, model)])

    @classmethod
    def cautious(cls, message, model=None):
        return cls([LinterMessage.warning(message, model)])

    def with_warning(self, message, model=None):
        result = LinterMessage.warning(message, model)
        return LinterResult(cast(list[LinterMessage], self.results) + [result])

    def with_error(self, message, model=None):
        result = LinterMessage.error(message, model)
        return LinterResult(cast(list[LinterMessage], self.results) + [result])

    def has_errors(self) -> bool:
        return any(map(lambda result: result.outcome == LintSeverity.ERROR, self.results))

    def has_warnings(self) -> bool:
        return any(map(lambda result: result.outcome == LintSeverity.WARNING, self.results))

    def error_results(self) -> Sequence[LinterMessage]:
        return [result for result in self.results if result.outcome == LintSeverity.ERROR]

    def warning_results(self) -> Sequence[LinterMessage]:
        return [result for result in self.results if result.outcome == LintSeverity.WARNING]

    def no_errors_or_warnings(self) -> bool:
        return len(self.results) == 0

    def combine(self, other: "LinterResult") -> "LinterResult":
        return LinterResult(cast(list[Any], self.results) + cast(list[Any], other.results))


class Linter(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable name of the linter."""
        pass

    @property
    @abc.abstractmethod
    def id(self) -> str:
        """A linter ID for configuration (i.e. enabling and disabling)."""
        pass

    @abc.abstractmethod
    def lint_implementation(self, contract: DataContractSpecification) -> LinterResult:
        pass

    def lint(self, contract: DataContractSpecification) -> list[Check]:
        """Call with a data contract to get a list of check results from the linter."""
        result = self.lint_implementation(contract)
        checks = []
        if not result.error_results():
            checks.append(Check(type="lint", name=f"Linter '{self.name}'", result="passed", engine="datacontract"))
        else:
            # All linter messages are treated as warnings. Severity is
            # currently ignored, but could be used in filtering in the future
            # Linter messages with level WARNING are currently ignored, but might
            # be logged or printed in the future.
            for lint_error in result.error_results():
                checks.append(
                    Check(
                        type="lint",
                        name=f"Linter '{self.name}'",
                        result="warning",
                        engine="datacontract",
                        reason=lint_error.message,
                    )
                )
        return checks
