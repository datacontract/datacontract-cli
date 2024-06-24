from datacontract.export.avro_idl_converter import AvroIdlExporter
from datacontract.export.bigquery_converter import BigQueryExporter
from datacontract.export.dbml_converter import DbmlExporter
from datacontract.export.dbt_converter import DbtExporter, DbtSourceExporter, DbtStageExporter
from datacontract.export.avro_converter import AvroExporter
from datacontract.export.exporter import ExportFormat, Exporter
from datacontract.export.go_converter import GoExporter
from datacontract.export.great_expectations_converter import GreateExpectationsExporter
from datacontract.export.html_export import HtmlExporter
from datacontract.export.jsonschema_converter import JsonSchemaExporter
from datacontract.export.odcs_converter import OdcsExporter
from datacontract.export.protobuf_converter import ProtoBufExporter
from datacontract.export.pydantic_converter import PydanticExporter
from datacontract.export.rdf_converter import RdfExporter
from datacontract.export.sodacl_converter import SodaExporter
from datacontract.export.spark_converter import SparkExporter
from datacontract.export.sql_converter import SqlExporter, SqlQueryExporter
from datacontract.export.terraform_converter import TerraformExporter


class ExporterFactory:
    def __init__(self):
        self.dict_exporter = {}

    def register_exporter(self, name, exporter):
        self.dict_exporter.update({name: exporter})

    def create(self, name) -> Exporter:
        if name not in self.dict_exporter.keys():
            raise ValueError(f"Export format {name} not supported.")
        return self.dict_exporter[name](name)


exporter_factory = ExporterFactory()
exporter_factory.register_exporter(ExportFormat.avro, AvroExporter)
exporter_factory.register_exporter(ExportFormat.avro_idl, AvroIdlExporter)
exporter_factory.register_exporter(ExportFormat.bigquery, BigQueryExporter)
exporter_factory.register_exporter(ExportFormat.dbml, DbmlExporter)
exporter_factory.register_exporter(ExportFormat.rdf, RdfExporter)
exporter_factory.register_exporter(ExportFormat.dbt, DbtExporter)
exporter_factory.register_exporter(ExportFormat.dbt_sources, DbtSourceExporter)
exporter_factory.register_exporter(ExportFormat.dbt_staging_sql, DbtStageExporter)
exporter_factory.register_exporter(ExportFormat.jsonschema, JsonSchemaExporter)
exporter_factory.register_exporter(ExportFormat.odcs, OdcsExporter)
exporter_factory.register_exporter(ExportFormat.go, GoExporter)
exporter_factory.register_exporter(ExportFormat.great_expectations, GreateExpectationsExporter)
exporter_factory.register_exporter(ExportFormat.html, HtmlExporter)
exporter_factory.register_exporter(ExportFormat.protobuf, ProtoBufExporter)
exporter_factory.register_exporter(ExportFormat.pydantic_model, PydanticExporter)
exporter_factory.register_exporter(ExportFormat.sodacl, SodaExporter)
exporter_factory.register_exporter(ExportFormat.sql, SqlExporter)
exporter_factory.register_exporter(ExportFormat.sql_query, SqlQueryExporter)
exporter_factory.register_exporter(ExportFormat.terraform, TerraformExporter)
exporter_factory.register_exporter(ExportFormat.spark, SparkExporter)
