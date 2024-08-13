import os
from pathlib import PosixPath

from typer.testing import CliRunner

from datacontract.cli import app

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli(tmp_path: PosixPath):
    runner = CliRunner()
    result = runner.invoke(app, ["catalog", "--files", "fixtures/catalog/*.yaml", "--output", tmp_path])
    assert result.exit_code == 0
    assert os.path.exists(tmp_path / "index.html")
    assert os.path.exists(tmp_path / "fixtures/catalog/datacontract-1.html")
