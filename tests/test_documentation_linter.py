import datacontract.model.data_contract_specification as spec
from datacontract.lint.linters.description_linter import DescriptionLinter
from datacontract.model.run import Check


def construct_error_check(msg: str) -> Check:
    return Check(
        type="lint",
        name="Linter 'Objects have descriptions'",
        result="warning",
        engine="datacontract",
        reason=msg,
    )


success_check = Check(type="lint", name="Linter 'Objects have descriptions'", result="passed", engine="datacontract")

linter = DescriptionLinter()


def test_correct_contract():
    specification = spec.DataContractSpecification(
        info=spec.Info(description="Test contract description"),
        models={
            "test_model": spec.Model(
                description="Test model description",
                fields={"test_field": spec.Field(description="Test field description")},
            )
        },
        examples=[spec.Example(description="Example description")],
        definitions={"test_definition": spec.Definition(description="Test description definition")},
    )
    assert linter.lint(specification) == [success_check]


def test_missing_contract():
    specification = spec.DataContractSpecification(
        models={"test_model": spec.Model(fields={"test_field": spec.Field()})},
        examples=[spec.Example()],
        definitions={"test_definition": spec.Definition()},
    )
    assert linter.lint(specification) == [
        construct_error_check("Contract has empty description."),
        construct_error_check("Model 'test_model' has empty description."),
        construct_error_check("Field 'test_field' in model 'test_model' has empty description."),
        construct_error_check("Definition 'test_definition' has empty description."),
        construct_error_check("Example 1 has empty description."),
    ]
