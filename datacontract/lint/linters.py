import csv
import yaml
import json
import io

from .result import LinterResult
from ..model.data_contract_specification import DataContractSpecification, Example

"""This module contains linter definitions for linting a data contract.

Lints are quality checks that can succeed, fail, or warn. They are
distinct from checks such as "valid yaml" or "file not found", which
will cause the processing of the data contract to stop. Lints can be
ignored, and are high-level requirements on the format of a data
contract."""


def get_example_headers(example: Example) -> list[str]:
    match example.type:
        case "csv":
            dialect = csv.Sniffer().sniff(example.data)
            data = io.StringIO(example.data)
            reader = csv.reader(data, dialect=dialect)
            return next(reader)
        case "yaml":
            data = yaml.safe_load(example.data)
            return data.keys()
        case "json":
            data = json.loads(example.data)
            return data.keys()


def linter_examples_conform_to_model(
    data_contract_yaml: DataContractSpecification
) -> LinterResult:
    """Check whether the example(s) match the model."""
    result = LinterResult("Example(s) match schema")
    examples = data_contract_yaml.examples
    models = data_contract_yaml.models
    examples_with_model = []
    for (index, example) in enumerate(examples):
        if example.model not in models:
            result = result.with_error(
                f"Example {index + 1} has non-existent model '{example.model}'")
        else:
            examples_with_model.append(
                (index, example, models.get(example.model)))
    for (index, example, model) in examples_with_model:
        if example.type == "custom":
            result = result.with_warning(f"Example {index + 1} has type"
                                         " \"custom\", cannot check model"
                                         " conformance")
        elif model.type == "object":
            result = result.with_warning(
                f"Example {index + 1} uses a "
                f"model '{example.model}' with type 'object'. Linting is "
                "currently only supported for 'table' models")
        else:
            headers = get_example_headers(example)
            for example_header in headers:
                if example_header not in model.fields:
                    result = result.with_error(
                        f"Example {index + 1} has field '{example_header}'"
                        f" that's not contained in model '{example.model}'")
            for (field_name, field_value) in model.fields.items():
                if field_name not in headers and field_value.required:
                    result = result.with_error(
                        f"Example {index + 1} is missing field '{field_name}'"
                        f" required by model '{example.model}'")
    return result


def lint_all(data_contract_yaml) -> list[LinterResult]:
    linters = [linter for (name, linter) in globals().items()
               if callable(linter) and name.startswith('linter')]
    all_results = []
    for linter in linters:
        all_results.append(linter(data_contract_yaml))
    return all_results
