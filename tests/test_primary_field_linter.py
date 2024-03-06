from datacontract.lint.linters.primary_field_linter import PrimaryFieldUniqueRequired
import datacontract.lint.resolve as resolve
import datacontract.model.data_contract_specification as spec
from datacontract.model.run import Check


def construct_error_check(msg: str) -> Check:
    return Check(
        type="lint",
        name="Linter 'Model primary fields unique and required'",
        result="warning",
        engine="datacontract",
        reason=msg,
    )


success_check = Check(
    type="lint",
    name="Linter 'Model primary fields unique and required'",
    result="passed",
    engine="datacontract"
)

linter = PrimaryFieldUniqueRequired()

def test_correct_model():
    specification = spec.DataContractSpecification(
        models={
            "test_model": spec.Model(
                fields={
                    "test_field": spec.Field(primary=True, unique=True, required=True)
                }
            )
        })
    assert linter.lint(specification) == [success_check]

def test_incorrect_model():
    specification = spec.DataContractSpecification(
    models={
        "test_model": spec.Model(
            fields={
                "test_field": spec.Field(primary=True)
            }
        )
    })
    assert linter.lint(specification) == [construct_error_check(
        "Field 'test_field' in model 'test_model' is marked as "
        "primary, but not as unique and required.")]
    
