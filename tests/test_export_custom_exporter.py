from datacontract.data_contract import DataContract
from datacontract.export.exporter import Exporter
from datacontract.export.exporter_factory import exporter_factory

# logging.basicConfig(level=logging.DEBUG, force=True)


class CustomExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        result = {
            "data_contract_servers": data_contract.servers,
            "model": model,
            "server": server,
            "sql_server_type": sql_server_type,
            "export_args": export_args,
            "custom_args": export_args.get("custom_arg", ""),
        }
        return str(result)


exporter_factory.register_exporter("custom", CustomExporter)


def test_custom_exporter():
    expected_custom = """{'data_contract_servers': {'production': Server(type='snowflake', description=None, environment=None, format=None, project=None, dataset=None, path=None, delimiter=None, endpointUrl=None, location=None, account='my-account', database='my-database', schema_='my-schema', host=None, port=None, catalog=None, topic=None, http_path=None, token=None, dataProductId=None, outputPortId=None, driver=None)}, 'model': 'orders', 'server': 'production', 'sql_server_type': 'auto', 'export_args': {'server': 'production', 'custom_arg': 'my_custom_arg'}, 'custom_args': 'my_custom_arg'}"""
    result = DataContract(data_contract_file="./fixtures/export/datacontract.yaml", server="production").export(
        export_format="custom", model="orders", server="production", custom_arg="my_custom_arg"
    )
    # TODO use json comparison instead of string comparison
    assert result.strip() == expected_custom.strip()
