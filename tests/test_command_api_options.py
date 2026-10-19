"""The `datacontract api` options travel in the environment, which survives uvicorn's --reload respawn."""

import os

import pytest
from typer.testing import CliRunner

from datacontract.api import ALLOW_LOCAL_FILES_ENV
from datacontract.cli import app
from datacontract.config.variables import CONTRACT_VARIABLES_ENV

runner = CliRunner()


@pytest.fixture
def uvicorn(monkeypatch):
    # setenv first so teardown restores the variables the command writes, even when they were unset.
    for name in (CONTRACT_VARIABLES_ENV, ALLOW_LOCAL_FILES_ENV):
        monkeypatch.setenv(name, "")
        monkeypatch.delenv(name)
    import uvicorn as uvicorn_module

    monkeypatch.setattr(uvicorn_module, "run", lambda **kwargs: None)
    return monkeypatch


def test_contract_variables_option_sets_the_variable(uvicorn):
    result = runner.invoke(app, ["api", "--contract-variables", "TABLE_*,CUTOFF_DATE"])

    assert result.exit_code == 0
    assert os.environ[CONTRACT_VARIABLES_ENV] == "TABLE_*,CUTOFF_DATE"


def test_allow_local_files_option_overrides_an_inherited_value(uvicorn):
    uvicorn.setenv(ALLOW_LOCAL_FILES_ENV, "true")

    result = runner.invoke(app, ["api", "--no-allow-local-files"])

    assert result.exit_code == 0
    assert os.environ[ALLOW_LOCAL_FILES_ENV] == "false"


def test_an_inherited_value_survives_when_the_option_is_absent(uvicorn):
    uvicorn.setenv(CONTRACT_VARIABLES_ENV, "TABLE_*")

    result = runner.invoke(app, ["api"])

    assert result.exit_code == 0
    assert os.environ[CONTRACT_VARIABLES_ENV] == "TABLE_*"
