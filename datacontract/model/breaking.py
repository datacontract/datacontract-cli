from enum import Enum

from pydantic import BaseModel, Field, computed_field

from datacontract.model.changelog import ChangelogType


class BreakingChangeLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class BreakingChangeEntry(BaseModel):
    path: str
    change_type: ChangelogType
    level: BreakingChangeLevel
    message: str
    rule_id: str
    old_value: str | None = None
    new_value: str | None = None


class BreakingChangeResult(BaseModel):
    v1: str
    v2: str
    summary: list[BreakingChangeEntry] = Field(default_factory=list)
    entries: list[BreakingChangeEntry] = Field(default_factory=list)

    @computed_field
    @property
    def is_breaking(self) -> bool:
        return any(entry.level == BreakingChangeLevel.ERROR for entry in self.entries)
