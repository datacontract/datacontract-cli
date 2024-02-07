import datacontract.lint.linters as linters
import datacontract.lint.resolve as resolve
import datacontract.lint.result as lint_result

def test_lint_invalid_model():
    data_contract_file = "examples/lint/datacontract_unknown_model.yaml"
    spec = resolve.resolve_data_contract_from_location(data_contract_file)
    result = linters.linter_example_schema(spec)
    expected = lint_result.LinterResult.error("Example 1 has non-existent model 'orders'")
    assert not result.no_errors_or_warnings()
    assert result.error_results() == [
        expected
        ]
