"""Custom quality checks: SQL checks defined once in a folder and used by name from a contract."""

import json

import pytest
from open_data_contract_standard.model import Server

from datacontract.config import Config
from datacontract.data_contract import DataContract
from datacontract.engines.checks.create_checks import create_checks
from datacontract.model.run import ResultEnum

CHECKS = "./fixtures/custom-quality-checks/checks"
CSV_PATH = "./fixtures/diagnostics/data/orders.csv"


def _contract(property_quality: str = "", schema_quality: str = "", items_quality: str = "") -> str:
    return f"""
apiVersion: v3.1.0
kind: DataContract
id: custom_quality_checks_test
version: 1.0.0
status: active
servers:
  - server: local
    type: local
    path: {CSV_PATH}
    format: csv
schema:
  - name: orders
    properties:
      - name: email
        logicalType: string
      - name: amount
        logicalType: integer
{property_quality}
      - name: tags
        logicalType: array
        items:
          logicalType: string
{items_quality}
{schema_quality}
"""


def _amount_rule(rule: str) -> str:
    return "        quality:\n" + "\n".join(f"          {line}" for line in rule.strip().splitlines())


def _schema_rule(rule: str) -> str:
    return "    quality:\n" + "\n".join(f"      {line}" for line in rule.strip().splitlines())


def _test(contract: str, checks: str = CHECKS):
    return DataContract(data_contract_str=contract, config=Config(custom_quality_checks=checks)).test()


def _specs(contract: str, checks: str | None = CHECKS, server: Server | None = None):
    odcs = DataContract(data_contract_str=contract).get_data_contract()
    return [
        spec
        for spec in create_checks(odcs, server or odcs.servers[0], custom_quality_checks=checks)
        if spec.type in ("field_quality_custom", "model_quality_custom")
    ]


BETWEEN = """
- type: custom
  engine: datacontract-cli
  implementation:
    check: between
    arguments:
      min: 0
      max: 100
"""


def test_a_violated_check_fails_with_the_rendered_description_as_name():
    run = _test(_contract(property_quality=_amount_rule(BETWEEN)))

    check = next(c for c in run.checks if c.type == "field_quality_custom")
    assert check.result == ResultEnum.failed
    assert check.name == "amount between 0 and 100."
    assert check.category == "quality"
    assert check.dimension == "conformity"
    assert "amount < 0 OR amount > 100" in check.implementation
    assert check.diagnostics["value"] == 2
    assert check.diagnostics["custom_quality_check"] == "between"
    assert check.diagnostics["query"] == "ansi"
    assert check.diagnostics["expected_result_from"] == "check"
    assert "check: between" in check.qualityDefinition


def test_the_rule_overrides_the_expected_result_and_the_dimension():
    rule = BETWEEN + "  dimension: accuracy\n  mustBeLessOrEqualTo: 2\n"
    run = _test(_contract(property_quality=_amount_rule(rule)))

    check = next(c for c in run.checks if c.type == "field_quality_custom")
    assert check.result == ResultEnum.passed
    assert check.dimension == "accuracy"
    assert check.diagnostics["expected_result_from"] == "rule"
    assert "mustBeLessOrEqualTo: 2" in check.qualityDefinition
    assert "mustBe: 0" not in check.qualityDefinition


def test_an_identifier_argument_becomes_a_name_and_the_call_form_names_the_check():
    rule = """
- type: custom
  engine: datacontract-cli
  implementation:
    check: distinct_values
    arguments:
      of: email
  mustBe: 5
"""
    run = _test(_contract(schema_quality=_schema_rule(rule)))

    check = next(c for c in run.checks if c.type == "model_quality_custom")
    assert check.result == ResultEnum.passed
    assert check.name == "distinct_values(of=email)"
    assert "COUNT(DISTINCT email)" in check.implementation


def test_value_arguments_become_literals_and_cannot_change_the_query():
    rule = """
- type: custom
  engine: datacontract-cli
  implementation:
    check: not_in
    arguments:
      values: ["O'Brien", "0) OR (1=1"]
"""
    [spec] = _specs(_contract(property_quality=_amount_rule(rule)))

    assert spec.query.endswith("WHERE amount IN ('O''Brien', '0) OR (1=1')")


def test_a_variable_in_an_argument_is_text_even_when_it_holds_a_number(monkeypatch):
    monkeypatch.setenv("MAX_AMOUNT", "100")
    rule = BETWEEN.replace("max: 100", "max: ${MAX_AMOUNT}")
    run = _test(_contract(property_quality=_amount_rule(rule)))

    check = next(c for c in run.checks if c.type == "field_quality_custom")
    assert "amount > '100'" in check.implementation
    assert check.result == ResultEnum.failed
    assert check.diagnostics["value"] == 2


def test_a_contract_variable_in_an_argument_is_resolved_into_a_literal(monkeypatch):
    monkeypatch.setenv("MAX_AMOUNT", "1000) OR (1=1")
    rule = BETWEEN.replace("max: 100", "max: ${MAX_AMOUNT}")
    run = _test(_contract(property_quality=_amount_rule(rule)))

    check = next(c for c in run.checks if c.type == "field_quality_custom")
    assert "amount > '1000) OR (1=1'" in check.implementation


def _rule(check: str, arguments: str = "", extra: str = "") -> str:
    rule = f"- type: custom\n  engine: datacontract-cli\n  implementation:\n    check: {check}\n"
    if arguments:
        rule += "    arguments:\n" + "".join(f"      {line}\n" for line in arguments.strip().splitlines())
    return rule + "".join(f"  {line}\n" for line in extra.strip().splitlines())


def _unexecuted(spec, result: str, reason: str):
    assert spec.preset_result == result
    assert reason in spec.preset_reason


def test_a_rule_without_a_configured_folder_is_an_error():
    [spec] = _specs(_contract(property_quality=_amount_rule(BETWEEN)), checks=None)
    _unexecuted(spec, "error", "--custom-quality-checks")


def test_an_unknown_check_is_an_error_naming_the_available_ones():
    [spec] = _specs(_contract(property_quality=_amount_rule(_rule("betwen"))))
    _unexecuted(spec, "error", "no custom quality check named 'betwen'. Available: between, distinct_values")


def test_a_check_defined_twice_is_an_error(tmp_path):
    (tmp_path / "between.yaml").write_text("queries: {ansi: SELECT 1}\nmustBe: 1\n")
    (tmp_path / "between.yml").write_text("queries: {ansi: SELECT 1}\nmustBe: 1\n")
    [spec] = _specs(_contract(property_quality=_amount_rule(_rule("between"))), checks=str(tmp_path))
    _unexecuted(spec, "error", "defined twice: between.yaml, between.yml")


@pytest.mark.parametrize(
    "content, reason",
    [
        ("queries: {ansi: SELECT 1}\nmustbe: 0\n", "unknown key mustbe"),
        ("queries: {sqlserver: SELECT 1}\nmustBe: 0\n", "queries.sqlserver is not a known dialect"),
        ("queries: {ansi: SELECT 1}\nmustBe: 0\nmustBeLessThan: 1\n", "only one expected result"),
        ("queries: {ansi: 'SELECT COUNT(*) FROM ${table}_${ENV}'}\nmustBe: 0\n", "${ENV} is neither"),
        ("queries: {ansi: 'SELECT TOP 1 x FROM ${table}'}\nmustBe: 0\n", "is not portable SQL"),
        ("mustBe: 0\n", "needs queries"),
    ],
)
def test_a_broken_check_file_is_an_error(tmp_path, content, reason):
    (tmp_path / "broken.yaml").write_text(content)
    [spec] = _specs(_contract(schema_quality=_schema_rule(_rule("broken"))), checks=str(tmp_path))
    _unexecuted(spec, "error", reason)


def test_wrong_use_of_an_existing_check_warns():
    rules = "\n".join(
        [
            _rule("between", "min: 0\nmax: 1\nmni: 0"),
            _rule("between", "min: 0"),
            _rule("distinct_values", "of: email"),
            _rule("distinct_values", "of: 1", "mustBe: 5"),
        ]
    )
    specs = _specs(_contract(property_quality=_amount_rule(rules)))
    _unexecuted(specs[0], "warning", "has no argument mni")
    _unexecuted(specs[1], "warning", "needs the argument max")
    _unexecuted(specs[2], "warning", "Neither the rule nor the custom quality check 'distinct_values' sets")
    _unexecuted(specs[3], "warning", "The argument of names a column or table")


def test_a_mapping_as_value_argument_warns():
    [spec] = _specs(_contract(property_quality=_amount_rule(_rule("between", "min: {a: 1}\nmax: 1"))))
    _unexecuted(spec, "warning", "The argument min must be a single value or a list of values")


def test_a_dry_run_reports_a_missing_folder_as_an_error():
    run = DataContract(data_contract_str=_contract(property_quality=_amount_rule(BETWEEN)), dry_run=True).test()

    check = next(c for c in run.checks if c.type == "field_quality_custom")
    assert check.result == ResultEnum.error


def test_the_dimension_of_the_check_selects_the_rule():
    contract = _contract(property_quality=_amount_rule(BETWEEN))
    config = Config(custom_quality_checks=CHECKS)

    selected = DataContract(data_contract_str=contract, dimensions={"conformity"}, config=config).test()
    not_selected = DataContract(data_contract_str=contract, dimensions={"timeliness"}, config=config).test()

    assert any(c.type == "field_quality_custom" for c in selected.checks)
    assert not any(c.type == "field_quality_custom" for c in not_selected.checks)


def test_a_column_check_on_a_schema_warns():
    [spec] = _specs(_contract(schema_quality=_schema_rule(_rule("between", "min: 0\nmax: 1"))))
    _unexecuted(spec, "warning", "refers to the column, so declare it on a property")


def test_a_rule_on_an_array_item_warns():
    items_quality = "          quality:\n" + "".join(
        f"            {line}\n" for line in _rule("not_in", "values: [a]").splitlines()
    )
    [spec] = _specs(_contract(items_quality=items_quality))
    _unexecuted(spec, "warning", "is an array item, not a column")


def test_the_query_of_the_rule_dialect_is_used_and_otherwise_ansi_or_nothing():
    contract = _contract(schema_quality=_schema_rule(_rule("tsql_only")))
    [on_duckdb] = _specs(contract)
    _unexecuted(on_duckdb, "warning", "has no query for duckdb and no ansi query")

    [on_sqlserver] = _specs(contract, server=Server(server="production", type="sqlserver"))
    assert on_sqlserver.query == "SELECT TOP 1 COUNT(*) FROM orders"
    assert on_sqlserver.diagnostics["query"] == "tsql"


def test_the_call_form_quotes_only_strings_that_would_be_misread(tmp_path):
    (tmp_path / "codes.yaml").write_text(
        "arguments:\n  codes:\n  strict: {default: true}\n"
        "queries: {ansi: 'SELECT COUNT(*) FROM ${table} WHERE ${column} IN (${arguments.codes})'}\nmustBe: 0\n"
    )
    rule = _rule("codes", 'codes: ["007", "a, b", "", plain, 7]')
    [spec] = _specs(_contract(property_quality=_amount_rule(rule)), checks=str(tmp_path))

    assert spec.name == "codes(codes=['007', 'a, b', '', plain, 7], strict=true)"


def test_the_cli_reads_the_folder_from_the_option(tmp_path):
    from typer.testing import CliRunner

    from datacontract.cli import app

    contract = tmp_path / "datacontract.yaml"
    contract.write_text(_contract(property_quality=_amount_rule(BETWEEN)).replace(CSV_PATH, CSV_PATH[2:]))
    output = tmp_path / "results.json"
    CliRunner().invoke(app, ["test", str(contract), "--custom-quality-checks", CHECKS, "--output", str(output)])

    assert "amount between 0 and 100." in output.read_text()


def test_ci_reads_the_folder_from_the_option(tmp_path):
    from typer.testing import CliRunner

    from datacontract.cli import app

    contract = tmp_path / "datacontract.yaml"
    contract.write_text(_contract(property_quality=_amount_rule(BETWEEN)).replace(CSV_PATH, CSV_PATH[2:]))
    result = CliRunner().invoke(app, ["ci", str(contract), "--custom-quality-checks", CHECKS, "--json"])

    assert "amount between 0 and 100." in result.stdout


def _check_file(tmp_path, name: str, arguments: str, query: str) -> str:
    (tmp_path / f"{name}.yaml").write_text(f'arguments:\n{arguments}queries:\n  ansi: "{query}"\nmustBe: 0\n')
    return str(tmp_path)


@pytest.mark.parametrize(
    "text, count",
    [("@test", 2), ("x%' OR 1=1 OR email LIKE '", 0), ("O'Brien", 0)],
)
def test_a_value_inside_a_string_is_escaped_into_it(tmp_path, text, count):
    checks = _check_file(
        tmp_path, "contains", "  text:\n", "SELECT COUNT(*) FROM ${table} WHERE email LIKE '%${arguments.text}%'"
    )
    rule = _rule("contains", f"text: {json.dumps(text)}", f"mustBe: {count}")
    run = _test(_contract(schema_quality=_schema_rule(rule)), checks)

    check = next(c for c in run.checks if c.type == "model_quality_custom")
    assert check.result == ResultEnum.passed, check.reason


@pytest.mark.parametrize(
    "query, value, rendered",
    [
        ("WHERE ${column} > now() - INTERVAL '${arguments.x} days'", 7, "INTERVAL '7 days'"),
        ("WHERE ${column} = '${arguments.x}'", 10115, "amount = '10115'"),
        ("WHERE ${column} = '${arguments.x}'", True, "amount = 'true'"),
        ("WHERE ${column} < 5 -${arguments.x} AND 1 = 1", -1, "amount < 5 -(-1) AND 1 = 1"),
    ],
)
def test_quotes_around_a_value_make_it_a_string_and_a_negative_number_is_no_comment(tmp_path, query, value, rendered):
    checks = _check_file(tmp_path, "check", "  x:\n", f"SELECT COUNT(*) FROM ${{table}} {query}")
    [spec] = _specs(_contract(property_quality=_amount_rule(_rule("check", f"x: {json.dumps(value)}"))), checks)

    assert rendered in spec.query


@pytest.mark.parametrize(
    "arguments, query, reason",
    [
        ("  x:\n", "SELECT COUNT(*) FROM ${table} -- ${arguments.x}", "${arguments.x} in queries.ansi must stand on"),
        ("  x:\n", 'SELECT COUNT(*) FROM ${table} WHERE a = \\"${arguments.x}\\"', "${arguments.x} in queries.ansi"),
        ("  x:\n", "SELECT COUNT(*) FROM t_${arguments.x}", "${arguments.x} in queries.ansi must stand on"),
        ("", "SELECT COUNT(*) FROM ${table} WHERE note LIKE '%${column}%'", "${column} in queries.ansi names a column"),
        ("  x: {type: identifier}\n", "SELECT COUNT(*) FROM ${table} WHERE a LIKE '${arguments.x}%'", "names a column"),
    ],
)
def test_a_reference_that_does_not_stand_on_its_own_makes_the_check_invalid(tmp_path, arguments, query, reason):
    checks = _check_file(tmp_path, "check", arguments, query)
    rule = _rule("check", "x: amount" if arguments else "")
    [spec] = _specs(_contract(property_quality=_amount_rule(rule)), checks)

    _unexecuted(spec, "error", reason)


def test_a_list_inside_a_string_warns(tmp_path):
    checks = _check_file(
        tmp_path, "check", "  x:\n", "SELECT COUNT(*) FROM ${table} WHERE ${column} LIKE '%${arguments.x}%'"
    )
    [spec] = _specs(_contract(property_quality=_amount_rule(_rule("check", "x: [a, b]"))), checks)

    _unexecuted(spec, "warning", "${arguments.x} is inside a string, so it must be a single value")
