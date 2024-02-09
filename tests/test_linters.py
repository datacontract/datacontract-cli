import datacontract.lint.linters as linters
import datacontract.lint.resolve as resolve
import datacontract.lint.result as lint_result
import datacontract.model.data_contract_specification as spec


def test_lint_invalid_model():
    data_contract_file = "examples/lint/datacontract_unknown_model.yaml"
    contract = resolve.resolve_data_contract_from_location(data_contract_file)
    result = linters.linter_examples_conform_to_model(contract)
    expected = lint_result.LinterMessage.error(
        "Example 1 has non-existent model 'orders'")
    assert result.error_results() == [
        expected
    ]
    assert result.warning_results() == []


def test_lint_valid_csv_columns():
    contract = resolve.resolve_data_contract_from_location(
        "examples/lint/datacontract_csv_lint_base.yaml")
    result = linters.linter_examples_conform_to_model(contract)
    assert result.no_errors_or_warnings()


def test_lint_extra_model_columns():
    base_spec = resolve.resolve_data_contract_from_location(
        "examples/lint/datacontract_csv_lint_base.yaml")
    base_spec.models['orders'] = spec.Model(fields={
        "column_1": spec.Field(type="str"),
        "column_2": spec.Field(type="str"),
        "column_3": spec.Field(type="str", required=True)
    })
    result = linters.linter_examples_conform_to_model(base_spec)
    expected = lint_result.LinterMessage.error(
        "Example 1 is missing field 'column_3' required by model 'orders'")
    assert result.error_results() == [
        expected
    ]
    assert result.warning_results() == []


def test_lint_extra_example_columns():
    base_spec = resolve.resolve_data_contract_from_location(
        "examples/lint/datacontract_csv_lint_base.yaml")
    base_spec.examples[0] = spec.Example(
        type="csv",
        model="orders",
        data="column_1, column_2, column_3\nvalue_1, value_2, value_3")
    result = linters.linter_examples_conform_to_model(base_spec)
    expected = lint_result.LinterMessage.error(
        "Example 1 has field 'column_3' that's not contained in model 'orders'")
    assert result.error_results() == [
        expected
    ]
    assert result.warning_results() == []


def test_lint_json_example():
    base_spec = resolve.resolve_data_contract_from_location(
        "examples/lint/datacontract_csv_lint_base.yaml")
    base_spec.examples[0] = spec.Example(
        type="json",
        model="orders",
        data='{"column_1": 1, "column_2": 2}')
    result = linters.linter_examples_conform_to_model(base_spec)
    assert result.no_errors_or_warnings()


def test_lint_json_example_extra_columns():
    base_spec = resolve.resolve_data_contract_from_location(
        "examples/lint/datacontract_csv_lint_base.yaml")
    base_spec.examples[0] = spec.Example(
        type="json",
        model="orders",
        data='{"column_1": 1, "column_2": 2, "column_3": 3}')
    result = linters.linter_examples_conform_to_model(base_spec)
    expected = lint_result.LinterMessage.error(
        "Example 1 has field 'column_3' that's not contained in model 'orders'"
        )
    assert result.error_results() == [
        expected
    ]


def test_lint_yaml_example():
    base_spec = resolve.resolve_data_contract_from_location(
        "examples/lint/datacontract_csv_lint_base.yaml")
    base_spec.examples[0] = spec.Example(
        type="yaml",
        model="orders",
        data="""
column_1: 1
column_2: 2
""")
    result = linters.linter_examples_conform_to_model(base_spec)
    assert result.no_errors_or_warnings()
