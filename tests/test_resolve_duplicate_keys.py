"""Duplicate contract keys must not silently overwrite schema or quality rules."""

import pytest

from datacontract.data_contract import DataContract
from datacontract.lint.resolve import _to_yaml
from datacontract.model.exceptions import DataContractException


@pytest.mark.parametrize(
    "document",
    [
        "status: active\nstatus: draft\n",
        "schema:\n- name: orders\n  properties:\n  - name: id\n    required: true\n    required: false\n",
        "schema:\n- name: orders\n  quality: {type: sql, query: SELECT 1, query: SELECT 2}\n",
    ],
)
def test_duplicate_mapping_keys_are_rejected(document: str) -> None:
    with pytest.raises(DataContractException, match="duplicate key"):
        _to_yaml(document)


def test_duplicate_key_error_identifies_source_and_line() -> None:
    with pytest.raises(DataContractException) as exc:
        _to_yaml("version: 1.0.0\nversion: 2.0.0\n", "contracts/orders.yaml")
    assert "contracts/orders.yaml" in str(exc.value)
    assert "line 2" in str(exc.value)


def test_yaml_merge_allows_explicit_override() -> None:
    parsed = _to_yaml("defaults: &defaults {required: false}\ncolumn: {<<: *defaults, required: true}\n")
    assert parsed["column"]["required"] is True


def test_yaml_merge_does_not_hide_duplicate_explicit_keys() -> None:
    with pytest.raises(DataContractException, match="duplicate key"):
        _to_yaml("defaults: &defaults {required: false}\ncolumn: {<<: *defaults, required: true, required: false}\n")


def test_date_strings_and_distinct_mapping_keys_are_unchanged() -> None:
    parsed = _to_yaml("date: 2026-10-13\nfirst: {name: id}\nsecond: {name: id}\n")
    assert parsed["date"] == "2026-10-13"
    assert parsed["first"] == parsed["second"] == {"name": "id"}


def test_lint_reports_duplicate_keys_as_a_failed_check() -> None:
    run = DataContract(data_contract_str="apiVersion: v3.0.2\napiVersion: v3.2.0\n").lint()
    assert not run.has_passed()
    assert any("duplicate key" in (check.reason or "") for check in run.checks)
