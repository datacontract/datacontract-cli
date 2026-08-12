from enum import Enum

from pydantic import BaseModel, Field


class ChangelogType(str, Enum):
    """How an element of the data contract changed between two versions."""

    added = "added"
    removed = "removed"
    updated = "updated"


class ChangelogEntry(BaseModel):
    """A single difference between two versions of a data contract."""

    path: str = Field(
        description="The dotted path to the changed element within the data contract.",
        examples=["schema.orders.properties.order_status"],
    )
    type: ChangelogType = Field(description="Whether the element was added, removed, or updated.")
    old_value: str | None = Field(
        default=None,
        description="The value in the source version. Absent for an added element.",
    )
    new_value: str | None = Field(
        default=None,
        description="The value in the target version. Absent for a removed element.",
    )


class ChangelogResult(BaseModel):
    """The differences between two versions of a data contract."""

    v1: str = Field(description="A label identifying the source (before) data contract.")
    v2: str = Field(description="A label identifying the target (after) data contract.")
    summary: list[ChangelogEntry] = Field(
        default=[],
        description="One entry per changed element, rolled up to the level a reader cares about. Values are omitted.",
    )
    entries: list[ChangelogEntry] = Field(
        default=[],
        description="Every individual change, with the old and new value.",
    )

    def has_changes(self) -> bool:
        return len(self.entries) > 0

    def pretty(self) -> str:
        return self.model_dump_json(indent=2)
