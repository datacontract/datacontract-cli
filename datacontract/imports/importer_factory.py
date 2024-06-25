import importlib.util
import sys
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


def lazy_module_import(module_path):
    spec = importlib.util.find_spec(module_path)
    if spec is not None:
        loader = importlib.util.LazyLoader(spec.loader)
        spec.loader = loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_path] = module
        loader.exec_module(module)
        return module


def load_importer(import_format, module_path, class_name):
    module = lazy_module_import(module_path)
    if module:
        importer_class = getattr(module, class_name)
        importer_factory.register_importer(import_format, importer_class)


importer_factory = ImporterFactory()

load_importer(
    import_format=ImportFormat.avro, module_path="datacontract.imports.avro_importer", class_name="AvroImporter"
)
load_importer(
    import_format=ImportFormat.bigquery,
    module_path="datacontract.imports.bigquery_importer",
    class_name="BigQueryImporter",
)
load_importer(
    import_format=ImportFormat.glue, module_path="datacontract.imports.glue_importer", class_name="GlueImporter"
)
load_importer(
    import_format=ImportFormat.jsonschema,
    module_path="datacontract.imports.jsonschema_importer",
    class_name="JsonSchemaImporter",
)
load_importer(
    import_format=ImportFormat.odcs, module_path="datacontract.imports.odcs_importer", class_name="OdcsImporter"
)
load_importer(import_format=ImportFormat.sql, module_path="datacontract.imports.sql_importer", class_name="SqlImporter")
load_importer(
    import_format=ImportFormat.unity, module_path="datacontract.imports.unity_importer", class_name="UnityImporter"
)
