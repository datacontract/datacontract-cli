import importlib
import sys

from datacontract.export.exporter import Exporter, ExportFormat


class ExporterFactory:
    def __init__(self):
        self.dict_exporter = {}
        self.dict_lazy_exporter = {}

    def register_exporter(self, name: str, exporter: Exporter):
        self.dict_exporter.update({name: exporter})

    def register_lazy_exporter(self, name: str, module_path: str, class_name: str):
        self.dict_lazy_exporter.update({name: (module_path, class_name)})

    def create(self, name) -> Exporter:
        exporters = self.dict_exporter.copy()
        exporters.update(self.dict_lazy_exporter.copy())
        if name not in exporters.keys():
            raise ValueError(f"The '{name}' format is not supported.")
        exporter_class = exporters[name]
        if type(exporters[name]) is tuple:
            exporter_class = load_module_class(module_path=exporters[name][0], class_name=exporters[name][1])
        if not exporter_class:
            raise ValueError(f"Module {name} could not be loaded.")
        return exporter_class(name)


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


exporter_factory = ExporterFactory()

exporter_factory.register_lazy_exporter(
    name=ExportFormat.avro,
    module_path="datacontract.export.avro_converter",
    class_name="AvroExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.avro_idl,
    module_path="datacontract.export.avro_idl_converter",
    class_name="AvroIdlExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.bigquery,
    module_path="datacontract.export.bigquery_converter",
    class_name="BigQueryExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.data_caterer,
    module_path="datacontract.export.data_caterer_converter",
    class_name="DataCatererExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.dbml,
    module_path="datacontract.export.dbml_converter",
    class_name="DbmlExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.rdf,
    module_path="datacontract.export.rdf_converter",
    class_name="RdfExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.dbt,
    module_path="datacontract.export.dbt_converter",
    class_name="DbtExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.dbt_sources,
    module_path="datacontract.export.dbt_converter",
    class_name="DbtSourceExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.dbt_staging_sql,
    module_path="datacontract.export.dbt_converter",
    class_name="DbtStageExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.jsonschema,
    module_path="datacontract.export.jsonschema_converter",
    class_name="JsonSchemaExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.odcs_v2,
    module_path="datacontract.export.odcs_v2_exporter",
    class_name="OdcsV2Exporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.odcs_v3,
    module_path="datacontract.export.odcs_v3_exporter",
    class_name="OdcsV3Exporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.odcs,
    module_path="datacontract.export.odcs_v3_exporter",
    class_name="OdcsV3Exporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.go,
    module_path="datacontract.export.go_converter",
    class_name="GoExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.great_expectations,
    module_path="datacontract.export.great_expectations_converter",
    class_name="GreatExpectationsExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.html,
    module_path="datacontract.export.html_export",
    class_name="HtmlExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.protobuf,
    module_path="datacontract.export.protobuf_converter",
    class_name="ProtoBufExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.pydantic_model,
    module_path="datacontract.export.pydantic_converter",
    class_name="PydanticExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.sodacl,
    module_path="datacontract.export.sodacl_converter",
    class_name="SodaExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.sql,
    module_path="datacontract.export.sql_converter",
    class_name="SqlExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.sql_query,
    module_path="datacontract.export.sql_converter",
    class_name="SqlQueryExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.terraform,
    module_path="datacontract.export.terraform_converter",
    class_name="TerraformExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.spark,
    module_path="datacontract.export.spark_converter",
    class_name="SparkExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.sqlalchemy,
    module_path="datacontract.export.sqlalchemy_converter",
    class_name="SQLAlchemyExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.dcs,
    module_path="datacontract.export.dcs_exporter",
    class_name="DcsExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.markdown,
    module_path="datacontract.export.markdown_converter",
    class_name="MarkdownExporter",
)

exporter_factory.register_lazy_exporter(
    name=ExportFormat.iceberg, module_path="datacontract.export.iceberg_converter", class_name="IcebergExporter"
)
