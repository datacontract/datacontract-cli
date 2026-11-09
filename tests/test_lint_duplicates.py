import pytest
import yaml

from datacontract.data_contract import DataContract


def document(**overrides):
    return {
        "apiVersion": "v3.2.0",
        "kind": "DataContract",
        "id": "test",
        "version": "1",
        "status": "active",
        "schema": [{"name": "orders", "properties": [{"name": "a"}, {"name": "b"}]}],
        **overrides,
    }


def lint(doc, **kwargs):
    return DataContract(data_contract_str=yaml.safe_dump(doc), **kwargs).lint()


def reasons(run):
    return [c.reason for c in run.checks if c.reason]


def test_unique_names_are_valid():
    assert lint(document()).result == "passed"


@pytest.mark.parametrize(
    "overrides, expected",
    [
        ({"schema": [{"name": "orders"}, {"name": "orders"}]}, "schema[1].name duplicates schema[0].name ('orders')"),
        (
            {"schema": [{"name": "orders", "properties": [{"name": "a"}, {"name": "a"}]}]},
            "schema[0].properties[1].name duplicates schema[0].properties[0].name ('a')",
        ),
        (
            {"schema": [{"name": "o", "properties": [{"name": "x", "properties": [{"name": "i"}, {"name": "i"}]}]}]},
            "schema[0].properties[0].properties[1].name duplicates",
        ),
        (
            {"schema": [{"name": "o", "properties": [{"name": "x", "items": {"properties": [{"name": "i"}] * 2}}]}]},
            "schema[0].properties[0].items.properties[1].name duplicates",
        ),
        (
            {
                "schema": [
                    {"name": "o", "properties": [{"name": "x", "map": {"value": {"properties": [{"name": "i"}] * 2}}}]}
                ]
            },
            "schema[0].properties[0].map.value.properties[1].name duplicates",
        ),
        (
            {"servers": [{"server": "prod", "type": "custom"}, {"server": "prod", "type": "custom"}]},
            "servers[1].server duplicates servers[0].server ('prod')",
        ),
        ({"roles": [{"role": "r"}, {"role": "r"}]}, "roles[1].role duplicates roles[0].role"),
        (
            {"schema": [{"name": "o", "properties": [{"name": "a", "id": "x"}, {"name": "b", "id": "x"}]}]},
            "schema[0].properties[1].id duplicates schema[0].properties[0].id ('x')",
        ),
        (
            {"schema": [{"name": "o", "quality": [{"id": "q", "type": "text"}, {"id": "q", "type": "text"}]}]},
            "schema[0].quality[1].id duplicates schema[0].quality[0].id ('q')",
        ),
    ],
)
def test_duplicates_fail(overrides, expected):
    run = lint(document(**overrides))
    assert run.result == "failed"
    assert any(expected in r for r in reasons(run))


def test_same_name_in_different_scopes_is_valid():
    doc = document(
        schema=[
            {"name": "orders", "properties": [{"name": "id"}, {"name": "o", "properties": [{"name": "id"}]}]},
            {"name": "items", "properties": [{"name": "id"}]},
        ]
    )
    assert lint(doc).result == "passed"


def test_repeated_sla_property_is_valid():
    sla = [
        {"property": "timeOfAvailability", "value": "09:00-08:00", "element": "orders.a", "driver": "regulatory"},
        {"property": "timeOfAvailability", "value": "08:00-08:00", "element": "orders.a", "driver": "analytics"},
    ]
    assert lint(document(slaProperties=sla)).result == "passed"


def test_same_id_in_different_arrays_is_valid():
    doc = document(schema=[{"name": "o", "id": "x", "properties": [{"name": "a", "id": "x"}]}])
    assert lint(doc).result == "passed"


@pytest.mark.parametrize(
    "overrides",
    [
        {"customProperties": [{"property": "related", "value": [{"id": "x", "v": 1}, {"id": "x", "v": 2}]}]},
        {"schema": [{"name": "o", "properties": [{"name": "a", "examples": [{"id": "x"}, {"id": "x"}]}]}]},
    ],
)
def test_repeated_id_in_free_form_values_is_valid(overrides):
    assert lint(document(**overrides)).result == "passed"


def test_names_are_case_sensitive():
    assert lint(document(schema=[{"name": "Orders"}, {"name": "orders"}])).result == "passed"


def test_all_errors_reports_every_duplicate():
    doc = document(schema=[{"name": "a"}, {"name": "a"}], servers=[{"server": "s"}, {"server": "s"}])
    run = lint(doc, all_errors=True)
    assert run.result == "failed"
    assert any("schema[1].name" in r for r in reasons(run))
    assert any("servers[1].server" in r for r in reasons(run))


def test_custom_schema_skips_duplicate_checks(tmp_path):
    custom = tmp_path / "custom.json"
    custom.write_text('{"type":"object"}')
    assert lint(document(), schema_location=str(custom)).result == "passed"
    schema = [{"name": "a", "id": "x"}, {"name": "a", "id": "x"}]
    assert lint(document(schema=schema), schema_location=str(custom)).result == "passed"
