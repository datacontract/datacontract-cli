"""Freshness/retention checks target physicalName, like every other check.

The sla element speaks contract language; the engine reads the warehouse, so an
object or property named differently there must be read by its physicalName.
"""

import ibis
import pandas as pd
import pyarrow as pa
import pytest
from open_data_contract_standard.model import (
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
    ServiceLevelAgreementProperty,
)

from datacontract.engines.checks.create_checks import create_checks
from datacontract.engines.ibis import ibis_check_execute
from datacontract.model.run import ResultEnum, Run


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


def _events_schema():
    return SchemaObject(
        name="events",
        properties=[SchemaProperty(name="ts", logicalType="timestamp")],
    )


def test_unparseable_freshness_value_fails_only_its_own_check():
    """A freshness value the CLI cannot read must not abort the whole contract.

    Checks are created for the whole contract before any of them runs, so raising here
    used to surface as a single run-level error with none of the contract's other checks
    created (`value: 25h`, the unit baked into the value, did exactly that).
    """
    schema = _events_schema()
    contract = _contract(
        schema,
        ServiceLevelAgreementProperty(property="freshness", element="events.ts", value="25h"),
        ServiceLevelAgreementProperty(property="retention", element="events.ts", value=1, unit="y"),
    )

    checks = create_checks(contract, None)

    freshness = _of_type(checks, "servicelevel_freshness")
    assert len(freshness) == 1
    assert freshness[0].preset_result == "failed"
    assert "25h" in freshness[0].preset_reason
    # The rest of the contract still produced its checks.
    assert len(_of_type(checks, "servicelevel_retention")) == 1
    assert _of_type(checks, "field_is_present")


def test_freshness_accepts_iso8601_duration_like_retention():
    """Freshness reads ISO-8601 durations, the other value form retention already took."""
    contract = _contract(
        _events_schema(),
        ServiceLevelAgreementProperty(property="freshness", element="events.ts", value="P1DT12H"),
    )

    freshness = _of_type(create_checks(contract, None), "servicelevel_freshness")

    assert len(freshness) == 1
    assert freshness[0].seconds == 36 * 3600
    assert freshness[0].preset_result is None


def test_unsupported_freshness_unit_fails_its_check():
    """An unreadable unit is reported, not silently dropped."""
    contract = _contract(
        _events_schema(),
        ServiceLevelAgreementProperty(property="freshness", element="events.ts", value=3, unit="fortnights"),
    )

    freshness = _of_type(create_checks(contract, None), "servicelevel_freshness")

    assert len(freshness) == 1
    assert freshness[0].preset_result == "failed"
    assert "fortnights" in freshness[0].preset_reason


def _audited_events_schema():
    return SchemaObject(
        name="events",
        properties=[
            SchemaProperty(
                name="audit",
                physicalName="audit_field_struct",
                logicalType="object",
                properties=[
                    SchemaProperty(name="created", physicalName="creation_ts", logicalType="timestamp"),
                    SchemaProperty(name="revised", physicalName="revision_ts", logicalType="timestamp"),
                ],
            )
        ],
    )


def test_servicelevel_element_reaches_into_a_struct():
    """`model.struct.field` measures a field of a struct, by its physicalNames."""
    contract = _contract(
        _audited_events_schema(),
        ServiceLevelAgreementProperty(property="freshness", element="events.audit.created", value=24, unit="h"),
        ServiceLevelAgreementProperty(property="retention", element="events.audit.created", value=1, unit="y"),
    )

    checks = create_checks(contract, Server(server="s", type="databricks"))

    for check_type in ("servicelevel_freshness", "servicelevel_retention"):
        (check,) = _of_type(checks, check_type)
        assert check.field == "audit_field_struct.creation_ts"
        assert check.preset_result is None


def test_servicelevel_element_into_a_struct_warns_where_nested_checks_do_not_run():
    """A struct field the server cannot read is reported, like any nested property check."""
    contract = _contract(
        _audited_events_schema(),
        ServiceLevelAgreementProperty(property="freshness", element="events.audit.created", value=24, unit="h"),
    )

    (check,) = _of_type(create_checks(contract, Server(server="s", type="postgres")), "servicelevel_freshness")

    assert check.preset_result == "warning"
    assert "nested" in check.preset_reason


def test_servicelevel_element_coalesces_fields():
    contract = _contract(
        _audited_events_schema(),
        ServiceLevelAgreementProperty(
            property="freshness", element="COALESCE(events.audit.revised, events.audit.created)", value=24, unit="h"
        ),
    )

    (check,) = _of_type(create_checks(contract, None), "servicelevel_freshness")

    assert check.columns == ["audit_field_struct.revision_ts", "audit_field_struct.creation_ts"]
    assert check.field == "coalesce(audit_field_struct.revision_ts, audit_field_struct.creation_ts)"


def test_servicelevel_element_that_names_no_single_model_is_skipped():
    """A coalesce across models, or a comma list outside a coalesce, names no column to read."""
    contract = _contract(
        _audited_events_schema(),
        ServiceLevelAgreementProperty(
            property="freshness", element="coalesce(events.audit.revised, other.created)", value=24, unit="h"
        ),
        ServiceLevelAgreementProperty(
            property="freshness", element="events.audit.revised, events.audit.created", value=24, unit="h"
        ),
    )

    assert _of_type(create_checks(contract, None), "servicelevel_freshness") == []


def _run_servicelevel_checks(audits: list, *slas: ServiceLevelAgreementProperty, tz: str | None = "UTC"):
    """The field and result of each service level check, run against one audit struct per row."""
    timestamp = pa.timestamp("us", tz=tz)
    audit_type = pa.struct([("creation_ts", timestamp), ("revision_ts", timestamp)])
    con = ibis.duckdb.connect()
    con.create_table("events", pa.table({"audit_field_struct": pa.array(audits, type=audit_type)}))
    server = Server(server="s", type="duckdb")
    contract = _contract(_audited_events_schema(), *slas)
    specs = [c for c in create_checks(contract, server) if c.category == "servicelevel"]
    run = Run.create_run()
    run.checks = ibis_check_execute.build_check_stubs(specs)

    ibis_check_execute._run_model(run, con, "events", specs, contract, server)

    return [(c.field, c.result) for c in run.checks]


def test_servicelevel_checks_read_coalesced_struct_fields():
    """An updated record counts by its revision, not by its creation long ago."""
    now = pd.Timestamp.now(tz="UTC")
    coalesced = "coalesce(events.audit.revised, events.audit.created)"

    results = _run_servicelevel_checks(
        [
            {"creation_ts": pd.Timestamp("2000-01-01", tz="UTC"), "revision_ts": now - pd.Timedelta(hours=1)},
            {"creation_ts": now - pd.Timedelta(hours=2), "revision_ts": None},
        ],
        ServiceLevelAgreementProperty(property="retention", element="events.audit.created", value=1, unit="d"),
        ServiceLevelAgreementProperty(property="retention", element=coalesced, value=1, unit="d"),
        ServiceLevelAgreementProperty(property="freshness", element=coalesced, value=90, unit="m"),
    )

    assert results == [
        ("audit_field_struct.creation_ts", ResultEnum.failed),
        ("coalesce(audit_field_struct.revision_ts, audit_field_struct.creation_ts)", ResultEnum.passed),
        ("coalesce(audit_field_struct.revision_ts, audit_field_struct.creation_ts)", ResultEnum.passed),
    ]


@pytest.mark.parametrize("tz", [None, "UTC"], ids=["timestamp_ntz", "timestamp"])
def test_a_new_record_that_was_never_revised_is_fresh_by_its_creation(tz):
    """Inserts set only creation_ts, updates set revision_ts: the newest record is an insert.

    A timestamp without a timezone (Databricks TIMESTAMP_NTZ) holds UTC wall clock time.
    """
    now = pd.Timestamp.now(tz="UTC").tz_convert(tz)

    results = _run_servicelevel_checks(
        [
            # inserted long ago, last updated 3 hours ago
            {"creation_ts": pd.Timestamp("2000-01-01", tz=tz), "revision_ts": now - pd.Timedelta(hours=3)},
            # inserted 10 minutes ago, never updated
            {"creation_ts": now - pd.Timedelta(minutes=10), "revision_ts": None},
        ],
        ServiceLevelAgreementProperty(
            property="freshness", element="coalesce(events.audit.revised, events.audit.created)", value=30, unit="m"
        ),
        # Without the fallback, the 3 hours old update would be the newest record.
        ServiceLevelAgreementProperty(property="freshness", element="events.audit.revised", value=30, unit="m"),
        tz=tz,
    )

    assert results == [
        ("coalesce(audit_field_struct.revision_ts, audit_field_struct.creation_ts)", ResultEnum.passed),
        ("audit_field_struct.revision_ts", ResultEnum.failed),
    ]


def test_every_coalesced_field_is_optional():
    """Any coalesced field may be null, or the whole struct; a row with no value at all is left out."""
    now = pd.Timestamp.now(tz="UTC")
    coalesced = "coalesce(events.audit.revised, events.audit.created)"

    results = _run_servicelevel_checks(
        [
            {"creation_ts": now - pd.Timedelta(hours=1), "revision_ts": None},
            {"creation_ts": None, "revision_ts": now - pd.Timedelta(minutes=30)},
            {"creation_ts": None, "revision_ts": None},
            None,
        ],
        # The newest is the revision of a row without creation, the oldest the creation of an unrevised row.
        ServiceLevelAgreementProperty(property="freshness", element=coalesced, value=45, unit="m"),
        ServiceLevelAgreementProperty(property="retention", element=coalesced, value=90, unit="m"),
        # A coalesce of one field is that field.
        ServiceLevelAgreementProperty(
            property="freshness", element="coalesce(events.audit.created)", value=45, unit="m"
        ),
    )

    assert results == [
        ("coalesce(audit_field_struct.revision_ts, audit_field_struct.creation_ts)", ResultEnum.passed),
        ("coalesce(audit_field_struct.revision_ts, audit_field_struct.creation_ts)", ResultEnum.passed),
        ("audit_field_struct.creation_ts", ResultEnum.failed),
    ]
