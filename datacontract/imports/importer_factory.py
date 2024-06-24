import importlib.util
from datacontract.imports.importer import ImportFormat, Importer


class ImporterFactory:
    def __init__(self):
        self.dict_importer = {}

    def register_importer(self, name, exporter):
        self.dict_importer.update({name: exporter})

    def create(self, name) -> Importer:
        if name not in self.dict_importer.keys():
            raise ValueError(f"Import format {name} not supported.")
        return self.dict_importer[name](name)


importer_factory = ImporterFactory()

if importlib.util.find_spec("datacontract.imports.avro_importer"):
    from datacontract.imports.avro_importer import AvroImporter

    importer_factory.register_importer(ImportFormat.avro, AvroImporter)

if importlib.util.find_spec("datacontract.imports.bigquery_importer"):
    from datacontract.imports.bigquery_importer import BigQueryImporter

    importer_factory.register_importer(ImportFormat.bigquery, BigQueryImporter)

if importlib.util.find_spec("datacontract.imports.glue_importer"):
    from datacontract.imports.glue_importer import GlueImporter

    importer_factory.register_importer(ImportFormat.glue, GlueImporter)

if importlib.util.find_spec("datacontract.imports.jsonschema_importer"):
    from datacontract.imports.jsonschema_importer import JsonSchemaImporter

    importer_factory.register_importer(ImportFormat.jsonschema, JsonSchemaImporter)

if importlib.util.find_spec("datacontract.imports.odcs_importer"):
    from datacontract.imports.odcs_importer import OdcsImporter

    importer_factory.register_importer(ImportFormat.odcs, OdcsImporter)


if importlib.util.find_spec("datacontract.imports.sql_importer"):
    from datacontract.imports.sql_importer import SqlImporter

    importer_factory.register_importer(ImportFormat.sql, SqlImporter)


if importlib.util.find_spec("datacontract.imports.sql_importer"):
    from datacontract.imports.unity_importer import UnityImporter

    importer_factory.register_importer(ImportFormat.unity, UnityImporter)
