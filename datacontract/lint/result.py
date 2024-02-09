from enum import Enum
from typing import Sequence, Any
from dataclasses import dataclass, field


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
       outcome: The outcome of the linting, either ERROR or WARNING.
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
    linter: str
    results: Sequence[LinterMessage] = field(default_factory=list)

    def with_warning(self, message, model=None):
        result = LinterMessage.warning(message, model)
        return LinterResult(self.linter, self.results + [result])

    def with_error(self, message, model=None):
        result = LinterMessage.error(message, model)
        return LinterResult(self.linter, self.results + [result])

    def has_errors(self) -> bool:
        return any(map(lambda result: result.outcome == LintSeverity.ERROR,
                       self.results))

    def has_warnings(self) -> bool:
        return any(map(lambda result: result.outcome == LintSeverity.WARNING,
                       self.results))

    def error_results(self) -> Sequence[LinterMessage]:
        return [result for result in self.results
                if result.outcome == LintSeverity.ERROR]

    def warning_results(self) -> Sequence[LinterMessage]:
        return [result for result in self.results
                if result.outcome == LintSeverity.WARNING]

    def no_errors_or_warnings(self) -> bool:
        return len(self.results) == 0
