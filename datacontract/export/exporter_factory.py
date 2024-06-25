import importlib
import sys
from datacontract.export.exporter import ExportFormat, Exporter


class ExporterFactory:
    def __init__(self):
        self.dict_exporter = {}

    def register_exporter(self, name, exporter):
        self.dict_exporter.update({name: exporter})

    def create(self, name) -> Exporter:
        if name not in self.dict_exporter.keys():
            raise ValueError(f"Export format {name} not supported.")
        return self.dict_exporter[name](name)


def lazy_module_import(module_path):
    spec = importlib.util.find_spec(module_path)
    if spec is not None:
        loader = importlib.util.LazyLoader(spec.loader)
        spec.loader = loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_path] = module
        loader.exec_module(module)
        return module


def load_exporter(import_format, module_path, class_name):
    module = lazy_module_import(module_path)
    if module:
        exporter_class = getattr(module, class_name)
        exporter_factory.register_exporter(import_format, exporter_class)


exporter_factory = ExporterFactory()

load_exporter(
    import_format=ExportFormat.avro, module_path="datacontract.export.avro_converter", class_name="AvroExporter"
)

load_exporter(
    import_format=ExportFormat.avro_idl,
    module_path="datacontract.export.avro_idl_converter",
    class_name="AvroIdlExporter",
)
load_exporter(
    import_format=ExportFormat.bigquery,
    module_path="datacontract.export.bigquery_converter",
    class_name="BigQueryExporter",
)
load_exporter(
    import_format=ExportFormat.dbml, module_path="datacontract.export.dbml_converter", class_name="DbmlExporter"
)
load_exporter(import_format=ExportFormat.rdf, module_path="datacontract.export.rdf_converter", class_name="RdfExporter")
load_exporter(import_format=ExportFormat.dbt, module_path="datacontract.export.dbt_converter", class_name="DbtExporter")
load_exporter(
    import_format=ExportFormat.dbt_sources,
    module_path="datacontract.export.dbt_converter",
    class_name="DbtSourceExporter",
)


load_exporter(
    import_format=ExportFormat.dbt_staging_sql,
    module_path="datacontract.export.dbt_converter",
    class_name="DbtStageExporter",
)


load_exporter(
    import_format=ExportFormat.jsonschema,
    module_path="datacontract.export.jsonschema_converter",
    class_name="JsonSchemaExporter",
)

load_exporter(
    import_format=ExportFormat.odcs, module_path="datacontract.export.odcs_converter", class_name="OdcsExporter"
)

load_exporter(import_format=ExportFormat.go, module_path="datacontract.export.go_converter", class_name="GoExporter")

load_exporter(
    import_format=ExportFormat.great_expectations,
    module_path="datacontract.export.great_expectations_converter",
    class_name="GreateExpectationsExporter",
)

load_exporter(import_format=ExportFormat.html, module_path="datacontract.export.html_export", class_name="HtmlExporter")

load_exporter(
    import_format=ExportFormat.protobuf,
    module_path="datacontract.export.protobuf_converter",
    class_name="ProtoBufExporter",
)

load_exporter(
    import_format=ExportFormat.pydantic_model,
    module_path="datacontract.export.pydantic_converter",
    class_name="PydanticExporter",
)

load_exporter(
    import_format=ExportFormat.sodacl, module_path="datacontract.export.sodacl_converter", class_name="SodaExporter"
)

load_exporter(import_format=ExportFormat.sql, module_path="datacontract.export.sql_converter", class_name="SqlExporter")

load_exporter(
    import_format=ExportFormat.sql_query, module_path="datacontract.export.sql_converter", class_name="SqlQueryExporter"
)


load_exporter(
    import_format=ExportFormat.terraform,
    module_path="datacontract.export.terraform_converter",
    class_name="TerraformExporter",
)

load_exporter(
    import_format=ExportFormat.spark, module_path="datacontract.export.spark_converter", class_name="SparkExporter"
)
