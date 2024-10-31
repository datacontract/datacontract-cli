import yaml

from datacontract.model.data_contract_specification import DataContractSpecification, Model

from ..lint import Linter, LinterResult


class QualityUsesSchemaLinter(Linter):
    @property
    def name(self) -> str:
        return "Quality check(s) use model"

    @property
    def id(self) -> str:
        return "quality-schema"

    def lint_sodacl(self, check, models: dict[str, Model]) -> LinterResult:
        result = LinterResult()
        for sodacl_check in check.keys():
            table_name = sodacl_check[len("checks for ") :]
            if table_name not in models:
                result = result.with_error(f"Quality check on unknown model '{table_name}'")
        return result

    def lint_montecarlo(self, check, models: dict[str, Model]) -> LinterResult:
        return LinterResult().with_warning("Linting montecarlo checks is not currently implemented")

    def lint_great_expectations(self, check, models: dict[str, Model]) -> LinterResult:
        return LinterResult().with_warning("Linting great expectations checks is not currently implemented")

    def lint_implementation(self, contract: DataContractSpecification) -> LinterResult:
        result = LinterResult()
        models = contract.models
        check = contract.quality
        if not check:
            return LinterResult()
        if not check.specification:
            return LinterResult.cautious("Quality check without specification.")
        if isinstance(check.specification, str):
            check_specification = yaml.safe_load(check.specification)
        else:
            check_specification = check.specification
        match check.type:
            case "SodaCL":
                result = result.combine(self.lint_sodacl(check_specification, models))
            case "montecarlo":
                result = result.combine(self.lint_montecarlo(check_specification, models))
            case "great-expectations":
                result = result.combine(self.lint_great_expectations(check_specification, models))
            case _:
                result = result.with_warning("Can't lint quality check " f"with type '{check.type}'")
        return result
