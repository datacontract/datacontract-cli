from enum import Enum

from pydantic import BaseModel, Field, computed_field

from datacontract.model.changelog import ChangelogType


class BreakingChangeLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Perspective(str, Enum):
    """Who a change breaks: consumers relying on v1's guarantees, or the producer whose data passed v1."""

    CONSUMER = "consumer"
    PRODUCER = "producer"


class Direction(str, Enum):
    """How a change moves the set of data the contract permits."""

    TIGHTENS = "tightens"
    LOOSENS = "loosens"
    BOTH = "both"
    UNDETERMINED = "undetermined"
    UNTESTED = "untested"


class BreakingChangeEntry(BaseModel):
    path: str
    change_type: ChangelogType
    level: BreakingChangeLevel
    # None inside an added or removed element, which carries the grade, and on summary entries.
    direction: Direction | None = None
    message: str
    rule_id: str
    old_value: str | None = None
    new_value: str | None = None


class BreakingChangeResult(BaseModel):
    v1: str
    v2: str
    perspective: Perspective
    summary: list[BreakingChangeEntry] = Field(default_factory=list)
    entries: list[BreakingChangeEntry] = Field(default_factory=list)

    @computed_field
    @property
    def is_breaking(self) -> bool:
        return any(entry.level == BreakingChangeLevel.ERROR for entry in self.entries)
