import json
import logging
import os
import threading
from typing import List, Optional

import fastjsonschema
from fastjsonschema import JsonSchemaValueException

from datacontract.engines.fastjsonschema.s3.s3_read_files import yield_s3_files
from datacontract.export.jsonschema_converter import to_jsonschema
from datacontract.model.data_contract_specification import DataContractSpecification, Server
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Check, ResultEnum, Run

# Thread-safe cache for primaryKey fields.
_primary_key_cache = {}
_cache_lock = threading.Lock()


def get_primary_key_field(schema: dict, model_name: str) -> Optional[str]:
    # Check cache first.
    with _cache_lock:
        cached_value = _primary_key_cache.get(model_name)
        if cached_value is not None:
            return cached_value

    # Find primaryKey field.
    fields = schema.get("properties", {})
    for field_name, attributes in fields.items():
        if attributes.get("primaryKey", False):
            # Cache the result before returning.
            with _cache_lock:
                _primary_key_cache[model_name] = field_name
            return field_name

    # Return None if no primary key was found.
    return None


def get_primary_key_value(schema: dict, model_name: str, json_object: dict) -> Optional[str]:
    # Get the `primaryKey` field.
    primary_key_field = get_primary_key_field(schema, model_name)
    if not primary_key_field:
        return None

    # Return the value of the `primaryKey` field in the JSON object.
    return json_object.get(primary_key_field)


def process_exceptions(run, exceptions: List[DataContractException]):
    if not exceptions:
        return

    # Define the maximum number of errors to process (can be adjusted by defining an ENV variable).
    try:
        error_limit = int(os.getenv("DATACONTRACT_MAX_ERRORS", 500))
    except ValueError:
        # Fallback to default if environment variable is invalid.
        error_limit = 500

    # Calculate the effective limit to avoid index out of range
    limit = min(len(exceptions), error_limit)

    # Add all exceptions up to the limit - 1 to `run.checks`.
    DEFAULT_ERROR_MESSAGE = "An error occurred during validation phase. See the logs for more details."
    run.checks.extend(
        [
            Check(
                type=exception.type,
                name=exception.name,
                result=exception.result,
                reason=exception.reason,
                model=exception.model,
                engine=exception.engine,
                message=exception.message or DEFAULT_ERROR_MESSAGE,
            )
            for exception in exceptions[: limit - 1]
        ]
    )

    # Raise the last exception within the limit.
    last_exception = exceptions[limit - 1]
    raise last_exception


def validate_json_stream(
    schema: dict, model_name: str, validate: callable, json_stream: list[dict]
) -> List[DataContractException]:
    logging.info(f"Validating JSON stream for model: '{model_name}'.")
    exceptions: List[DataContractException] = []
    for json_obj in json_stream:
        try:
            validate(json_obj)
        except JsonSchemaValueException as e:
            logging.warning(f"Validation failed for JSON object with type: '{model_name}'.")
            primary_key_value = get_primary_key_value(schema, model_name, json_obj)
            exceptions.append(
                DataContractException(
                    type="schema",
                    name="Check that JSON has valid schema",
                    result="failed",
                    reason=f"{f'#{primary_key_value}: ' if primary_key_value is not None else ''}{e.message}",
                    model=model_name,
                    engine="jsonschema",
                    message=e.message,
                )
            )
    if not exceptions:
        logging.info(f"All JSON objects in the stream passed validation for model: '{model_name}'.")
    return exceptions


def read_json_lines(file):
    file_content = file.read()
    for line in file_content.splitlines():
        yield json.loads(line)


def read_json_lines_content(file_content: str):
    for line in file_content.splitlines():
        yield json.loads(line)


def read_json_array(file):
    data = json.load(file)
    for item in data:
        yield item


def read_json_array_content(file_content: str):
    data = json.loads(file_content)
    for item in data:
        yield item


def read_json_file(file):
    yield json.load(file)


def read_json_file_content(file_content: str):
    yield json.loads(file_content)


def process_json_file(run, schema, model_name, validate, file, delimiter):
    if delimiter == "new_line":
        json_stream = read_json_lines(file)
    elif delimiter == "array":
        json_stream = read_json_array(file)
    else:
        json_stream = read_json_file(file)

    # Validate the JSON stream and collect exceptions.
    exceptions = validate_json_stream(schema, model_name, validate, json_stream)

    # Handle all errors from schema validation.
    process_exceptions(run, exceptions)


def process_local_file(run, server, schema, model_name, validate):
    path = server.path
    if "{model}" in path:
        path = path.format(model=model_name)

    if os.path.isdir(path):
        return process_directory(run, path, server, model_name, validate)
    else:
        logging.info(f"Processing file {path}")
        with open(path, "r") as file:
            process_json_file(run, schema, model_name, validate, file, server.delimiter)


def process_directory(run, path, server, model_name, validate):
    success = True
    for filename in os.listdir(path):
        if filename.endswith(".json"):  # or make this a parameter
            file_path = os.path.join(path, filename)
            with open(file_path, "r") as file:
                if not process_json_file(run, model_name, validate, file, server.delimiter):
                    success = False
                    break
    return success


def process_s3_file(run, server, schema, model_name, validate):
    s3_endpoint_url = server.endpointUrl
    s3_location = server.location
    if "{model}" in s3_location:
        s3_location = s3_location.format(model=model_name)
    json_stream = None

    for file_content in yield_s3_files(s3_endpoint_url, s3_location):
        if server.delimiter == "new_line":
            json_stream = read_json_lines_content(file_content)
        elif server.delimiter == "array":
            json_stream = read_json_array_content(file_content)
        else:
            json_stream = read_json_file_content(file_content)

    if json_stream is None:
        raise DataContractException(
            type="schema",
            name="Check that JSON has valid schema",
            result="warning",
            reason=f"Cannot find any file in {s3_location}",
            engine="datacontract",
        )

    # Validate the JSON stream and collect exceptions.
    exceptions = validate_json_stream(schema, model_name, validate, json_stream)

    # Handle all errors from schema validation.
    process_exceptions(run, exceptions)


def check_jsonschema(run: Run, data_contract: DataContractSpecification, server: Server):
    run.log_info("Running engine jsonschema")

    # Early exit conditions
    if server.format != "json":
        run.checks.append(
            Check(
                type="schema",
                name="Check that JSON has valid schema",
                result="warning",
                reason="Server format is not 'json'. Skip validating jsonschema.",
                engine="jsonschema",
            )
        )
        run.log_warn("jsonschema: Server format is not 'json'. Skip jsonschema checks.")
        return

    if not data_contract.models:
        run.log_warn("jsonschema: No models found. Skip jsonschema checks.")
        return

    for model_name, model in iter(data_contract.models.items()):
        # Process the model
        run.log_info(f"jsonschema: Converting model {model_name} to JSON Schema")
        schema = to_jsonschema(model_name, model)
        run.log_info(f"jsonschema: {schema}")

        validate = fastjsonschema.compile(
            schema,
            formats={"uuid": r"^[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}$"},
        )

        # Process files based on server type
        if server.type == "local":
            process_local_file(run, server, schema, model_name, validate)
        elif server.type == "s3":
            process_s3_file(run, server, schema, model_name, validate)
        elif server.type == "gcs":
            run.checks.append(
                Check(
                    type="schema",
                    name="Check that JSON has valid schema",
                    model=model_name,
                    result=ResultEnum.info,
                    reason="JSON Schema check skipped for GCS, as GCS is currently not supported",
                    engine="jsonschema",
                )
            )
        elif server.type == "azure":
            run.checks.append(
                Check(
                    type="schema",
                    name="Check that JSON has valid schema",
                    model=model_name,
                    result=ResultEnum.info,
                    reason="JSON Schema check skipped for azure, as azure is currently not supported",
                    engine="jsonschema",
                )
            )
        else:
            run.checks.append(
                Check(
                    type="schema",
                    name="Check that JSON has valid schema",
                    model=model_name,
                    result=ResultEnum.warning,
                    reason=f"Server type {server.type} not supported",
                    engine="jsonschema",
                )
            )
            return

        run.checks.append(
            Check(
                type="schema",
                name="Check that JSON has valid schema",
                model=model_name,
                result=ResultEnum.passed,
                reason="All JSON entries are valid.",
                engine="jsonschema",
            )
        )
