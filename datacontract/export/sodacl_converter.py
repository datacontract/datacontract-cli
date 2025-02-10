import yaml

from datacontract.engines.data_contract_checks import create_checks
from datacontract.export.exporter import Exporter
from datacontract.model.run import Run


class SodaExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        run = Run.create_run()
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
