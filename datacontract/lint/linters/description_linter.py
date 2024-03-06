from ..lint import Linter, LinterResult
from datacontract.model.data_contract_specification import\
    DataContractSpecification, Model


class DescriptionLinter(Linter):
    """Check for a description on models, model fields, definitions and examples."""

    @property
    def name(self) -> str:
        return "Objects have descriptions"

    def lint_implementation(
        self,
        contract: DataContractSpecification
    ) -> LinterResult:
        result = LinterResult()
        for (model_name, model) in contract.models.items():
            if not model.description:
                result = result.with_error(
                    f"Model '{model_name}' has empty description."
                )
            for (field_name, field) in model.fields.items():
                if not field.description:
                    result = result.with_error(
                        f"Field '{field_name}' in model '{model_name}'"
                        f" has empty description.")
        for (definition_name, definition) in contract.definitions.items():
            if not definition.description:
                result = result.with_error(
                    f"Definition '{definition_name}' has empty description.")
        for (index, example) in enumerate(contract.examples):
            if not example.description:
                result = result.with_error(
                    f"Example {index + 1} has empty description.")
        return result
