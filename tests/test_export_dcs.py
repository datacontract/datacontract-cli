import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.dcs_exporter import to_dcs_yaml
from datacontract.lint.resolve import resolve_data_contract

runner = CliRunner()

FIXTURE = "fixtures/export/datacontract.odcs.yaml"


def _export(odcs_yaml: str) -> dict:
    return yaml.safe_load(to_dcs_yaml(resolve_data_contract(data_contract_str=odcs_yaml)))


def _contract_with_pii(value: str) -> str:
    """A minimal ODCS contract whose single property carries a `pii` custom property."""
    return f"""
kind: DataContract
apiVersion: v3.1.0
id: pii-unit-test
name: PII Unit Test
version: 1.0.0
status: active
schema:
- name: orders
  properties:
  - name: order_id
    logicalType: string
    customProperties:
    - property: pii
      value: {value}
"""


def _field(contract: dict, name: str = "order_id") -> dict:
    return contract["models"]["orders"]["fields"][name]


def test_cli():
    result = runner.invoke(app, ["export", "dcs", FIXTURE])
    assert result.exit_code == 0


def test_export_dcs_maps_the_contract_metadata():
    contract = _export(open(FIXTURE).read())

    assert contract["id"] == "orders-unit-test"
    assert contract["info"]["title"] == "Orders Unit Test"
    assert contract["info"]["version"] == "1.0.0"
    assert contract["info"]["status"] == "active"
    assert contract["info"]["owner"] == "checkout"
    assert contract["servers"]["production"]["type"] == "snowflake"
    assert contract["servers"]["production"]["database"] == "my-database"


def test_export_dcs_maps_models_and_fields():
    contract = _export(open(FIXTURE).read())

    orders = contract["models"]["orders"]
    assert orders["description"] == "The orders model"
    assert orders["type"] == "table"
    assert set(orders["fields"]) == {"order_id", "order_total", "order_status"}

    order_id = _field(contract)
    assert order_id["title"] == "Order ID"
    assert order_id["type"] == "string"
    assert order_id["required"] is True
    assert order_id["primaryKey"] is True
    assert order_id["unique"] is True
    assert order_id["classification"] == "sensitive"
    assert order_id["tags"] == ["order_id"]


def test_export_dcs_maps_logical_type_options_to_constraints():
    contract = _export(open(FIXTURE).read())

    order_id = _field(contract)
    assert order_id["pattern"] == "^B[0-9]+$"
    assert order_id["minLength"] == 8
    assert order_id["maxLength"] == 10

    order_total = _field(contract, "order_total")
    assert order_total["minimum"] == 0
    assert order_total["maximum"] == 1000000


def test_a_stringified_pii_custom_property_becomes_a_boolean():
    """DCS types `pii` as a boolean, but the DCS importer writes it back out as
    `str(field.pii)` — so contracts in the wild carry the string "True"."""
    contract = _export(_contract_with_pii("'True'"))

    assert _field(contract)["pii"] is True


def test_a_boolean_pii_custom_property_is_kept():
    contract = _export(_contract_with_pii("true"))

    assert _field(contract)["pii"] is True


def test_a_false_pii_custom_property_is_not_dropped():
    contract = _export(_contract_with_pii("'false'"))

    assert _field(contract)["pii"] is False


def test_an_unrecognised_pii_value_is_kept_verbatim_rather_than_mistyped():
    """Emitting `pii: maybe` would be a spec violation, so it stays in config."""
    contract = _export(_contract_with_pii("maybe"))

    field = _field(contract)
    assert "pii" not in field
    assert field["config"]["pii"] == "maybe"


def test_other_custom_properties_go_to_config():
    contract = _export(open(FIXTURE).read())

    assert _field(contract, "order_status")["config"]["enum"] == ["pending", "shipped", "delivered"]


def test_the_exported_contract_passes_lint(tmp_path):
    """The point of the exporter: what it emits is a usable data contract."""
    output = tmp_path / "exported.datacontract.yaml"
    assert runner.invoke(app, ["export", "dcs", FIXTURE, "--output", str(output)]).exit_code == 0

    result = runner.invoke(app, ["lint", str(output)])

    assert result.exit_code == 0, result.output
