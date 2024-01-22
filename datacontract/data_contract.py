import json
import logging
import os
import sys
from datetime import datetime, timezone

from datacontract.engines.datacontract.check_that_datacontract_contains_valid_servers_configuration import \
    check_that_datacontract_contains_valid_server_configuration
from datacontract.engines.datacontract.check_that_datacontract_file_exists import \
    check_that_datacontract_file_exists
from datacontract.engines.datacontract.check_that_datacontract_str_is_valid import \
    check_that_datacontract_str_is_valid
from datacontract.engines.fastjsonschema.check_jsonschema import \
    check_jsonschema
from datacontract.engines.soda.check_soda_execute import check_soda_execute
from datacontract.export.jsonschema_converter import to_jsonschema
from datacontract.export.sodacl_converter import to_sodacl
from datacontract.integration.fetch_resource import fetch_resource
from datacontract.integration.publish_datamesh_manager import \
    publish_datamesh_manager
from datacontract.model.data_contract_specification import \
    DataContractSpecification
from datacontract.model.run import \
    Run, Check
from datacontract.model.run_failed_exception import RunFailedException


class DataContract:
    def __init__(
        self,
        data_contract_file: str = None,
        data_contract_str: str = None,
        data_contract: DataContractSpecification = None,
        publish: bool = False,
    ):
        self.data_contract_file = data_contract_file
        self.data_contract_str = data_contract_str
        self.data_contract = data_contract
        self.publish = publish
        self.run = Run.create_run()

    def lint(self):
        try:
            self.run.log_info("Linting data contract")
            if self.data_contract_file is not None:
                check_that_datacontract_file_exists(self.run, self.data_contract_file)
                self.data_contract_str = self.read_file(self.data_contract_file)
            check_that_datacontract_str_is_valid(self.run, self.data_contract_str)
            self.data_contract = DataContractSpecification.from_string(self.data_contract_str)
            self._update_run()
        except Exception as e:
            self.run.checks.append(Check(
                type="general",
                result="error",
                name="Check Data Contract",
                reason=str(e),
                engine="datacontract",
            ))
            self.run.log_error(str(e))
            self._update_run()
            pass
        return self.run

    def test(self) -> Run:
        try:
            self.run.log_info(f"Testing data contract")
            # 1. check yaml file exists and is valid
            self.lint()
            if not self.run.has_passed():
                return self.run

            # 3. check yaml contains models
            # 4. check yaml contains server
            check_that_datacontract_contains_valid_server_configuration(self.run, self.data_contract)

            # TODO
            server_name = list(self.data_contract.servers.keys())[0]
            server = self.data_contract.servers.get(server_name)
            self.run.dataProductId = server.dataProductId
            self.run.outputPortId = server.outputPortId
            self.run.server = server_name

            # 5. check server is supported type
            # 6. check server credentials are complete
            # 7. check soda-core can connect to type
            if server.format == "json":
                check_jsonschema(self.run, self.data_contract, server)
            check_soda_execute(self.run, self.data_contract, server)
            self._update_run()
            if self.publish:
                publish_datamesh_manager(self.run)
        except RunFailedException as e:
            self.run.checks.append(Check(
                type=e.type,
                result=e.result,
                name=e.name,
                reason=e.reason,
                engine=e.engine,
                details=""
            ))
            self.run.log_error(str(e))
            self._update_run()
            pass
        except Exception as e:
            self.run.checks.append(Check(
                type="general",
                result="error",
                name="Check Data Contract",
                reason=str(e),
                engine="datacontract",
            ))
            logging.exception("Exception occurred")
            self.run.log_error(str(e))
            self._update_run()
            pass

        return self.run

    def export(self, format) -> str:
        self.lint()
        if format == "jsonschema":
            model_name, model = next(iter(self.data_contract.models.items()))
            jsonschema_dict = to_jsonschema(model_name, model)
            return json.dumps(jsonschema_dict, indent=2)
        if format == "sodacl":
            return to_sodacl(self.data_contract)
        else:
            print(f"Format {format} not supported.")
            return ""

    def _update_run(self):
        if self.data_contract is None:
            return
        self.run.timestampEnd = datetime.now(timezone.utc)
        self.run.dataContractId = self.data_contract.id
        self.run.dataContractVersion = self.data_contract.info.version
        self.run.calculate_result()

    def read_file(self, data_contract_file):
        self.run.log_info(f"Reading data contract {data_contract_file}")
        if data_contract_file.startswith("http://") or data_contract_file.startswith("https://"):
            return fetch_resource(data_contract_file)

        if not os.path.exists(data_contract_file):
            print(f"The file '{data_contract_file}' does not exist.")
            sys.exit(1)
        with open(data_contract_file, 'r') as file:
            file_content = file.read()
        return file_content

