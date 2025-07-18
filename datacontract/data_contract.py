import logging
import typing

from open_data_contract_standard.model import CustomProperty, OpenDataContractStandard

from datacontract.export.odcs_v3_exporter import to_odcs_v3
from datacontract.imports.importer import ImportFormat, Spec
from datacontract.imports.odcs_v3_importer import import_from_odcs

if typing.TYPE_CHECKING:
    from pyspark.sql import SparkSession

from duckdb.duckdb import DuckDBPyConnection

from datacontract.breaking.breaking import (
    info_breaking_changes,
    models_breaking_changes,
    quality_breaking_changes,
    terms_breaking_changes,
)
from datacontract.breaking.breaking_change import BreakingChange, BreakingChanges, Severity
from datacontract.engines.data_contract_test import execute_data_contract_test
from datacontract.export.exporter import ExportFormat
from datacontract.export.exporter_factory import exporter_factory
from datacontract.imports.importer_factory import importer_factory
from datacontract.init.init_template import get_init_template
from datacontract.integration.datamesh_manager import publish_test_results_to_datamesh_manager
from datacontract.lint import resolve
from datacontract.lint.linters.description_linter import DescriptionLinter
from datacontract.lint.linters.field_pattern_linter import FieldPatternLinter
from datacontract.lint.linters.field_reference_linter import FieldReferenceLinter
from datacontract.lint.linters.notice_period_linter import NoticePeriodLinter
from datacontract.lint.linters.valid_constraints_linter import ValidFieldConstraintsLinter
from datacontract.model.data_contract_specification import DataContractSpecification, Info
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Check, ResultEnum, Run


class DataContract:
    def __init__(
        self,
        data_contract_file: str = None,
        data_contract_str: str = None,
        data_contract: DataContractSpecification = None,
        schema_location: str = None,
        server: str = None,
        publish_url: str = None,
        spark: "SparkSession" = None,
        duckdb_connection: DuckDBPyConnection = None,
        inline_definitions: bool = True,
        inline_quality: bool = True,
        ssl_verification: bool = True,
        publish_test_results: bool = False,
    ):
        self._data_contract_file = data_contract_file
        self._data_contract_str = data_contract_str
        self._data_contract = data_contract
        self._schema_location = schema_location
        self._server = server
        self._publish_url = publish_url
        self._publish_test_results = publish_test_results
        self._spark = spark
        self._duckdb_connection = duckdb_connection
        self._inline_definitions = inline_definitions
        self._inline_quality = inline_quality
        self._ssl_verification = ssl_verification
        self.all_linters = {
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
                Check(
                    type="lint",
                    result=ResultEnum.passed,
                    name="Data contract is syntactically valid",
                    engine="datacontract",
                )
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
                            result=ResultEnum.error,
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
                    result=ResultEnum.error,
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

            execute_data_contract_test(data_contract, run, self._server, self._spark, self._duckdb_connection)

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
                    result=ResultEnum.error,
                    name="Test Data Contract",
                    reason=str(e),
                    engine="datacontract",
                )
            )
            logging.exception("Exception occurred")
            run.log_error(str(e))

        run.finish()

        if self._publish_url is not None or self._publish_test_results:
            publish_test_results_to_datamesh_manager(run, self._publish_url, self._ssl_verification)

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
        if export_format == ExportFormat.html or export_format == ExportFormat.mermaid:
            data_contract = resolve.resolve_data_contract_v2(
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
        else:
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

    # REFACTOR THIS
    # could be a class method, not using anything from the instance
    def import_from_source(
        self,
        format: str,
        source: typing.Optional[str] = None,
        template: typing.Optional[str] = None,
        schema: typing.Optional[str] = None,
        spec: Spec = Spec.datacontract_specification,
        **kwargs,
    ) -> DataContractSpecification | OpenDataContractStandard:
        id = kwargs.get("id")
        owner = kwargs.get("owner")

        if spec == Spec.odcs or format == ImportFormat.excel:
            data_contract_specification_initial = DataContract.init(template=template, schema=schema)

            odcs_imported = importer_factory.create(format).import_source(
                data_contract_specification=data_contract_specification_initial, source=source, import_args=kwargs
            )

            if isinstance(odcs_imported, DataContractSpecification):
                # convert automatically
                odcs_imported = to_odcs_v3(odcs_imported)

            self._overwrite_id_in_odcs(odcs_imported, id)
            self._overwrite_owner_in_odcs(odcs_imported, owner)

            return odcs_imported
        elif spec == Spec.datacontract_specification:
            data_contract_specification_initial = DataContract.init(template=template, schema=schema)

            data_contract_specification_imported = importer_factory.create(format).import_source(
                data_contract_specification=data_contract_specification_initial, source=source, import_args=kwargs
            )

            if isinstance(data_contract_specification_imported, OpenDataContractStandard):
                # convert automatically
                data_contract_specification_imported = import_from_odcs(
                    data_contract_specification_initial, data_contract_specification_imported
                )

            self._overwrite_id_in_data_contract_specification(data_contract_specification_imported, id)
            self._overwrite_owner_in_data_contract_specification(data_contract_specification_imported, owner)

            return data_contract_specification_imported
        else:
            raise DataContractException(
                type="general",
                result=ResultEnum.error,
                name="Import Data Contract",
                reason=f"Unsupported data contract format: {spec}",
                engine="datacontract",
            )

    def _overwrite_id_in_data_contract_specification(
        self, data_contract_specification: DataContractSpecification, id: str | None
    ):
        if not id:
            return

        data_contract_specification.id = id

    def _overwrite_owner_in_data_contract_specification(
        self, data_contract_specification: DataContractSpecification, owner: str | None
    ):
        if not owner:
            return

        if data_contract_specification.info is None:
            data_contract_specification.info = Info()
        data_contract_specification.info.owner = owner

    def _overwrite_owner_in_odcs(self, odcs: OpenDataContractStandard, owner: str | None):
        if not owner:
            return

        if odcs.customProperties is None:
            odcs.customProperties = []
        for customProperty in odcs.customProperties:
            if customProperty.name == "owner":
                customProperty.value = owner
                return
        odcs.customProperties.append(CustomProperty(property="owner", value=owner))

    def _overwrite_id_in_odcs(self, odcs: OpenDataContractStandard, id: str | None):
        if not id:
            return

        odcs.id = id
