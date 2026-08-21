"""`datacontract test --dry-run` reports the checks a run would execute.

The point of a dry run is that the plan can be trusted: it has to list what a
real run against the same contract actually executes, and it has to get there
without reading any data or needing credentials for the server.
"""

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum

local_json = "fixtures/local-json/datacontract.yaml"
postgres = "fixtures/postgres-export/datacontract.yaml"


def plan(contract: str):
    return DataContract(data_contract_file=contract, dry_run=True).test()


def keys(run):
    return sorted(check.key for check in run.checks if check.key)


def test_cli():
    result = CliRunner().invoke(app, ["test", local_json, "--dry-run"])

    assert result.exit_code == 0


def test_the_plan_lists_the_checks_a_real_run_executes():
    """The plan is only useful if it matches what actually happens."""
    planned = plan(local_json)
    executed = DataContract(data_contract_file=local_json).test()

    assert keys(planned) == keys(executed)
    assert keys(planned) != []


def test_every_planned_check_is_skipped():
    run = plan(local_json)

    assert run.checks != []
    assert {check.result for check in run.checks} == {ResultEnum.skipped}


def test_a_plan_is_not_a_failure():
    """Nothing ran, but nothing went wrong: a dry run must not fail a build."""
    run = plan(local_json)

    assert run.result == ResultEnum.skipped


def test_the_plan_says_what_each_check_asserts():
    """The described implementation is what makes the plan reviewable.

    Only the checks built from the spec list carry one; the JSON Schema check
    describes itself in its name, in a dry run exactly as in a real one.
    """
    run = plan(local_json)

    described = [check for check in run.checks if check.engine != "jsonschema"]
    assert described != []
    assert all(check.implementation for check in described)


def test_a_dry_run_needs_no_credentials():
    """The server is never contacted, so a plan works where a run cannot."""
    planned = CliRunner().invoke(app, ["test", postgres, "--dry-run"])
    without_dry_run = CliRunner().invoke(app, ["test", postgres])

    assert planned.exit_code == 0
    assert without_dry_run.exit_code == 1
    assert "DATACONTRACT_POSTGRES_USERNAME" in without_dry_run.stdout


def test_a_json_server_plans_its_schema_check():
    """The JSON Schema check does not come from the spec list, so it is added separately."""
    run = plan(local_json)

    jsonschema_checks = [check for check in run.checks if check.engine == "jsonschema"]
    assert jsonschema_checks != []
    assert all(check.result == ResultEnum.skipped for check in jsonschema_checks)


def test_the_plan_records_that_it_was_a_plan():
    """Consumers of the JSON output need to tell a plan from a run that skipped."""
    run = plan(local_json)

    assert run.dryRun is True


def test_a_real_run_is_not_marked_as_a_plan():
    run = DataContract(data_contract_file=local_json).test()

    assert run.dryRun is False
