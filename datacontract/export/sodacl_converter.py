import yaml

from datacontract.engines.data_contract_checks import create_checks
from datacontract.export.exporter import Exporter
from datacontract.model.data_contract_specification import DataContractSpecification, Server
from datacontract.model.run import Run


class SodaExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> str:
        run = Run.create_run()
        server = get_server(data_contract, server)
        run.checks.extend(create_checks(data_contract, server))
        return to_sodacl_yaml(run)


def to_sodacl_yaml(run: Run) -> str:
    sodacl_dict = {}
    for run_check in run.checks:
        if run_check.engine != "soda" or run_check.language != "sodacl":
            continue
        check_yaml_str = run_check.implementation
        check_yaml_dict = yaml.safe_load(check_yaml_str)
        for key, value in check_yaml_dict.items():
            if key in sodacl_dict:
                if isinstance(sodacl_dict[key], list) and isinstance(value, list):
                    sodacl_dict[key].extend(value)
                else:
                    sodacl_dict[key].update(value)
            else:
                sodacl_dict[key] = value
    return yaml.dump(sodacl_dict)


def get_server(data_contract_specification: DataContractSpecification, server_name: str = None) -> Server | None:
    if server_name is None:
        return None
    return data_contract_specification.servers.get(server_name)
