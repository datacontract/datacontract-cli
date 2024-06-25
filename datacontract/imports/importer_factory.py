from datacontract.imports.importer import Importer


class ImporterFactory:
    def __init__(self):
        self.dict_importer = {}

    def create(self, name) -> Importer:
        if name == "avro":
            from datacontract.imports.avro_importer import AvroImporter

            return AvroImporter
        if name == "bigquery":
            from datacontract.imports.bigquery_importer import BigQueryImporter

            return BigQueryImporter
        if name == "glue":
            from datacontract.imports.glue_importer import GlueImporter

            return GlueImporter
        if name == "jsonschema":
            from datacontract.imports.jsonschema_importer import JsonSchemaImporter

            return JsonSchemaImporter
        if name == "odcs":
            from datacontract.imports.odcs_importer import OdcsImporter

            return OdcsImporter
        if name == "sql":
            from datacontract.imports.sql_importer import SqlImporter

            return SqlImporter
        if name == "unity":
            from datacontract.imports.unity_importer import UnityImporter

            return UnityImporter
        raise ValueError(f"Import format {name} not supported.")
