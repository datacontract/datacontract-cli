import logging

import yaml
from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty, Server

from datacontract.export.exporter import Exporter
from datacontract.export.sodacl_check_builder import create_checks
from datacontract.model.run import Run

logger = logging.getLogger(__name__)


class SodaExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> str:
        run = Run.create_run()
        found_server = get_server(data_contract, server)
        run.checks.extend(create_checks(data_contract, found_server))
        nested = [
            path
            for schema_obj in data_contract.schema_ or []
            for prop in schema_obj.properties or []
            for path in _nested_paths(prop, f"{schema_obj.name}.{prop.name}")
        ]
        if nested:
            listed = ", ".join(nested) if len(nested) <= 6 else ", ".join(nested[:5]) + f" and {len(nested) - 5} others"
            logger.warning(f"SodaCL only checks top-level columns; nested properties not exported: {listed}")
        return to_sodacl_yaml(run)


def _nested_paths(prop: SchemaProperty, path: str):
    children = prop.properties or []
    if prop.items is not None:
        children, path = prop.items.properties or [], f"{path}[]"
    for child in children:
        child_path = f"{path}.{child.name}"
        yield child_path
        yield from _nested_paths(child, child_path)


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


def get_server(data_contract: OpenDataContractStandard, server_name: str = None) -> Server | None:
    if server_name is None or data_contract.servers is None:
        return None
    return next((s for s in data_contract.servers if s.server == server_name), None)
