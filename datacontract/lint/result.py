from enum import Enum
from typing import Optional, Sequence, Any
from dataclasses import dataclass, field

LintOutcome = Enum('LintOutcome', ['ERROR', 'WARNING'])


@dataclass
class LinterResult:
    """Result of a single lint.

    Attributes:
       outcome: The outcome of the linting, either ERROR or WARNING.
       message: A message describing the error or warning in more detail.
       model: The model that caused the lint to fail. Is optional.
    """
    outcome: LintOutcome
    message: str
    model: Any = None

    @classmethod
    def error(cls, message: str, model=None):
        return LinterResult(LintOutcome.ERROR, message, model)

    @classmethod
    def warning(cls, message: str, model=None):
        return LinterResult(LintOutcome.WARNING, message, model)


@dataclass
class LintingResult:
    """Result of linting a contract. Contains multiple LinterResults from
       the same linter or lint phase.

    Attributes:
      linter: The linter that produced these results
      results: A list of linting results. Multiple identical linting
          results can be present in the list. An empty list means that
          the linter ran without producing warnings or errors.
    """
    linter: str
    results: Sequence[LinterResult] = field(default_factory=list)

    def with_warning(self, message, model=None):
        result = LinterResult.warning(message, model)
        return LintingResult(self.linter, self.results + [result])

    def with_error(self, message, model=None):
        result = LinterResult.error(message, model)
        return LintingResult(self.linter, self.results + [result])

    def has_errors(self) -> bool:
        return any(map(lambda result: result.outcome == LintOutcome.ERROR,
                       self.results))

    def has_warnings(self) -> bool:
        return any(map(lambda result: result.outcome == LintOutcome.WARNING,
                       self.results))

    def error_results(self) -> Sequence[LinterResult]:
        return [result for result in self.results
                if result.outcome == LintOutcome.ERROR]

    def warning_results(self) -> Sequence[LinterResult]:
        return [result for result in self.results
                if result.outcome == LintOutcome.WARNING]

    def no_errors_or_warnings(self) -> bool:
        return len(self.results) == 0
