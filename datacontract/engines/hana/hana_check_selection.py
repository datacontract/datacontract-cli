"""Which checks a test run selects, for the native SAP HANA engine.

The Ibis path filters its ``CheckSpec`` list by ``--dimension``, ``--quality-id``
and ``--tag`` before it executes anything. The HANA engine builds and executes a
check in one step, so it asks this selection *before* it sends a query: a check
the run did not ask for must not cost a round trip.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class CheckSelection:
    """The ``--dimension``, ``--quality-id`` and ``--tag`` filters of a test run.

    A filter left at ``None`` selects everything. ``--quality-id`` and ``--tag``
    address ODCS quality rules, so they exclude the built-in schema checks
    entirely, exactly as they do for the other engines.
    """

    dimensions: frozenset[str] | None = None
    quality_ids: frozenset[str] | None = None
    tags: frozenset[str] | None = None

    @classmethod
    def of(
        cls,
        dimensions: Iterable[str] | None = None,
        quality_ids: Iterable[str] | None = None,
        tags: Iterable[str] | None = None,
    ) -> CheckSelection:
        return cls(
            dimensions=None if dimensions is None else frozenset(dimensions),
            quality_ids=None if quality_ids is None else frozenset(quality_ids),
            tags=None if tags is None else frozenset(tags),
        )

    def selects(
        self,
        *,
        dimension: str | None = None,
        quality_id: str | None = None,
        tags: Iterable[str] | None = None,
    ) -> bool:
        if self.dimensions is not None and dimension not in self.dimensions:
            return False
        if self.quality_ids is not None and quality_id not in self.quality_ids:
            return False
        if self.tags is not None and (not tags or self.tags.isdisjoint(tags)):
            return False
        return True

    def selects_builtin(self, dimension: str | None) -> bool:
        """Whether a check the contract did not declare as a quality rule is selected."""
        return self.selects(dimension=dimension)

    def describe(self) -> str:
        """The active filters, for the warning shown when they select nothing."""
        parts = []
        if self.dimensions is not None:
            parts.append(f"dimensions: {', '.join(sorted(self.dimensions))}")
        if self.quality_ids is not None:
            parts.append(f"quality rule ids: {', '.join(sorted(self.quality_ids))}")
        if self.tags is not None:
            parts.append(f"tags: {', '.join(sorted(self.tags))}")
        return "; ".join(parts)

    def __bool__(self) -> bool:
        """True when the run filters at all."""
        return self.dimensions is not None or self.quality_ids is not None or self.tags is not None


SELECT_ALL = CheckSelection()
