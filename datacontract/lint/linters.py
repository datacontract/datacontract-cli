from .result import LintingResult
"""This module contains linter definitions for linting a data contract.

Lints are quality checks that can succeed, fail, or warn. They are
distinct from checks such as "valid yaml" or "file not found", which
will cause the processing of the data contract to stop. Lints can be
ignored, and are high-level requirements on the format of a data
contract."""


def linter_example_schema(data_contract_yaml) -> LintingResult:
    """Check whether the example(s) match the model."""
    result = LintingResult("Example(s) match schema")
    examples = data_contract_yaml.examples
    models = data_contract_yaml.models
    for (index, example) in enumerate(examples):
        if example.model not in models:
            result = result.with_error(
                f"Example {index + 1} has non-existent model '{example.model}'")
    return result


def linter_quality_checks_uses_schema(
        data_contract_yaml) -> LintingResult:
    return LintingResult("Quality checks use schema names")


def linter_documentation_best_practices(
        data_contract_yaml) -> LintingResult:
    return LintingResult("Contract follows documentation best practices")


def lint_all(data_contract_yaml) -> list[LintingResult]:
    linters = [linter for (name, linter) in globals().items()
               if callable(linter) and name.startswith('linter')]
    all_results = []
    for linter in linters:
        all_results.append(linter(data_contract_yaml))
    return all_results
