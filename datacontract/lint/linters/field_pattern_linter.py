import re

from datacontract.model.data_contract_specification import DataContractSpecification
from ..lint import Linter, LinterResult


class FieldPatternLinter(Linter):
    """Checks that all patterns defined for fields are correct Python regex
    syntax.

    """

    @property
    def name(self):
        return "Field pattern is correct regex"

    @property
    def id(self) -> str:
        return "field-pattern"

    def lint_implementation(self, contract: DataContractSpecification) -> LinterResult:
        result = LinterResult()
        for model_name, model in contract.models.items():
            for field_name, field in model.fields.items():
                if field.pattern:
                    try:
                        re.compile(field.pattern)
                    except re.error as e:
                        result = result.with_error(
                            f"Failed to compile pattern regex '{field.pattern}' for "
                            f"field '{field_name}' in model '{model_name}': {e.msg}"
                        )
        return result
