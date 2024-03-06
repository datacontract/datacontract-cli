from ..lint import Linter, LinterResult
from datacontract.model.data_contract_specification import DataContractSpecification

class FieldReferenceLinter(Linter):
    @property
    def name(self):
        return "Field references existing field"

    def lint_implementation(
        self,
        contract: DataContractSpecification
    ) -> LinterResult:
        result = LinterResult()
        for (model_name, model) in contract.models.items():
            for (field_name, field) in model.fields.items():
                if field.references:
                    (ref_model, ref_field) = field.references.split(".", maxsplit=2)
                    if ref_model not in contract.models:
                        result = result.with_error(
                            f"Field '{field_name}' in model '{model_name}'"
                            f" references non-existing model '{ref_model}'.")
                    else:
                        ref_model_obj = contract.models[ref_model]
                        if ref_field not in ref_model_obj.fields:
                            result = result.with_error(
                                f"Field '{field_name}' in model '{model_name}'"
                                f" references non-existing field '{ref_field}'"
                                f" in model '{ref_model}'.")
        return result
