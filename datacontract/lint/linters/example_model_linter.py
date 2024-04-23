import csv
import io
import json

import yaml

from datacontract.model.data_contract_specification import DataContractSpecification, Example
from ..lint import Linter, LinterResult


class ExampleModelLinter(Linter):
    @property
    def name(self) -> str:
        return "Example(s) match model"

    @property
    def id(self) -> str:
        return "example-model"

    @staticmethod
    def get_example_headers(example: Example) -> list[str]:
        if isinstance(example.data, str):
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
                case _:
                    # This is checked in lint_implementation, so shouldn't happen.
                    raise NotImplementedError(f"Unknown type {example.type}")
        else:
            # Checked in lint_implementation, shouldn't happen.
            raise NotImplementedError("Can't lint object examples.")

    def lint_implementation(self, contract: DataContractSpecification) -> LinterResult:
        """Check whether the example(s) headers match the model.

        This linter checks whether the example's fields match the model
        fields, and whether all required fields of the model are present in
        the example.
        """
        result = LinterResult()
        examples = contract.examples
        models = contract.models
        examples_with_model = []
        for index, example in enumerate(examples):
            if example.model not in models:
                result = result.with_error(f"Example {index + 1} has non-existent model '{example.model}'")
            else:
                examples_with_model.append((index, example, models.get(example.model)))
        for index, example, model in examples_with_model:
            if example.type == "custom":
                result = result.with_warning(
                    f"Example {index + 1} has type" ' "custom", cannot check model' " conformance"
                )
            elif not isinstance(example.data, str):
                result = result.with_warning(
                    f"Example {index + 1} is not a " "string example, can only lint string examples for now."
                )
            elif model.type == "object":
                result = result.with_warning(
                    f"Example {index + 1} uses a "
                    f"model '{example.model}' with type 'object'. Linting is "
                    "currently only supported for 'table' models"
                )
            else:
                if example.type in ("csv", "yaml", "json"):
                    headers = self.get_example_headers(example)
                    for example_header in headers:
                        if example_header not in model.fields:
                            result = result.with_error(
                                f"Example {index + 1} has field '{example_header}'"
                                f" that's not contained in model '{example.model}'"
                            )
                    for field_name, field_value in model.fields.items():
                        if field_name not in headers and field_value.required:
                            result = result.with_error(
                                f"Example {index + 1} is missing field '{field_name}'"
                                f" required by model '{example.model}'"
                            )
                else:
                    result = result.with_error(f"Example {index + 1} has unknown type" f"{example.type}")
        return result
