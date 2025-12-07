from datacontract.data_contract import DataContract
from datacontract.export.exporter import Exporter
from datacontract.export.exporter_factory import exporter_factory

# logging.basicConfig(level=logging.DEBUG, force=True)


class CustomExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> str:
        result = {
            "data_contract_servers": data_contract.servers,
            "schema_name": schema_name,
            "server": server,
            "sql_server_type": sql_server_type,
            "export_args": export_args,
            "custom_args": export_args.get("custom_arg", ""),
        }
        return str(result)


exporter_factory.register_exporter("custom_exporter", CustomExporter)


def test_custom_exporter():
    result = DataContract(data_contract_file="./fixtures/export/datacontract.odcs.yaml", server="production").export(
        export_format="custom_exporter", schema_name="orders", server="production", custom_arg="my_custom_arg"
    )
    # Verify result contains expected key components (Server model repr differs between DCS/ODCS)
    assert "'schema_name': 'orders'" in result
    assert "'server': 'production'" in result
    assert "'sql_server_type': 'auto'" in result
    assert "'custom_args': 'my_custom_arg'" in result
    assert "Server(" in result
    assert "server='production'" in result
    assert "type='snowflake'" in result
    assert "account='my-account'" in result
    assert "database='my-database'" in result
