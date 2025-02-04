import json
import logging
import tempfile
import typing

import yaml

if typing.TYPE_CHECKING:
    from pyspark.sql import SparkSession

from datacontract.breaking.breaking import (
    info_breaking_changes,
    models_breaking_changes,
    quality_breaking_changes,
    terms_breaking_changes,
)
from datacontract.engines.datacontract.check_that_datacontract_contains_valid_servers_configuration import (
    check_that_datacontract_contains_valid_server_configuration,
)
from datacontract.engines.fastjsonschema.check_jsonschema import check_jsonschema
from datacontract.engines.soda.check_soda_execute import check_soda_execute
from datacontract.export.exporter import ExportFormat
from datacontract.export.exporter_factory import exporter_factory
from datacontract.imports.importer_factory import importer_factory
from datacontract.init.init_template import get_init_template
from datacontract.integration.datamesh_manager import publish_test_results_to_datamesh_manager
from datacontract.lint import resolve
from datacontract.lint.linters.description_linter import DescriptionLinter
from datacontract.lint.linters.example_model_linter import ExampleModelLinter
from datacontract.lint.linters.field_pattern_linter import FieldPatternLinter
from datacontract.lint.linters.field_reference_linter import FieldReferenceLinter
from datacontract.lint.linters.notice_period_linter import NoticePeriodLinter
from datacontract.lint.linters.quality_schema_linter import QualityUsesSchemaLinter
from datacontract.lint.linters.valid_constraints_linter import ValidFieldConstraintsLinter
from datacontract.model.breaking_change import BreakingChange, BreakingChanges, Severity
from datacontract.model.data_contract_specification import DataContractSpecification, Server
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Check, Run


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
        spark: "SparkSession" = None,
        inline_definitions: bool = True,
        inline_quality: bool = True,
        ssl_verification: bool = True,
    ):
        self._data_contract_file = data_contract_file
        self._data_contract_str = data_contract_str
        self._data_contract = data_contract
        self._schema_location = schema_location
        self._server = server
        self._examples = examples
        self._publish_url = publish_url
        self._spark = spark
        self._inline_definitions = inline_definitions
        self._inline_quality = inline_quality
        self._ssl_verification = ssl_verification
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
    def init(cls, template: typing.Optional[str], schema: typing.Optional[str] = None) -> DataContractSpecification:
        template_str = get_init_template(template)
        return resolve.resolve_data_contract(data_contract_str=template_str, schema_location=schema)

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
                inline_definitions=self._inline_definitions,
                inline_quality=self._inline_quality,
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
                self._data_contract_file,
                self._data_contract_str,
                self._data_contract,
                self._schema_location,
                inline_definitions=self._inline_definitions,
                inline_quality=self._inline_quality,
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
                elif self._server:
                    server_name = self._server
                    server = data_contract.servers.get(server_name)
                else:
                    server_name = list(data_contract.servers.keys())[0]
                    server = data_contract.servers.get(server_name)

                run.log_info(f"Running tests for data contract {data_contract.id} with server {server_name}")
                run.dataContractId = data_contract.id
                run.dataContractVersion = data_contract.info.version
                run.dataProductId = server.dataProductId
                run.outputPortId = server.outputPortId
                run.server = server_name

                # TODO check server is supported type for nicer error messages

                # TODO check server credentials are complete for nicer error messages

                if server.format == "json" and server.type != "kafka":
                    check_jsonschema(run, data_contract, server)

                check_soda_execute(run, data_contract, server, self._spark, tmp_dir)

        except DataContractException as e:
            run.checks.append(
                Check(
                    type=e.type,
                    name=e.name,
                    result=e.result,
                    reason=e.reason,
                    model=e.model,
                    engine=e.engine,
                    details="",
                )
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
            publish_test_results_to_datamesh_manager(run, self._publish_url, self._ssl_verification)

        return run

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

    def breaking(self, other: "DataContract") -> BreakingChanges:
        return self.changelog(other, include_severities=[Severity.ERROR, Severity.WARNING])

    def changelog(
        self, other: "DataContract", include_severities: [Severity] = (Severity.ERROR, Severity.WARNING, Severity.INFO)
    ) -> BreakingChanges:
        old = self.get_data_contract_specification()
        new = other.get_data_contract_specification()

        breaking_changes = list[BreakingChange]()

        breaking_changes.extend(
            info_breaking_changes(
                old_info=old.info,
                new_info=new.info,
                new_path=other._data_contract_file,
                include_severities=include_severities,
            )
        )

        breaking_changes.extend(
            terms_breaking_changes(
                old_terms=old.terms,
                new_terms=new.terms,
                new_path=other._data_contract_file,
                include_severities=include_severities,
            )
        )

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

    def export(self, export_format: ExportFormat, model: str = "all", sql_server_type: str = "auto", **kwargs) -> str:
        data_contract = resolve.resolve_data_contract(
            self._data_contract_file,
            self._data_contract_str,
            self._data_contract,
            schema_location=self._schema_location,
            inline_definitions=self._inline_definitions,
            inline_quality=self._inline_quality,
        )

        return exporter_factory.create(export_format).export(
            data_contract=data_contract,
            model=model,
            server=self._server,
            sql_server_type=sql_server_type,
            export_args=kwargs,
        )

    def import_from_source(
        self,
        format: str,
        source: typing.Optional[str] = None,
        template: typing.Optional[str] = None,
        schema: typing.Optional[str] = None,
        **kwargs,
    ) -> DataContractSpecification:
        data_contract_specification_initial = DataContract.init(template=template, schema=schema)

        return importer_factory.create(format).import_source(
            data_contract_specification=data_contract_specification_initial, source=source, import_args=kwargs
        )
