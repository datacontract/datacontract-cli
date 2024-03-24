import datacontract.model.data_contract_specification as spec
from datacontract.lint.linters.valid_constraints_linter import ValidFieldConstraintsLinter
from datacontract.model.run import Check


def construct_error_check(msg: str) -> Check:
    return Check(
        type="lint",
        name="Linter 'Fields use valid constraints'",
        result="warning",
        engine="datacontract",
        reason=msg,
    )


success_check = Check(type="lint", name="Linter 'Fields use valid constraints'", result="passed", engine="datacontract")

linter = ValidFieldConstraintsLinter()


def test_empty_constraints():
    specification = spec.DataContractSpecification(
        models={
            "test_model": spec.Model(
                fields={"test_field_1": spec.Field(type="string"), "test_field_2": spec.Field(type="number")}
            )
        }
    )
    assert linter.lint(specification) == [success_check]


def test_correct_constraints():
    specification = spec.DataContractSpecification(
        models={
            "test_model": spec.Model(
                fields={
                    "test_field_1": spec.Field(type="string", minLength=5, maxLength=8),
                    "test_field_2": spec.Field(type="number", minimum=10, maximum=100),
                }
            )
        }
    )
    assert linter.lint(specification) == [success_check]


def test_incorrect_constraints():
    specification = spec.DataContractSpecification(
        models={
            "test_model": spec.Model(
                fields={
                    "test_field_1": spec.Field(type="number", minLength=5),
                    "test_field_2": spec.Field(type="string", maximum=100),
                }
            )
        }
    )
    assert linter.lint(specification) == [
        construct_error_check(
            "Forbidden constraint 'minLength' defined on "
            "field 'test_field_1' in model 'test_model'. "
            "Field type is 'number'."
        ),
        construct_error_check(
            "Forbidden constraint 'maximum' defined on "
            "field 'test_field_2' in model 'test_model'. "
            "Field type is 'string'."
        ),
    ]
