from datacontract.export.exporter import Exporter


class DcsExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        return data_contract.to_yaml()
