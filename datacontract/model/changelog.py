from enum import Enum

from pydantic import BaseModel


class ChangelogType(str, Enum):
    added = "added"
    removed = "removed"
    updated = "updated"


class ChangelogEntry(BaseModel):
    path: str
    type: ChangelogType
    old_value: str | None = None
    new_value: str | None = None


class ChangelogResult(BaseModel):
    v1: str
    v2: str
    summary: list[ChangelogEntry] = []
    entries: list[ChangelogEntry] = []

    def has_changes(self) -> bool:
        return len(self.entries) > 0

    def pretty(self) -> str:
        return self.model_dump_json(indent=2)
