from datacontract.imports.avro_importer import AvroImporter
from datacontract.imports.bigquery_importer import BigQueryImporter
from datacontract.imports.glue_importer import GlueImporter
from datacontract.imports.importer import ImportFormat, Importer
from datacontract.imports.jsonschema_importer import JsonSchemaImporter
from datacontract.imports.odcs_importer import OdcsImporter
from datacontract.imports.sql_importer import SqlImporter
from datacontract.imports.unity_importer import UnityImporter


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
importer_factory.register_importer(ImportFormat.avro, AvroImporter)
importer_factory.register_importer(ImportFormat.bigquery, BigQueryImporter)
importer_factory.register_importer(ImportFormat.glue, GlueImporter)
importer_factory.register_importer(ImportFormat.jsonschema, JsonSchemaImporter)
importer_factory.register_importer(ImportFormat.odcs, OdcsImporter)
importer_factory.register_importer(ImportFormat.sql, SqlImporter)
importer_factory.register_importer(ImportFormat.unity, UnityImporter)
