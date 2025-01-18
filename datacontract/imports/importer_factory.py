import importlib.util
import sys

from datacontract.imports.importer import Importer, ImportFormat


class ImporterFactory:
    def __init__(self):
        self.dict_importer = {}
        self.dict_lazy_importer = {}

    def register_importer(self, name, importer: Importer):
        self.dict_importer.update({name: importer})

    def register_lazy_importer(self, name: str, module_path: str, class_name: str):
        self.dict_lazy_importer.update({name: (module_path, class_name)})

    def create(self, name) -> Importer:
        importers = self.dict_importer.copy()
        importers.update(self.dict_lazy_importer.copy())
        if name not in importers.keys():
            raise ValueError(f"The '{name}' format is not supported.")
        importer_class = importers[name]
        if type(importers[name]) is tuple:
            importer_class = load_module_class(module_path=importers[name][0], class_name=importers[name][1])
        if not importer_class:
            raise ValueError(f"Module {name} could not be loaded.")
        return importer_class(name)


def import_module(module_path):
    if importlib.util.find_spec(module_path) is not None:
        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError:
            return None
        sys.modules[module_path] = module
        return module


def load_module_class(module_path, class_name):
    module = import_module(module_path)
    if not module:
        return None
    return getattr(module, class_name)


importer_factory = ImporterFactory()
importer_factory.register_lazy_importer(
    name=ImportFormat.avro,
    module_path="datacontract.imports.avro_importer",
    class_name="AvroImporter",
)
importer_factory.register_lazy_importer(
    name=ImportFormat.bigquery,
    module_path="datacontract.imports.bigquery_importer",
    class_name="BigQueryImporter",
)
importer_factory.register_lazy_importer(
    name=ImportFormat.glue,
    module_path="datacontract.imports.glue_importer",
    class_name="GlueImporter",
)
importer_factory.register_lazy_importer(
    name=ImportFormat.jsonschema,
    module_path="datacontract.imports.jsonschema_importer",
    class_name="JsonSchemaImporter",
)
importer_factory.register_lazy_importer(
    name=ImportFormat.odcs,
    module_path="datacontract.imports.odcs_importer",
    class_name="OdcsImporter",
)
importer_factory.register_lazy_importer(
    name=ImportFormat.sql,
    module_path="datacontract.imports.sql_importer",
    class_name="SqlImporter",
)
importer_factory.register_lazy_importer(
    name=ImportFormat.unity,
    module_path="datacontract.imports.unity_importer",
    class_name="UnityImporter",
)
importer_factory.register_lazy_importer(
    name=ImportFormat.spark,
    module_path="datacontract.imports.spark_importer",
    class_name="SparkImporter",
)
importer_factory.register_lazy_importer(
    name=ImportFormat.dbt, module_path="datacontract.imports.dbt_importer", class_name="DbtManifestImporter"
)
importer_factory.register_lazy_importer(
    name=ImportFormat.dbml,
    module_path="datacontract.imports.dbml_importer",
    class_name="DBMLImporter",
)
importer_factory.register_lazy_importer(
    name=ImportFormat.iceberg,
    module_path="datacontract.imports.iceberg_importer",
    class_name="IcebergImporter",
)
importer_factory.register_lazy_importer(
    name=ImportFormat.parquet,
    module_path="datacontract.imports.parquet_importer",
    class_name="ParquetImporter",
)
importer_factory.register_lazy_importer(
    name=ImportFormat.csv,
    module_path="datacontract.imports.csv_importer",
    class_name="CsvImporter",
)
