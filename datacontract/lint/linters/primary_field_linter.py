from ..lint import Linter, LinterResult
from datacontract.model.data_contract_specification import DataContractSpecification

class PrimaryFieldUniqueRequired(Linter):
    """Checks that all fields defined as primary are also defined as unique and required."""
    @property
    def name(self) -> str:
        return "Model primary fields unique and required"

    @property
    def id(self) -> str:
        return "notice-period"

    def lint_implementation(
            self,
            contract: DataContractSpecification
    ) -> LinterResult:
        if not contract.models:
            return LinterResult.cautious("No models defined on contract.")
        result = LinterResult()
        for (model_name, model) in contract.models.items():
            for (field_name, field) in model.fields.items():
                if (field.primary
                    and not field.required
                    and not field.unique):
                    result = result.with_error(
                        f"Field '{field_name}' in model '{model_name}'"
                         " is marked as primary, but not as unique"
                         " and required.")
        return result
