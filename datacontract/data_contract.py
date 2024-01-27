import json
import logging

from datacontract.engines.datacontract.check_that_datacontract_contains_valid_servers_configuration import \
    check_that_datacontract_contains_valid_server_configuration
from datacontract.engines.fastjsonschema.check_jsonschema import \
    check_jsonschema
from datacontract.engines.soda.check_soda_execute import check_soda_execute
from datacontract.export.jsonschema_converter import to_jsonschema
from datacontract.export.sodacl_converter import to_sodacl
from datacontract.integration.publish_datamesh_manager import \
    publish_datamesh_manager
from datacontract.lint import resolve
from datacontract.model.data_contract_specification import \
    DataContractSpecification
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import \
    Run, Check


class DataContract:
    def __init__(
        self,
        data_contract_file: str = None,
        data_contract_str: str = None,
        data_contract: DataContractSpecification = None,
        server: str = None,
        publish_url: str = None,
    ):
        self._data_contract_file = data_contract_file
        self._data_contract_str = data_contract_str
        self._data_contract = data_contract
        self._server = server
        self._publish_url = publish_url

    def lint(self):
        run = Run.create_run()
        try:
            run.log_info("Linting data contract")
            data_contract = resolve.resolve_data_contract(self._data_contract_file, self._data_contract_str,
                                                          self._data_contract)
            run.dataContractId = data_contract.id
            run.dataContractVersion = data_contract.info.version
            run.checks.append(Check(
                type="lint",
                result="passed",
                name="Check Data Contract",
                engine="datacontract",
            ))
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
                                                          self._data_contract)

            check_that_datacontract_contains_valid_server_configuration(run, data_contract, self._server)
            # TODO check yaml contains models
            server_name = list(data_contract.servers.keys())[0]
            server = data_contract.servers.get(server_name)
            run.dataProductId = server.dataProductId
            run.outputPortId = server.outputPortId
            run.server = server_name

            # 5. check server is supported type
            # 6. check server credentials are complete
            if server.format == "json":
                check_jsonschema(run, data_contract, server)
            check_soda_execute(run, data_contract, server)

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
        else:
            print(f"Export format {export_format} not supported.")
            return ""
