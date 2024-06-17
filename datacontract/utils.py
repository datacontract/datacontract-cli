import json
import logging
import typing

import yaml
from datacontract.model.data_contract_specification import DataContractSpecification, Server


def _determine_sql_server_type(data_contract: DataContractSpecification, sql_server_type: str, server: str = None):
    if sql_server_type == "auto":
        if data_contract.servers is None or len(data_contract.servers) == 0:
            raise RuntimeError("Export with server_type='auto' requires servers in the data contract.")

        if server is None:
            server_types = set([server.type for server in data_contract.servers.values()])
        else:
            server_types = {data_contract.servers[server].type}

        if "snowflake" in server_types:
            return "snowflake"
        elif "postgres" in server_types:
            return "postgres"
        elif "databricks" in server_types:
            return "databricks"
        else:
            # default to snowflake dialect
            return "snowflake"
    else:
        return sql_server_type


def _get_examples_server(data_contract, run, tmp_dir):
    run.log_info(f"Copying examples to files in temporary directory {tmp_dir}")
    format = "json"
    for example in data_contract.examples:
        format = example.type
        p = f"{tmp_dir}/{example.model}.{format}"
        run.log_info(f"Creating example file {p}")
        with open(p, "w") as f:
            content = ""
            if format == "json" and isinstance(example.data, list):
                content = json.dumps(example.data)
            elif format == "json" and isinstance(example.data, str):
                content = example.data
            elif format == "yaml" and isinstance(example.data, list):
                content = yaml.dump(example.data, allow_unicode=True)
            elif format == "yaml" and isinstance(example.data, str):
                content = example.data
            elif format == "csv":
                content = example.data
            logging.debug(f"Content of example file {p}: {content}")
            f.write(content)
    path = f"{tmp_dir}" + "/{model}." + format
    delimiter = "array"
    server = Server(
        type="local",
        path=path,
        format=format,
        delimiter=delimiter,
    )
    run.log_info(f"Using {server} for testing the examples")
    return server


def _check_models_for_export(
    data_contract: DataContractSpecification, model: str, export_format: str
) -> typing.Tuple[str, str]:
    if data_contract.models is None:
        raise RuntimeError(f"Export to {export_format} requires models in the data contract.")

    model_names = list(data_contract.models.keys())

    if model == "all":
        if len(data_contract.models.items()) != 1:
            raise RuntimeError(
                f"Export to {export_format} is model specific. Specify the model via --model $MODEL_NAME. Available models: {model_names}"
            )

        model_name, model_value = next(iter(data_contract.models.items()))
    else:
        model_name = model
        model_value = data_contract.models.get(model_name)
        if model_value is None:
            raise RuntimeError(f"Model {model_name} not found in the data contract. Available models: {model_names}")

    return model_name, model_value
