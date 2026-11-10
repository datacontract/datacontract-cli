import os
import time

import pytest

from datacontract.data_contract import DataContract


def _contract(path, extra_properties=""):
    return f"""apiVersion: v3.1.0
kind: DataContract
id: local-file-metadata
name: Local file metadata
version: 1.0.0
status: active
servers:
  - server: landing
    type: local
    path: {path}
    format: metadata
schema:
  - name: files
    quality:
      - metric: rowCount
        mustBe: 2
    properties:
      - name: name
        logicalType: string
        required: true
        logicalTypeOptions:
          pattern: "\\\\.png$"
      - name: size
        logicalType: integer
        logicalTypeOptions:
          maximum: 2048
      - name: lastModified
        logicalType: timestamp
        required: true
{extra_properties}slaProperties:
  - property: freshness
    value: 1
    unit: d
    element: files.lastModified
"""


def _write(path, size=1024):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\0" * size)


def _failed(run):
    return {c.type: c.reason for c in run.checks if c.result != "passed"}


def test_conforming_files_pass(tmp_path):
    _write(tmp_path / "landing" / "a.png")
    _write(tmp_path / "landing" / "2026-11-10" / "b.png")

    run = DataContract(data_contract_str=_contract(tmp_path / "landing")).test()

    assert run.result == "passed", _failed(run)
    assert any(c.type == "servicelevel_freshness" for c in run.checks)


def test_violating_files_fail(tmp_path):
    _write(tmp_path / "landing" / "a.png", size=4096)
    _write(tmp_path / "landing" / "b.csv")
    old = time.time() - 3 * 86400
    for file in (tmp_path / "landing").iterdir():
        os.utime(file, (old, old))

    run = DataContract(data_contract_str=_contract(tmp_path / "landing")).test()

    assert set(_failed(run)) == {"field_regex", "field_maximum", "servicelevel_freshness"}


def test_glob_selects_files_within_one_directory(tmp_path):
    _write(tmp_path / "landing" / "a.png")
    _write(tmp_path / "landing" / "b.png")
    _write(tmp_path / "landing" / "c.csv")
    _write(tmp_path / "landing" / "nested" / "d.png")

    run = DataContract(data_contract_str=_contract(f"{tmp_path}/landing/*.png")).test()

    assert run.result == "passed", _failed(run)


def test_missing_path_has_no_files(tmp_path):
    run = DataContract(data_contract_str=_contract(tmp_path / "missing")).test()

    assert set(_failed(run)) == {"row_count", "servicelevel_freshness"}


@pytest.mark.skipif(not hasattr(os.stat_result, "st_birthtime"), reason="the file system records no creation time")
def test_creation_time_is_checked(tmp_path):
    _write(tmp_path / "landing" / "a.png")
    _write(tmp_path / "landing" / "b.png")
    created = "      - name: created\n        logicalType: timestamp\n        required: true\n"

    run = DataContract(data_contract_str=_contract(tmp_path / "landing", created)).test()

    assert run.result == "passed", _failed(run)
    assert any(c.field == "created" for c in run.checks)
