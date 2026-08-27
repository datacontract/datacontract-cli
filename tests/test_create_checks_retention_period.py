"""ISO 8601 retention periods are summed over all their components, or rejected."""

import pytest
from open_data_contract_standard.model import (
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
    ServiceLevelAgreementProperty,
)

from datacontract.engines.checks.create_checks import create_checks


def _retention_checks(period):
    contract = OpenDataContractStandard(
        version="1",
        kind="DataContract",
        apiVersion="v3.1.0",
        id="x",
        schema=[SchemaObject(name="events", properties=[SchemaProperty(name="ts", logicalType="timestamp")])],
        slaProperties=[
            ServiceLevelAgreementProperty(property="retention", element="events.ts", value=period),
        ],
    )
    checks = create_checks(contract, Server(server="s", type="snowflake"))
    return [c for c in checks if c.type == "servicelevel_retention"]


@pytest.mark.parametrize(
    "period, seconds",
    [
        ("P1Y", 365 * 86400),
        ("P6M", 6 * 30 * 86400),
        ("P30D", 30 * 86400),
        ("PT6M", 6 * 60),
        ("PT30S", 30),
        ("P2DT12H", 2 * 86400 + 12 * 3600),
        ("P1Y6M", 365 * 86400 + 6 * 30 * 86400),
        ("PT1H30M", 3600 + 30 * 60),
        ("P1Y2M3DT4H5M6S", 365 * 86400 + 2 * 30 * 86400 + 3 * 86400 + 4 * 3600 + 5 * 60 + 6),
    ],
)
def test_retention_period_sums_every_component(period, seconds):
    (check,) = _retention_checks(period)
    assert check.seconds == seconds


@pytest.mark.parametrize("period", ["P30Djunk", "garbage", "P", "PT", "P4W"])
def test_unparsable_retention_period_yields_no_check(period):
    assert _retention_checks(period) == []
