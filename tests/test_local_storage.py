import logging
from os import environ

from typer.testing import CliRunner

from datacontract.cli import app

runner = CliRunner()

logging.basicConfig(level=logging.DEBUG, force=True)

DATACONTRACT_STORAGE__STORAGE_OPTIONS = '{"path": ".tmp/localstorage/"}'
DATACONTRACT_STORAGE__STORAGE_CLASS = "local"


def test_init():
    environ["DATACONTRACT_STORAGE__STORAGE_OPTIONS"] = DATACONTRACT_STORAGE__STORAGE_OPTIONS
    environ["DATACONTRACT_STORAGE__STORAGE_CLASS"] = DATACONTRACT_STORAGE__STORAGE_CLASS
    result = runner.invoke(app, ["init", "--overwrite"])
    assert result.exit_code == 0


def test_file_does_not_exist():
    environ["DATACONTRACT_STORAGE__STORAGE_OPTIONS"] = DATACONTRACT_STORAGE__STORAGE_OPTIONS
    environ["DATACONTRACT_STORAGE__STORAGE_CLASS"] = DATACONTRACT_STORAGE__STORAGE_CLASS
    result = runner.invoke(app, ["test", "unknown.yaml"])
    assert result.exit_code == 1
    assert "The file 'unknown.yaml' does not exist." in result.stdout
