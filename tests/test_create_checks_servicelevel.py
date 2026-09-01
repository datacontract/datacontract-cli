"""Freshness/retention checks target physicalName, like every other check.

The sla element speaks contract language; the engine reads the warehouse, so an
object or property named differently there must be read by its physicalName.
"""

from open_data_contract_standard.model import (
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
    ServiceLevelAgreementProperty,
)

from datacontract.engines.checks.create_checks import create_checks


def _contract(schema_object: SchemaObject, *slas: ServiceLevelAgreementProperty):
    return OpenDataContractStandard(
        version="1",
        kind="DataContract",
        apiVersion="v3.1.0",
        id="x",
        schema=[schema_object],
        slaProperties=list(slas),
    )


def _of_type(checks, check_type):
    return [c for c in checks if c.type == check_type]


def test_servicelevel_checks_resolve_physical_names():
    """An object and property with physicalName are measured under those names."""
    schema = SchemaObject(
        name="events",
        physicalName="events_v1",
        properties=[SchemaProperty(name="ts", physicalName="TS", logicalType="timestamp")],
    )
    contract = _contract(
        schema,
        ServiceLevelAgreementProperty(property="freshness", element="events.ts", value=24, unit="h"),
        ServiceLevelAgreementProperty(property="retention", element="events.ts", value=1, unit="y"),
    )

    checks = create_checks(contract, Server(server="s", type="snowflake"))

    for check_type in ("servicelevel_freshness", "servicelevel_retention"):
        (check,) = _of_type(checks, check_type)
        assert check.model == "events_v1"
        assert check.field == "TS"


def test_servicelevel_checks_fall_back_to_names_without_physical_names():
    """Without physicalName, service level checks use the logical names (unchanged)."""
    schema = SchemaObject(
        name="events",
        properties=[SchemaProperty(name="ts", logicalType="timestamp")],
    )
    contract = _contract(
        schema,
        ServiceLevelAgreementProperty(property="freshness", element="events.ts", value=24, unit="h"),
    )

    checks = create_checks(contract, Server(server="s", type="snowflake"))

    (check,) = _of_type(checks, "servicelevel_freshness")
    assert check.model == "events"
    assert check.field == "ts"


def test_multiple_servicelevel_promises_get_distinct_keys():
    """Each promise needs its own key, or every result lands on the first check (#1515)."""
    schema = SchemaObject(
        name="events",
        properties=[
            SchemaProperty(name="ts", logicalType="timestamp"),
            SchemaProperty(name="updated", logicalType="timestamp"),
        ],
    )
    contract = _contract(
        schema,
        ServiceLevelAgreementProperty(property="freshness", element="events.ts", value=48, unit="h"),
        ServiceLevelAgreementProperty(property="freshness", element="events.updated", value=2, unit="h"),
        ServiceLevelAgreementProperty(property="retention", element="events.ts", value=1, unit="y"),
        ServiceLevelAgreementProperty(property="retention", element="events.updated", value=2, unit="y"),
    )

    checks = create_checks(contract, Server(server="s", type="snowflake"))

    freshness_keys = [c.key for c in _of_type(checks, "servicelevel_freshness")]
    retention_keys = [c.key for c in _of_type(checks, "servicelevel_retention")]
    assert freshness_keys == ["events__ts__servicelevel_freshness", "events__updated__servicelevel_freshness"]
    assert retention_keys == ["events__ts__servicelevel_retention", "events__updated__servicelevel_retention"]


def test_servicelevel_checks_keep_kafka_logical_name():
    """to_schema_name reads the Spark SQL view (logical name) on kafka, not the topic."""
    schema = SchemaObject(
        name="events",
        physicalName="events-topic",
        properties=[SchemaProperty(name="ts", logicalType="timestamp")],
    )
    contract = _contract(
        schema,
        ServiceLevelAgreementProperty(property="freshness", element="events.ts", value=24, unit="h"),
    )

    checks = create_checks(contract, Server(server="s", type="kafka"))

    (check,) = _of_type(checks, "servicelevel_freshness")
    assert check.model == "events"
