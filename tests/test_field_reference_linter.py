import datacontract.model.data_contract_specification as spec
from datacontract.lint.linters.field_reference_linter import FieldReferenceLinter
from datacontract.model.run import Check


def construct_error_check(msg: str) -> Check:
    return Check(
        type="lint",
        name="Linter 'Field references existing field'",
        result="warning",
        engine="datacontract",
        reason=msg,
    )


success_check = Check(
    type="lint", name="Linter 'Field references existing field'", result="passed", engine="datacontract"
)

linter = FieldReferenceLinter()


def test_correct_field_reference():
    specification = spec.DataContractSpecification(
        models={
            "test_model_1": spec.Model(fields={"test_field_1": spec.Field(references="test_model_2.test_field_1")}),
            "test_model_2": spec.Model(fields={"test_field_1": spec.Field()}),
        }
    )
    assert linter.lint(specification) == [success_check]


def test_incorrect_model_reference():
    specification = spec.DataContractSpecification(
        models={"test_model_1": spec.Model(fields={"test_field_1": spec.Field(references="test_model_2.test_field_1")})}
    )
    assert linter.lint(specification) == [
        construct_error_check(
            "Field 'test_field_1' in model 'test_model_1' references non-existing model 'test_model_2'."
        )
    ]


def test_incorrect_field_reference():
    specification = spec.DataContractSpecification(
        models={
            "test_model_1": spec.Model(fields={"test_field_1": spec.Field(references="test_model_2.test_field_1")}),
            "test_model_2": spec.Model(),
        }
    )
    assert linter.lint(specification) == [
        construct_error_check(
            "Field 'test_field_1' in model 'test_model_1' references non-existing field 'test_field_1'"
            " in model 'test_model_2'."
        )
    ]
