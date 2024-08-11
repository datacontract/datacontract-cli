import json
import logging
import os

import fastjsonschema

from datacontract.engines.fastjsonschema.s3.s3_read_files import yield_s3_files
from datacontract.export.jsonschema_converter import to_jsonschema
from datacontract.model.data_contract_specification import DataContractSpecification, Server
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Run, Check


def validate_json_stream(model_name, validate, json_stream):
    try:
        logging.info("Validating JSON")
        for json_obj in json_stream:
            validate(json_obj)
        return True
    except fastjsonschema.JsonSchemaValueException as e:
        raise DataContractException(
            type="schema",
            name="Check that JSON has valid schema",
            model=model_name,
            reason=e.message,
            engine="jsonschema",
            original_exception=e,
        )


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


def process_json_file(run, model_name, validate, file, delimiter):
    if delimiter == "new_line":
        json_stream = read_json_lines(file)
    elif delimiter == "array":
        json_stream = read_json_array(file)
    else:
        json_stream = read_json_file(file)
    validate_json_stream(model_name, validate, json_stream)


def process_local_file(run, server, model_name, validate):
    path = server.path
    if "{model}" in path:
        path = path.format(model=model_name)

    if os.path.isdir(path):
        return process_directory(run, path, server, model_name, validate)
    else:
        logging.info(f"Processing file {path}")
        with open(path, "r") as file:
            process_json_file(run, model_name, validate, file, server.delimiter)


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


def process_s3_file(server, model_name, validate):
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

    return validate_json_stream(model_name, validate, json_stream)


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
            process_local_file(run, server, model_name, validate)
        elif server.type == "s3":
            process_s3_file(server, model_name, validate)
        elif server.type == "gcs":
            run.checks.append(
                Check(
                    type="schema",
                    name="Check that JSON has valid schema",
                    model=model_name,
                    result="info",
                    reason="JSON Schema check skipped for GCS, as GCS is currently not supported",
                    engine="jsonschema",
                )
            )
        else:
            run.checks.append(
                Check(
                    type="schema",
                    name="Check that JSON has valid schema",
                    model=model_name,
                    result="warn",
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
                result="passed",
                reason="All JSON entries are valid.",
                engine="jsonschema",
            )
        )
