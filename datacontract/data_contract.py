import json
import logging
import tempfile
import typing

import yaml
from pyspark.sql import SparkSession

from datacontract.breaking.breaking import models_breaking_changes, quality_breaking_changes
from datacontract.engines.datacontract.check_that_datacontract_contains_valid_servers_configuration import (
    check_that_datacontract_contains_valid_server_configuration,
)
from datacontract.engines.fastjsonschema.check_jsonschema import check_jsonschema
from datacontract.engines.soda.check_soda_execute import check_soda_execute
from datacontract.export.avro_converter import to_avro_schema_json
from datacontract.export.avro_idl_converter import to_avro_idl
from datacontract.export.bigquery_converter import to_bigquery_json
from datacontract.export.dbt_converter import to_dbt_models_yaml, \
    to_dbt_sources_yaml, to_dbt_staging_sql
from datacontract.export.great_expectations_converter import \
    to_great_expectations
from datacontract.export.html_export import to_html
from datacontract.export.jsonschema_converter import to_jsonschema_json
from datacontract.export.odcs_converter import to_odcs_yaml
from datacontract.export.protobuf_converter import to_protobuf
from datacontract.export.pydantic_converter import to_pydantic_model_str
from datacontract.export.go_converter import to_go_types
from datacontract.export.rdf_converter import to_rdf_n3
from datacontract.export.sodacl_converter import to_sodacl_yaml
from datacontract.export.sql_converter import to_sql_ddl, to_sql_query
from datacontract.export.terraform_converter import to_terraform
from datacontract.imports.avro_importer import import_avro
from datacontract.imports.bigquery_importer import import_bigquery_from_api, import_bigquery_from_json
from datacontract.imports.glue_importer import import_glue
from datacontract.imports.sql_importer import import_sql
from datacontract.imports.jsonschema_importer import import_jsonschema
from datacontract.integration.publish_datamesh_manager import \
    publish_datamesh_manager
from datacontract.integration.publish_opentelemetry import publish_opentelemetry
from datacontract.lint import resolve
from datacontract.lint.linters.description_linter import DescriptionLinter
from datacontract.lint.linters.example_model_linter import ExampleModelLinter
from datacontract.lint.linters.field_pattern_linter import FieldPatternLinter
from datacontract.lint.linters.field_reference_linter import FieldReferenceLinter
from datacontract.lint.linters.notice_period_linter import NoticePeriodLinter
from datacontract.lint.linters.quality_schema_linter import QualityUsesSchemaLinter
from datacontract.lint.linters.valid_constraints_linter import ValidFieldConstraintsLinter
from datacontract.model.breaking_change import BreakingChanges, BreakingChange, Severity
from datacontract.model.data_contract_specification import DataContractSpecification, Server
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Run, Check


class DataContract:
    def __init__(
        self,
        data_contract_file: str = None,
        data_contract_str: str = None,
        data_contract: DataContractSpecification = None,
        schema_location: str = None,
        server: str = None,
        examples: bool = False,
        publish_url: str = None,
        publish_to_opentelemetry: bool = False,
        spark: SparkSession = None,
        inline_definitions: bool = False,
        inline_quality: bool = False,
    ):
        self._data_contract_file = data_contract_file
        self._data_contract_str = data_contract_str
        self._data_contract = data_contract
        self._schema_location = schema_location
        self._server = server
        self._examples = examples
        self._publish_url = publish_url
        self._publish_to_opentelemetry = publish_to_opentelemetry
        self._spark = spark
        self._inline_definitions = inline_definitions
        self._inline_quality = inline_quality
        self.all_linters = {
            ExampleModelLinter(),
            QualityUsesSchemaLinter(),
            FieldPatternLinter(),
            FieldReferenceLinter(),
            NoticePeriodLinter(),
            ValidFieldConstraintsLinter(),
            DescriptionLinter(),
        }

    @classmethod
    def init(cls, template: str = "https://datacontract.com/datacontract.init.yaml") -> DataContractSpecification:
        return resolve.resolve_data_contract(data_contract_location=template)

    def lint(self, enabled_linters: typing.Union[str, set[str]] = "all") -> Run:
        """Lint the data contract by deserializing the contract and checking the schema, as well as calling the configured linters.

        enabled_linters can be either "all" or "none", or a set of linter IDs. The "schema" linter is always enabled, even with enabled_linters="none".
        """
        run = Run.create_run()
        try:
            run.log_info("Linting data contract")
            data_contract = resolve.resolve_data_contract(
                self._data_contract_file,
                self._data_contract_str,
                self._data_contract,
                self._schema_location,
                inline_definitions=True,
                inline_quality=True,
            )
            run.checks.append(
                Check(type="lint", result="passed", name="Data contract is syntactically valid", engine="datacontract")
            )
            if enabled_linters == "none":
                linters_to_check = set()
            elif enabled_linters == "all":
                linters_to_check = self.all_linters
            elif isinstance(enabled_linters, set):
                linters_to_check = {linter for linter in self.all_linters if linter.id in enabled_linters}
            else:
                raise RuntimeError(f"Unknown argument enabled_linters={enabled_linters} for lint()")
            for linter in linters_to_check:
                try:
                    run.checks.extend(linter.lint(data_contract))
                except Exception as e:
                    run.checks.append(
                        Check(
                            type="general",
                            result="error",
                            name=f"Linter '{linter.name}'",
                            reason=str(e),
                            engine="datacontract",
                        )
                    )
            run.dataContractId = data_contract.id
            run.dataContractVersion = data_contract.info.version
        except DataContractException as e:
            run.checks.append(
                Check(type=e.type, result=e.result, name=e.name, reason=e.reason, engine=e.engine, details="")
            )
            run.log_error(str(e))
        except Exception as e:
            run.checks.append(
                Check(
                    type="general",
                    result="error",
                    name="Check Data Contract",
                    reason=str(e),
                    engine="datacontract",
                )
            )
            run.log_error(str(e))
        run.finish()
        return run

    def test(self) -> Run:
        run = Run.create_run()
        try:
            run.log_info("Testing data contract")
            data_contract = resolve.resolve_data_contract(
                self._data_contract_file, self._data_contract_str, self._data_contract, self._schema_location
            )

            if data_contract.models is None or len(data_contract.models) == 0:
                raise DataContractException(
                    type="lint",
                    name="Check that data contract contains models",
                    result="warning",
                    reason="Models block is missing. Skip executing tests.",
                    engine="datacontract",
                )

            if self._examples:
                if data_contract.examples is None or len(data_contract.examples) == 0:
                    raise DataContractException(
                        type="lint",
                        name="Check that data contract contains valid examples",
                        result="warning",
                        reason="Examples block is missing. Skip executing tests.",
                        engine="datacontract",
                    )
            else:
                check_that_datacontract_contains_valid_server_configuration(run, data_contract, self._server)

            # TODO create directory only for examples
            with tempfile.TemporaryDirectory(prefix="datacontract-cli") as tmp_dir:
                if self._examples:
                    server_name = "examples"
                    server = self._get_examples_server(data_contract, run, tmp_dir)
                else:
                    server_name = list(data_contract.servers.keys())[0]
                    server = data_contract.servers.get(server_name)

                run.log_info(f"Running tests for data contract {data_contract.id} with server {server_name}")
                run.dataContractId = data_contract.id
                run.dataContractVersion = data_contract.info.version
                run.dataProductId = server.dataProductId
                run.outputPortId = server.outputPortId
                run.server = server_name

                # 5. check server is supported type
                # 6. check server credentials are complete
                if server.format == "json" and server.type != "kafka":
                    check_jsonschema(run, data_contract, server)
                check_soda_execute(run, data_contract, server, self._spark, tmp_dir)

        except DataContractException as e:
            run.checks.append(
                Check(type=e.type, result=e.result, name=e.name, reason=e.reason, engine=e.engine, details="")
            )
            run.log_error(str(e))
        except Exception as e:
            run.checks.append(
                Check(
                    type="general",
                    result="error",
                    name="Test Data Contract",
                    reason=str(e),
                    engine="datacontract",
                )
            )
            logging.exception("Exception occurred")
            run.log_error(str(e))

        run.finish()

        if self._publish_url is not None:
            try:
                publish_datamesh_manager(run, self._publish_url)
            except Exception:
                run.log_error("Failed to publish to datamesh manager")
        if self._publish_to_opentelemetry:
            try:
                publish_opentelemetry(run)
            except Exception:
                run.log_error("Failed to publish to opentelemetry")

        return run

    def breaking(self, other: "DataContract") -> BreakingChanges:
        return self.changelog(other, include_severities=[Severity.ERROR, Severity.WARNING])

    def changelog(
        self, other: "DataContract", include_severities: [Severity] = (Severity.ERROR, Severity.WARNING, Severity.INFO)
    ) -> BreakingChanges:
        old = self.get_data_contract_specification()
        new = other.get_data_contract_specification()

        breaking_changes = list[BreakingChange]()

        breaking_changes.extend(
            quality_breaking_changes(
                old_quality=old.quality,
                new_quality=new.quality,
                new_path=other._data_contract_file,
                include_severities=include_severities,
            )
        )

        breaking_changes.extend(
            models_breaking_changes(
                old_models=old.models,
                new_models=new.models,
                new_path=other._data_contract_file,
                include_severities=include_severities,
            )
        )

        return BreakingChanges(breaking_changes=breaking_changes)

    def get_data_contract_specification(self) -> DataContractSpecification:
        return resolve.resolve_data_contract(
            data_contract_location=self._data_contract_file,
            data_contract_str=self._data_contract_str,
            data_contract=self._data_contract,
            schema_location=self._schema_location,
            inline_definitions=self._inline_definitions,
            inline_quality=self._inline_quality,
        )

    def export(self, export_format, model: str = "all", rdf_base: str = None, sql_server_type: str = "auto") -> str:
        data_contract = resolve.resolve_data_contract(
            self._data_contract_file,
            self._data_contract_str,
            self._data_contract,
            inline_definitions=True,
            inline_quality=True,
        )
        if export_format == "jsonschema":
            model_name, model_value = self._check_models_for_export(data_contract, model, export_format)
            return to_jsonschema_json(model_name, model_value)
        if export_format == "sodacl":
            return to_sodacl_yaml(data_contract)
        if export_format == "dbt":
            return to_dbt_models_yaml(data_contract)
        if export_format == "dbt-sources":
            return to_dbt_sources_yaml(data_contract, self._server)
        if export_format == "dbt-staging-sql":
            model_name, model_value = self._check_models_for_export(data_contract, model, export_format)
            return to_dbt_staging_sql(data_contract, model_name, model_value)
        if export_format == "odcs":
            return to_odcs_yaml(data_contract)
        if export_format == "rdf":
            return to_rdf_n3(data_contract, rdf_base)
        if export_format == "protobuf":
            return to_protobuf(data_contract)
        if export_format == "avro":
            model_name, model_value = self._check_models_for_export(data_contract, model, export_format)
            return to_avro_schema_json(model_name, model_value)
        if export_format == "avro-idl":
            return to_avro_idl(data_contract)
        if export_format == "terraform":
            return to_terraform(data_contract)
        if export_format == "sql":
            server_type = self._determine_sql_server_type(data_contract, sql_server_type)
            return to_sql_ddl(data_contract, server_type=server_type)
        if export_format == "sql-query":
            model_name, model_value = self._check_models_for_export(data_contract, model, export_format)
            server_type = self._determine_sql_server_type(data_contract, sql_server_type)
            return to_sql_query(data_contract, model_name, model_value, server_type)
        if export_format == "great-expectations":
            model_name, model_value = self._check_models_for_export(data_contract, model, export_format)
            return to_great_expectations(data_contract, model_name)
        if export_format == "pydantic-model":
            return to_pydantic_model_str(data_contract)
        if export_format == "html":
            return to_html(data_contract)
        if export_format == "go":
            return to_go_types(data_contract)
        if export_format == "bigquery":
            model_name, model_value = self._check_models_for_export(data_contract, model, export_format)
            found_server = data_contract.servers.get(self._server)
            if found_server is None:
                raise RuntimeError(f"Export to {export_format} requires selecting a bigquery server from the data contract.")
            if found_server.type != 'bigquery':
                raise RuntimeError(f"Export to {export_format} requires selecting a bigquery server from the data contract.")
            return to_bigquery_json(model_name, model_value, found_server)
        else:
            print(f"Export format {export_format} not supported.")
            return ""

    def _determine_sql_server_type(self, data_contract: DataContractSpecification, sql_server_type: str):
        if sql_server_type == "auto":
            if data_contract.servers is None or len(data_contract.servers) == 0:
                raise RuntimeError("Export with server_type='auto' requires servers in the data contract.")

            server_types = set([server.type for server in data_contract.servers.values()])
            if "snowflake" in server_types:
                return "snowflake"
            elif "postgres" in server_types:
                return "postgres"
            elif "databricks" in server_types:
                return "databricks"
            else:
                # default to snowflake dialect
                return "snowflake"
        else:
            return sql_server_type

    def _get_examples_server(self, data_contract, run, tmp_dir):
        run.log_info(f"Copying examples to files in temporary directory {tmp_dir}")
        format = "json"
        for example in data_contract.examples:
            format = example.type
            p = f"{tmp_dir}/{example.model}.{format}"
            run.log_info(f"Creating example file {p}")
            with open(p, "w") as f:
                content = ""
                if format == "json" and isinstance(example.data, list):
                    content = json.dumps(example.data)
                elif format == "json" and isinstance(example.data, str):
                    content = example.data
                elif format == "yaml" and isinstance(example.data, list):
                    content = yaml.dump(example.data, allow_unicode=True)
                elif format == "yaml" and isinstance(example.data, str):
                    content = example.data
                elif format == "csv":
                    content = example.data
                logging.debug(f"Content of example file {p}: {content}")
                f.write(content)
        path = f"{tmp_dir}" + "/{model}." + format
        delimiter = "array"
        server = Server(
            type="local",
            path=path,
            format=format,
            delimiter=delimiter,
        )
        run.log_info(f"Using {server} for testing the examples")
        return server
    
    def _check_models_for_export(self, data_contract: DataContractSpecification, model: str, export_format: str) -> typing.Tuple[str, str]:
        if data_contract.models is None:
            raise RuntimeError(f"Export to {export_format} requires models in the data contract.")

        model_names = list(data_contract.models.keys())

        if model == "all":
            if len(data_contract.models.items()) != 1:
                raise RuntimeError(
                    f"Export to {export_format} is model specific. Specify the model via --model $MODEL_NAME. Available models: {model_names}"
                )

            model_name, model_value = next(iter(data_contract.models.items()))
        else:
            model_name = model
            model_value = data_contract.models.get(model_name)
            if model_value is None:
                raise RuntimeError(
                    f"Model {model_name} not found in the data contract. Available models: {model_names}"
                )
            
        return model_name, model_value

    def import_from_source(self, format: str, source: typing.Optional[str] = None, bigquery_tables: typing.Optional[typing.List[str]] = None, bigquery_project: typing.Optional[str] = None, bigquery_dataset: typing.Optional[str] = None) -> DataContractSpecification:
        data_contract_specification = DataContract.init()

        if format == "sql":
            data_contract_specification = import_sql(data_contract_specification, format, source)
        elif format == "avro":
            data_contract_specification = import_avro(data_contract_specification, source)
        elif format == "glue":
            data_contract_specification = import_glue(data_contract_specification, source)
        elif format == "jsonschema":
            data_contract_specification = import_jsonschema(data_contract_specification, source)
        elif format == "bigquery":
            if source is not None:
                data_contract_specification = import_bigquery_from_json(data_contract_specification, source)
            else:
                data_contract_specification = import_bigquery_from_api(data_contract_specification, bigquery_tables, bigquery_project, bigquery_dataset)
        else:
            print(f"Import format {format} not supported.")

        return data_contract_specification
