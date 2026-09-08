"""The `datacontract test` check selection (`--checks`, `--dimension`, `--quality-id`, `--tag`).

Engines that build their checks from a :class:`~datacontract.engines.checks.check_spec.CheckSpec`
list filter the specs directly (see ``datacontract/engines/data_contract_test.py``).
Engines that emit checks as they go — currently the Azure Blob file engine — carry a
:class:`CheckFilter` instead and ask it about each check before appending it.

An unset (``None``) criterion selects everything; the criteria that are set all apply.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from datacontract.engines.checks.dimensions import default_dimension


@dataclass(frozen=True)
class CheckFilter:
    categories: Optional[set[str]] = None
    dimensions: Optional[set[str]] = None
    quality_ids: Optional[set[str]] = None
    tags: Optional[set[str]] = None

    def matches(
        self,
        *,
        category: str,
        check_type: str,
        dimension: Optional[str] = None,
        quality_id: Optional[str] = None,
        tags: Optional[Iterable[str]] = None,
    ) -> bool:
        """Whether a check should run. ``dimension``/``quality_id``/``tags`` come from
        the ODCS quality rule behind the check, if any."""
        if self.categories is not None and category not in self.categories:
            return False
        if self.dimensions is not None:
            # A rule's own ODCS dimension wins; otherwise fall back to the one this
            # built-in check measures. Checks with neither are dropped by the filter.
            if (dimension if dimension is not None else default_dimension(check_type)) not in self.dimensions:
                return False
        # Only quality rules carry an id and tags, so these criteria exclude the
        # built-in schema and service level checks entirely.
        if self.quality_ids is not None and quality_id not in self.quality_ids:
            return False
        if self.tags is not None and (tags is None or self.tags.isdisjoint(tags)):
            return False
        return True
