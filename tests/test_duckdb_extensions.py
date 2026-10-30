"""DuckDB extensions bundled by the `xlsx`, `s3`, `gcs` and `azure` extras load without a download."""

import importlib.resources
import shutil
import sys

import duckdb
import pytest

from datacontract.engines.ibis.connections.duckdb_connection import _load_extension


@pytest.mark.parametrize("name", ["excel", "httpfs", "aws", "azure"])
def test_a_bundled_extension_loads_without_downloading(name, tmp_path):
    pytest.importorskip(f"duckdb_extension_{name}")
    # A file where DuckDB expects its extension folder, so installing (downloading) fails
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("")
    con = duckdb.connect()
    con.sql(f"SET extension_directory = '{blocker / 'extensions'}'")

    _load_extension(con, name, "unused")

    loaded = con.sql(f"SELECT loaded FROM duckdb_extensions() WHERE extension_name = '{name}'").fetchone()
    assert loaded == (True,)


def test_a_bundled_extension_loads_from_a_path_with_a_quote(tmp_path, monkeypatch):
    pytest.importorskip("duckdb_extension_excel")
    site_packages = tmp_path / "o'brien"
    package = importlib.resources.files("duckdb_extension_excel")
    shutil.copytree(str(package), site_packages / "duckdb_extension_excel")
    monkeypatch.syspath_prepend(str(site_packages))
    monkeypatch.delitem(sys.modules, "duckdb_extension_excel")
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("")
    con = duckdb.connect()
    con.sql(f"SET extension_directory = '{blocker / 'extensions'}'")

    _load_extension(con, "excel", "unused")

    loaded = con.sql("SELECT loaded FROM duckdb_extensions() WHERE extension_name = 'excel'").fetchone()
    assert loaded == (True,)
