"""`resolve_server_overrides` — the contract's server plus the override options.

A server override option displaces one property of the contract's `servers`
block. They are applied once, up front, so the connection, the table lookup and
the catalog reads behind physical type checks all see the same location.
"""

import pytest
from open_data_contract_standard.model import Server

from datacontract.config import SERVER_OVERRIDE_OPTIONS, Config
from datacontract.model.run import Run
from datacontract.model.server import resolve_server_overrides


@pytest.fixture
def run():
    return Run.create_run()


def test_an_option_set_in_the_environment_overrides_the_contract(run, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_POSTGRES_SCHEMA", "configured")
    server = Server(server="production", type="postgres", schema="declared")

    effective = resolve_server_overrides(server, Config.resolve(None), run)

    assert effective.schema_ == "configured"
    assert server.schema_ == "declared", "the contract's own server must not be mutated"


def test_an_option_passed_programmatically_overrides_the_contract(run):
    """Config fields and DATACONTRACT_* env vars are two distinct sources, and
    only the `get_<option>()` accessor reads both."""
    server = Server(server="production", type="postgres", schema="declared")

    effective = resolve_server_overrides(server, Config(postgres_schema="configured"), run)

    assert effective.schema_ == "configured"


def test_every_option_of_the_server_type_is_applied(run, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_BIGQUERY_PROJECT", "configured-project")
    monkeypatch.setenv("DATACONTRACT_BIGQUERY_DATASET", "configured_dataset")
    server = Server(server="production", type="bigquery", project="declared", dataset="declared")

    effective = resolve_server_overrides(server, Config.resolve(None), run)

    assert (effective.project, effective.dataset) == ("configured-project", "configured_dataset")


def test_mssql_picks_up_the_sqlserver_options(run, monkeypatch):
    """ODCS spells SQL Server `sqlserver`, ibis and ODBC call it `mssql`; the
    options are `sqlserver_*` for both spellings."""
    monkeypatch.setenv("DATACONTRACT_SQLSERVER_DATABASE", "configured")
    server = Server(server="production", type="mssql", database="declared")

    effective = resolve_server_overrides(server, Config.resolve(None), run)

    assert effective.database == "configured"


def test_an_option_of_another_server_type_is_ignored(run, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_SNOWFLAKE_SCHEMA", "configured")
    server = Server(server="production", type="postgres", schema="declared")

    effective = resolve_server_overrides(server, Config.resolve(None), run)

    assert effective.schema_ == "declared"


def test_an_empty_option_leaves_the_contract_value_in_place(run, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_POSTGRES_SCHEMA", "")
    server = Server(server="production", type="postgres", schema="declared")

    effective = resolve_server_overrides(server, Config.resolve(None), run)

    assert effective.schema_ == "declared"


def test_the_override_is_logged_with_both_values(run, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_POSTGRES_SCHEMA", "configured")
    server = Server(server="production", type="postgres", schema="declared")

    resolve_server_overrides(server, Config.resolve(None), run)

    assert any(
        "Server 'production': using schema 'configured' from configuration, overriding 'declared' from the contract"
        == log.message
        for log in run.logs
    ), [log.message for log in run.logs]


def test_a_property_the_contract_does_not_declare_is_logged_without_a_contract_value(run, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_POSTGRES_SCHEMA", "configured")
    server = Server(server="production", type="postgres")

    resolve_server_overrides(server, Config.resolve(None), run)

    assert any("using schema 'configured' from configuration" == log.message.split(": ", 1)[1] for log in run.logs), [
        log.message for log in run.logs
    ]


def test_every_option_names_a_real_server_property():
    """A typo in the map would silently stop overriding that property."""
    unknown = {
        property_name
        for property_name in SERVER_OVERRIDE_OPTIONS.values()
        if ("schema_" if property_name == "schema" else property_name) not in Server.model_fields
    }
    assert not unknown, f"SERVER_OVERRIDE_OPTIONS names properties the ODCS Server has not: {sorted(unknown)}"
