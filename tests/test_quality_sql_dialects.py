"""Custom SQL quality rules must keep working on every supported technology.

`quality.type: sql` queries are refused unless they read as a single read-only
query, and they are read in the SQL dialect of the server they run against
(there is no per-rule dialect field). That guard's failure mode is refusing SQL
a real data source would have accepted, so every server type gets a contract in
`fixtures/quality-sql-dialects/` with rules written the way that technology is
written -- including syntax that only parses in its own dialect.

These tests build the checks the way `datacontract test` does. They do not
connect to anything: the point is that the rules survive to become executable
checks, not what the data says.
"""

import logging
from pathlib import Path

import pytest

from datacontract.data_contract import DataContract
from datacontract.engines.checks.create_checks import create_checks
from datacontract.engines.checks.sql_guard import _DIALECT_BY_SERVER_TYPE, dialect_for_server_type, is_read_only_query
from datacontract.engines.data_contract_test import get_server
from datacontract.lint import resolve
from datacontract.model.run import ResultEnum
from datacontract.model.server import get_server_type

FIXTURES = Path(__file__).parent / "fixtures" / "quality-sql-dialects"
CONTRACTS = sorted(FIXTURES.glob("*.yaml"))
SQL_CHECK_TYPES = ("model_quality_sql", "field_quality_sql")


def _sql_checks(contract_path: Path):
    """The SQL quality checks of a contract, built as `datacontract test` builds them."""
    data_contract = resolve.resolve_data_contract(data_contract_location=str(contract_path), inline_references=False)
    server = get_server(data_contract, None)
    specs = create_checks(data_contract, server)
    return server, [spec for spec in specs if spec.type in SQL_CHECK_TYPES]


def test_there_is_a_contract_for_every_server_type_that_maps_to_a_dialect():
    """A new server type in the dialect map needs a contract here, or its SQL
    rules go untested."""
    covered = {path.stem for path in CONTRACTS}

    assert set(_DIALECT_BY_SERVER_TYPE) - covered == set(), "server types with no quality-sql contract"


@pytest.mark.parametrize("contract_path", CONTRACTS, ids=lambda p: p.stem)
def test_the_contract_is_valid(contract_path):
    run = DataContract(data_contract_file=str(contract_path), inline_references=False).lint()

    assert run.result == ResultEnum.passed, [check.reason for check in run.checks if check.reason]


@pytest.mark.parametrize("contract_path", CONTRACTS, ids=lambda p: p.stem)
def test_every_sql_quality_rule_becomes_an_executable_check(contract_path):
    """The rules are neither refused by the guard nor silently dropped."""
    server, checks = _sql_checks(contract_path)

    assert checks, "the contract declares SQL quality rules, so it must produce SQL checks"
    refused = [(check.name, check.preset_reason) for check in checks if check.preset_result == "failed"]
    assert refused == [], f"{get_server_type(server)} SQL was refused: {refused}"


@pytest.mark.parametrize("contract_path", CONTRACTS, ids=lambda p: p.stem)
def test_placeholders_are_substituted_before_the_query_is_read(contract_path):
    """`${model}` is not SQL, so a query still holding one would be refused. The
    guard runs after substitution -- this asserts none leaked through."""
    _, checks = _sql_checks(contract_path)

    for check in checks:
        assert "${" not in (check.query or ""), check.query
        assert "{model}" not in (check.query or ""), check.query


@pytest.mark.parametrize("contract_path", CONTRACTS, ids=lambda p: p.stem)
def test_the_queries_are_read_in_the_dialect_of_their_server(contract_path):
    server, checks = _sql_checks(contract_path)
    dialect = dialect_for_server_type(get_server_type(server))

    assert dialect is not None, "a server type with SQL rules needs a dialect"
    for check in checks:
        assert is_read_only_query(check.query, dialect), check.query


def test_some_rules_only_parse_in_their_own_dialect():
    """Without the dialect these contracts would break, so at least some of the
    fixtures have to use syntax that generic SQL cannot read. Otherwise the
    suite above would still pass with the dialect derivation removed."""
    dialect_only = []
    for contract_path in CONTRACTS:
        server, checks = _sql_checks(contract_path)
        dialect = dialect_for_server_type(get_server_type(server))
        for check in checks:
            if is_read_only_query(check.query, dialect) and not is_read_only_query(check.query):
                dialect_only.append((contract_path.stem, check.query))

    technologies = {stem for stem, _ in dialect_only}
    # Which queries need their dialect moves with the sqlglot version (it reads
    # more syntax generically over time), so this is a floor with headroom rather
    # than the exact count -- it catches fixtures that stopped proving the point,
    # without failing on a dependency bump.
    assert len(technologies) >= 3, f"only {technologies} exercise dialect-specific syntax"


@pytest.mark.parametrize("contract_path", CONTRACTS, ids=lambda p: p.stem)
def test_a_statement_that_is_not_a_query_is_still_refused_for_this_technology(contract_path):
    """The guard is not disabled for any technology: whatever dialect the server
    implies, a `DROP TABLE` in a quality rule is refused."""
    contract_yaml = contract_path.read_text()
    data_contract = resolve.resolve_data_contract(data_contract_str=contract_yaml, inline_references=False)
    server = get_server(data_contract, None)

    for schema_object in data_contract.schema_:
        for quality in schema_object.quality or []:
            quality.query = "DROP TABLE orders"

    checks = [spec for spec in create_checks(data_contract, server) if spec.type in SQL_CHECK_TYPES]

    assert checks
    assert all(check.preset_result == "failed" for check in checks)


@pytest.mark.parametrize("contract_path", CONTRACTS, ids=lambda p: p.stem)
def test_building_the_checks_logs_no_warning(contract_path, caplog):
    """A rule dropped for a missing threshold or query is only a log line, so a
    fixture could pass the assertions above while testing nothing."""
    with caplog.at_level(logging.WARNING, logger="datacontract.engines.checks.create_checks"):
        _sql_checks(contract_path)

    assert [record.getMessage() for record in caplog.records] == []
