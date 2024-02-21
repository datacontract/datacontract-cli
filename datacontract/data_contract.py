import json
import logging
import tempfile

import yaml

from datacontract.engines.datacontract.check_that_datacontract_contains_valid_servers_configuration import \
    check_that_datacontract_contains_valid_server_configuration
from datacontract.engines.fastjsonschema.check_jsonschema import \
    check_jsonschema
from datacontract.engines.soda.check_soda_execute import check_soda_execute
from datacontract.export.dbt_converter import to_dbt
from datacontract.export.jsonschema_converter import to_jsonschema
from datacontract.export.odcs_converter import to_odcs
from datacontract.export.sodacl_converter import to_sodacl
from datacontract.integration.publish_datamesh_manager import \
    publish_datamesh_manager
from datacontract.lint import resolve
from datacontract.lint.linters.example_model_linter import ExampleModelLinter
from datacontract.model.data_contract_specification import \
    DataContractSpecification, Server
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import \
    Run, Check


class DataContract:
    def __init__(
        self,
        data_contract_file: str = None,
        data_contract_str: str = None,
        data_contract: DataContractSpecification = None,
        schema_location: str = None,
        server: str = None,
        examples: bool = False,
        publish_url: str = None,
        spark: str = None,
    ):
        self._data_contract_file = data_contract_file
        self._data_contract_str = data_contract_str
        self._data_contract = data_contract
        self._schema_location = schema_location
        self._server = server
        self._examples = examples
        self._publish_url = publish_url
        self._spark = spark

    def lint(self):
        run = Run.create_run()
        try:
            run.log_info("Linting data contract")
            data_contract = resolve.resolve_data_contract(self._data_contract_file, self._data_contract_str,
                                                          self._data_contract, self._schema_location)
            run.checks.append(Check(
                type="lint",
                result="passed",
                name="Data contract is syntactically valid",
                engine="datacontract"
                ))
            run.checks.extend(ExampleModelLinter().lint(data_contract))
            run.dataContractId = data_contract.id
            run.dataContractVersion = data_contract.info.version
        except DataContractException as e:
            run.checks.append(Check(
                type=e.type,
                result=e.result,
                name=e.name,
                reason=e.reason,
                engine=e.engine,
                details=""
            ))
            run.log_error(str(e))
        except Exception as e:
            run.checks.append(Check(
                type="general",
                result="error",
                name="Check Data Contract",
                reason=str(e),
                engine="datacontract",
            ))
            run.log_error(str(e))
        run.finish()
        return run

    def test(self) -> Run:
        run = Run.create_run()
        try:
            run.log_info(f"Testing data contract")
            data_contract = resolve.resolve_data_contract(self._data_contract_file, self._data_contract_str,
                                                          self._data_contract, self._schema_location)

            check_that_datacontract_contains_valid_server_configuration(run, data_contract, self._server)
            # TODO check yaml contains models

            with tempfile.TemporaryDirectory(prefix="datacontract-cli") as tmp_dir:
                if self._examples:
                    server_name = "examples"
                    server = self._get_examples_server(data_contract, run, tmp_dir)
                else:
                    server_name = list(data_contract.servers.keys())[0]
                    server = data_contract.servers.get(server_name)

                run.log_info(f"Running tests for data contract {data_contract.id} with server {server_name}")
                run.dataContractId = data_contract.id
                run.dataContractVersion = data_contract.info.version
                run.dataProductId = server.dataProductId
                run.outputPortId = server.outputPortId
                run.server = server_name

                # 5. check server is supported type
                # 6. check server credentials are complete
                if server.format == "json":
                    check_jsonschema(run, data_contract, server)
                check_soda_execute(run, data_contract, server, self._spark)

        except DataContractException as e:
            run.checks.append(Check(
                type=e.type,
                result=e.result,
                name=e.name,
                reason=e.reason,
                engine=e.engine,
                details=""
            ))
            run.log_error(str(e))
        except Exception as e:
            run.checks.append(Check(
                type="general",
                result="error",
                name="Test Data Contract",
                reason=str(e),
                engine="datacontract",
            ))
            logging.exception("Exception occurred")
            run.log_error(str(e))

        run.finish()

        if self._publish_url is not None:
            publish_datamesh_manager(run, self._publish_url)

        return run


    def diff(self, other):
        pass

    def export(self, export_format) -> str:
        data_contract = resolve.resolve_data_contract(self._data_contract_file, self._data_contract_str,
                                                      self._data_contract)
        if export_format == "jsonschema":
            model_name, model = next(iter(data_contract.models.items()))
            jsonschema_dict = to_jsonschema(model_name, model)
            return json.dumps(jsonschema_dict, indent=2)
        if export_format == "sodacl":
            return to_sodacl(data_contract)
        if export_format == "dbt":
            return to_dbt(data_contract)
        if export_format == "odcs":
            return to_odcs(data_contract)
        else:
            print(f"Export format {export_format} not supported.")
            return ""

    def _get_examples_server(self, data_contract, run, tmp_dir):
        run.log_info(f"Copying examples to files in temporary directory {tmp_dir}")
        format = "json"
        for example in data_contract.examples:
            format = example.type
            p = f"{tmp_dir}/{example.model}.{format}"
            run.log_info(f"Creating example file {p}")
            with open(p, "w") as f:
                content = ""
                if format == "json" and type(example.data) is list:
                    content = json.dumps(example.data)
                elif format == "json" and type(example.data) is str:
                    content = example.data
                elif format == "yaml" and type(example.data) is list:
                    content = yaml.dump(example.data)
                elif format == "yaml" and type(example.data) is str:
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
