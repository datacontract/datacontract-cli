import datacontract.lint.resolve as resolve
import datacontract.model.data_contract_specification as spec
from datacontract.lint.linters.example_model_linter import ExampleModelLinter
from datacontract.model.run import Check


def construct_error_check(msg: str) -> Check:
    return Check(
        type="lint", name="Linter 'Example(s) match model'", result="warning", engine="datacontract", reason=msg
    )


success_check = Check(type="lint", name="Linter 'Example(s) match model'", result="passed", engine="datacontract")


def test_lint_invalid_model():
    data_contract_file = "fixtures/lint/datacontract_unknown_model.yaml"
    contract = resolve.resolve_data_contract_from_location(data_contract_file)
    result = ExampleModelLinter().lint(contract)
    expected = construct_error_check("Example 1 has non-existent model 'orders'")
    assert result == [expected]


def test_lint_valid_csv_columns():
    contract = resolve.resolve_data_contract_from_location("fixtures/lint/datacontract_csv_lint_base.yaml")
    result = ExampleModelLinter().lint(contract)
    assert result == [success_check]


def test_lint_extra_model_columns():
    base_spec = resolve.resolve_data_contract_from_location("fixtures/lint/datacontract_csv_lint_base.yaml")
    base_spec.models["orders"] = spec.Model(
        fields={
            "column_1": spec.Field(type="str"),
            "column_2": spec.Field(type="str"),
            "column_3": spec.Field(type="str", required=True),
        }
    )
    result = ExampleModelLinter().lint(base_spec)
    expected = construct_error_check("Example 1 is missing field 'column_3' required by model 'orders'")
    assert result == [expected]


def test_lint_extra_example_columns():
    base_spec = resolve.resolve_data_contract_from_location("fixtures/lint/datacontract_csv_lint_base.yaml")
    base_spec.examples[0] = spec.Example(
        type="csv", model="orders", data="column_1, column_2, column_3\nvalue_1, value_2, value_3"
    )
    result = ExampleModelLinter().lint(base_spec)
    expected = construct_error_check("Example 1 has field 'column_3' that's not contained in model 'orders'")
    assert result == [expected]


def test_lint_json_example():
    base_spec = resolve.resolve_data_contract_from_location("fixtures/lint/datacontract_csv_lint_base.yaml")
    base_spec.examples[0] = spec.Example(type="json", model="orders", data='{"column_1": 1, "column_2": 2}')
    result = ExampleModelLinter().lint(base_spec)
    assert result == [success_check]


def test_lint_json_example_extra_columns():
    base_spec = resolve.resolve_data_contract_from_location("fixtures/lint/datacontract_csv_lint_base.yaml")
    base_spec.examples[0] = spec.Example(
        type="json", model="orders", data='{"column_1": 1, "column_2": 2, "column_3": 3}'
    )
    result = ExampleModelLinter().lint(base_spec)
    expected = construct_error_check("Example 1 has field 'column_3' that's not contained in model 'orders'")
    assert result == [expected]


def test_lint_yaml_example():
    base_spec = resolve.resolve_data_contract_from_location("fixtures/lint/datacontract_csv_lint_base.yaml")
    base_spec.examples[0] = spec.Example(
        type="yaml",
        model="orders",
        data="""
column_1: 1
column_2: 2
""",
    )
    result = ExampleModelLinter().lint(base_spec)
    assert result == [success_check]
