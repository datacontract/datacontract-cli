"""A data contract carries SQL, so a contract the caller did not write must not
be able to reach the machine that runs it.

Two independent controls, tested here:
  1. custom SQL must be a read-only query -- for every data source
  2. duckdb is confined to the contract's own data locations
"""

import pytest
from fastapi.testclient import TestClient

from datacontract.api import ALLOW_LOCAL_FILES_ENV, app
from datacontract.data_contract import DataContract
from datacontract.engines.checks.sql_guard import dialect_for_server_type, is_read_only_query
from datacontract.engines.ibis.connections.duckdb_connection import restrict_to_paths
from datacontract.model.run import ResultEnum

client = TestClient(app)


def _contract(path: str, query: str = None, must_be: int = 0) -> str:
    quality = ""
    if query is not None:
        quality = f"""
    quality:
      - type: sql
        query: "{query}"
        mustBe: {must_be}
"""
    return f"""apiVersion: v3.0.2
kind: DataContract
id: orders
name: Orders
version: 1.0.0
status: active
servers:
  - server: production
    type: local
    path: {path}
    format: json
schema:
  - name: orders
    properties:
      - name: id
        logicalType: string
{quality}
"""


@pytest.fixture
def data_file(tmp_path):
    file = tmp_path / "orders.json"
    file.write_text('{"id": "1"}\n')
    return file


@pytest.fixture
def secret_file(tmp_path):
    file = tmp_path / "secret.txt"
    file.write_text("AWS_SECRET=super-secret-value")
    return file


# --- 1. custom SQL must be a read-only query -------------------------------


@pytest.mark.parametrize(
    "query",
    [
        "SELECT count(*) FROM orders",
        "WITH counted AS (SELECT count(*) AS n FROM orders) SELECT n FROM counted",
        "SELECT count(*) FROM orders UNION ALL SELECT count(*) FROM orders",
        "(SELECT count(*) FROM orders)",
        "SELECT count(*) FROM orders;",
    ],
)
def test_a_query_is_read_only(query):
    assert is_read_only_query(query)


@pytest.mark.parametrize(
    "statement",
    [
        "DROP TABLE orders",
        "DELETE FROM orders",
        "INSERT INTO orders VALUES ('1')",
        "UPDATE orders SET id = '2'",
        "CREATE TABLE pwn AS SELECT 1",
        # a file write on duckdb, and command execution on postgres
        "COPY (SELECT 1) TO '/tmp/pwn.csv'",
        "COPY orders TO PROGRAM 'sh -c id'",
        "ATTACH '/tmp/pwn.db' AS pwn",
        "INSTALL httpfs",
        "LOAD httpfs",
        "SET enable_external_access = true",
        "PRAGMA version",
        # a second statement smuggled in behind a legitimate one
        "SELECT count(*) FROM orders; DROP TABLE orders",
        # not sql at all: refused rather than passed through
        "not a query",
    ],
)
def test_a_statement_that_is_not_a_query_is_refused(statement):
    assert not is_read_only_query(statement)


@pytest.mark.parametrize(
    "server_type, query",
    [
        ("snowflake", "SELECT count(*) FROM orders SAMPLE (10 ROWS)"),
        ("bigquery", "SELECT count(*) FROM `proj.ds.orders` WHERE DATE(order_ts) = CURRENT_DATE()"),
        ("databricks", "SELECT count(*) FROM orders TIMESTAMP AS OF '2026-01-01'"),
        ("sqlserver", "SELECT TOP 1 count(*) FROM orders"),
    ],
)
def test_dialect_specific_syntax_is_read_as_the_server_dialect(server_type, query):
    """A rule that does not name a dialect is read as the dialect of the server it
    runs against. Parsed as generic SQL these are syntax errors, and the guard
    fails closed -- so without this they would be refused for being valid."""
    assert not is_read_only_query(query), "if this parses generically the case no longer tests anything"

    assert is_read_only_query(query, dialect_for_server_type(server_type))


def test_the_server_dialect_still_refuses_what_is_not_a_query():
    for server_type in ("snowflake", "bigquery", "postgres", "local"):
        assert not is_read_only_query("DROP TABLE orders", dialect_for_server_type(server_type))


def test_file_server_types_are_read_as_duckdb():
    """local/s3/gcs/azure are read through duckdb, so a rule on them is duckdb SQL."""
    for server_type in ("local", "s3", "gcs", "azure"):
        assert dialect_for_server_type(server_type) == "duckdb"


def test_the_documented_dialect_mapping_matches_the_code():
    """The mapping is a table in docs/docs/quality-rules/sql.md, so it drifts
    silently unless something reads both."""
    from pathlib import Path

    from datacontract.engines.checks.sql_guard import _DIALECT_BY_SERVER_TYPE

    page = Path(__file__).parent.parent / "docs" / "docs" / "quality-rules" / "sql.md"
    documented = {}
    for line in page.read_text().splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 2 or not cells[1].startswith("`"):
            continue
        for server_type in cells[0].split(","):
            documented[server_type.strip().strip("`")] = cells[1].strip("`")

    # `mssql` is an accepted spelling of sqlserver rather than its own ODCS server
    # type, so it is deliberately not in the documented table.
    assert documented == {k: v for k, v in _DIALECT_BY_SERVER_TYPE.items() if k != "mssql"}


def test_an_unmapped_server_type_has_no_dialect():
    assert dialect_for_server_type("no-such-server-type") is None
    assert dialect_for_server_type(None) is None


def test_a_refused_query_names_the_dialect_it_was_read_as(data_file):
    """`TOP` is SQL Server syntax; the contract declares a local (duckdb) server,
    so the query is not valid for the data source it would run against."""
    run = DataContract(
        data_contract_str=_contract(data_file, "SELECT TOP 1 count(*) FROM orders"),
        inline_references=False,
    ).test()

    check = next(c for c in run.checks if c.type == "model_quality_sql")
    assert check.result == ResultEnum.failed
    assert "duckdb SQL" in check.reason


def test_an_unmapped_dialect_does_not_reject_a_valid_query():
    """A dialect name sqlglot does not know is about the parser, not the query."""
    assert is_read_only_query("SELECT count(*) FROM orders", dialect="no-such-dialect")
    assert not is_read_only_query("DROP TABLE orders", dialect="no-such-dialect")


def test_a_quality_rule_that_is_not_a_query_fails_without_running(data_file, tmp_path):
    written = tmp_path / "written-by-the-contract.csv"

    run = DataContract(
        data_contract_str=_contract(data_file, f"COPY (SELECT 1) TO '{written}'"),
        inline_references=False,
    ).test()

    check = next(c for c in run.checks if c.type == "model_quality_sql")
    assert check.result == ResultEnum.failed
    assert "read-only query" in check.reason
    assert not written.exists()


# --- 2. duckdb is confined to the contract's own data locations -------------


def test_an_untrusted_contract_cannot_read_another_file(data_file, secret_file):
    """`read_text` is a read-only query, so it passes the first control and has
    to be stopped by the second one."""
    query = f"SELECT content FROM read_text('{secret_file}')"
    assert is_read_only_query(query), "the point of this test is a query the first control lets through"

    run = DataContract(
        data_contract_str=_contract(data_file, query),
        untrusted_contract=True,
        inline_references=False,
    ).test()

    assert "super-secret-value" not in run.model_dump_json()
    assert "Permission Error" in run.model_dump_json(), "duckdb should be the one refusing it"


def test_a_trusted_contract_reads_the_file_the_user_named(data_file, secret_file):
    """The counterpart: on the command line the file is the user's own, so the
    sandbox is not applied and the same query runs. This is what makes the
    assertion above a real result rather than a broken query."""
    run = DataContract(
        data_contract_str=_contract(data_file, f"SELECT content FROM read_text('{secret_file}')"),
        inline_references=False,
    ).test()

    assert "super-secret-value" in run.model_dump_json()


def test_an_untrusted_contract_still_reads_its_own_data(data_file):
    run = DataContract(
        data_contract_str=_contract(data_file, "SELECT count(*) FROM orders", must_be=1),
        untrusted_contract=True,
        inline_references=False,
    ).test()

    check = next(c for c in run.checks if c.type == "model_quality_sql")
    assert check.result == ResultEnum.passed


def test_the_sandbox_cannot_be_undone(tmp_path):
    """`restrict_to_paths` relies on duckdb refusing to widen the restriction
    once external access is off. If a future duckdb stops refusing, this fails
    rather than the sandbox quietly becoming decorative."""
    duckdb = pytest.importorskip("duckdb")
    allowed = tmp_path / "orders.json"
    allowed.write_text('{"id": "1"}\n')
    secret = tmp_path / "secret.txt"
    secret.write_text("super-secret-value")

    con = duckdb.connect(database=":memory:")
    restrict_to_paths(con, [str(allowed)])

    assert con.sql(f"SELECT * FROM read_json_auto('{allowed}')").fetchall() == [("1",)]
    for escape in (
        f"SELECT content FROM read_text('{secret}')",
        f"COPY (SELECT 1) TO '{tmp_path}/written.csv'",
        f"ATTACH '{tmp_path}/pwn.db' AS pwn",
        "SET enable_external_access = true",
        f"SET allowed_paths = ['{secret}']",
        "SET allowed_directories = ['/']",
    ):
        with pytest.raises(Exception):
            con.sql(escape)
    assert not (tmp_path / "written.csv").exists()


def test_a_glob_location_allows_its_directory_only(tmp_path):
    """A location duckdb has to glob cannot be pinned as an exact file, so the
    directory it globs is allowed instead -- and nothing above it."""
    duckdb = pytest.importorskip("duckdb")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "a.json").write_text('{"id": "1"}\n')
    (tmp_path / "secret.txt").write_text("super-secret-value")

    con = duckdb.connect(database=":memory:")
    restrict_to_paths(con, [f"{data_dir}/*.json"])

    assert con.sql(f"SELECT * FROM read_json_auto('{data_dir}/*.json')").fetchall() == [("1",)]
    with pytest.raises(Exception):
        con.sql(f"SELECT content FROM read_text('{tmp_path}/secret.txt')")


# --- 3. the API refuses a server type that reads its own disk ---------------


def test_the_api_refuses_a_local_server_type(data_file):
    response = client.post("/test", content=_contract(data_file), headers={"Content-Type": "application/yaml"})

    assert response.status_code == 422
    assert "file system of the server" in response.json()["detail"]


def test_an_operator_can_allow_local_files(data_file, monkeypatch):
    """A deployment that serves its own files on purpose opts in; the sandbox
    still confines the contract to the path it declares."""
    monkeypatch.setenv(ALLOW_LOCAL_FILES_ENV, "true")

    response = client.post("/test", content=_contract(data_file), headers={"Content-Type": "application/yaml"})

    assert response.status_code == 200


def test_a_caller_cannot_opt_themselves_in(data_file):
    """The opt-in is the operator's, so it is not a Config option and cannot be
    set through a per-request `datacontract-*` header."""
    response = client.post(
        "/test",
        content=_contract(data_file),
        headers={"Content-Type": "application/yaml", "datacontract-cli-api-allow-local-files": "true"},
    )

    assert response.status_code != 200


def test_the_cli_still_tests_a_local_server_type(data_file):
    """The guard is about contracts arriving over HTTP; a file the user names on
    the command line is theirs to read."""
    run = DataContract(data_contract_str=_contract(data_file), inline_references=False).test()

    assert run.result != ResultEnum.error
