import datacontract.model.data_contract_specification as spec
from datacontract.lint.linters.field_pattern_linter import FieldPatternLinter
from datacontract.model.run import Check


def construct_error_check(msg: str) -> Check:
    return Check(
        type="lint",
        name="Linter 'Field pattern is correct regex'",
        result="warning",
        engine="datacontract",
        reason=msg,
    )


success_check = Check(
    type="lint", name="Linter 'Field pattern is correct regex'", result="passed", engine="datacontract"
)

linter = FieldPatternLinter()


def test_correct_regex_pattern():
    specification = spec.DataContractSpecification(
        models={"test_model": spec.Model(fields={"test_field": spec.Field(pattern=".")})}
    )
    result = linter.lint(specification)
    assert result == [success_check]


def test_incorrect_regex_pattern():
    specification = spec.DataContractSpecification(
        models={"test_model": spec.Model(fields={"test_field": spec.Field(pattern="\\")})}
    )
    result = linter.lint(specification)
    assert result == [
        construct_error_check(
            "Failed to compile pattern regex '\\' for field"
            " 'test_field' in model 'test_model': "
            "bad escape (end of pattern)"
        )
    ]
