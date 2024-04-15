import datacontract.lint.resolve as resolve
from datacontract.lint.linters.quality_schema_linter import QualityUsesSchemaLinter
from datacontract.model.run import Check


def construct_error_check(msg: str) -> Check:
    return Check(
        type="lint",
        name="Linter 'Quality check(s) use model'",
        result="warning",
        engine="datacontract",
        reason=msg,
    )


success_check = Check(type="lint", name="Linter 'Quality check(s) use model'", result="passed", engine="datacontract")

data_contract_file = "fixtures/lint/datacontract_quality_schema.yaml"


def test_lint_correct_sodacl():
    base_contract_sodacl = resolve.resolve_data_contract_from_location(data_contract_file)
    result = QualityUsesSchemaLinter().lint(base_contract_sodacl)
    assert result == [success_check]


def test_lint_incorrect_sodacl():
    base_contract_sodacl = resolve.resolve_data_contract_from_location(data_contract_file)
    incorrect_contract = base_contract_sodacl.model_copy(deep=True)
    incorrect_contract.quality.specification = """
      checks for tests:
      - freshness(column_1) < 1d
    """
    result = QualityUsesSchemaLinter().lint(incorrect_contract)
    assert result == [construct_error_check("Quality check on unknown model 'tests'")]
