import inspect
import logging
import typing
from importlib import metadata

from open_data_contract_standard.model import OpenDataContractStandard, Team

if typing.TYPE_CHECKING:
    from duckdb.duckdb import DuckDBPyConnection
    from pyspark.sql import SparkSession

from datacontract.breaking.detector import BreakingChangeDetector
from datacontract.config import Config
from datacontract.engines.checks.dimensions import default_dimension
from datacontract.engines.data_contract_test import execute_data_contract_test
from datacontract.export.exporter import ExportFormat
from datacontract.export.exporter_factory import exporter_factory
from datacontract.imports.importer_factory import importer_factory
from datacontract.init.init_template import get_init_template
from datacontract.integration.entropy_data import publish_test_results_to_entropy_data
from datacontract.lint import resolve
from datacontract.model.breaking import BreakingChangeResult
from datacontract.model.changelog import ChangelogEntry, ChangelogResult, ChangelogType
from datacontract.model.exceptions import DataContractException, DataContractValidationErrors
from datacontract.model.run import Check, ResultEnum, Run


class DataContract:
    def __init__(
        self,
        data_contract_file: str = None,
        data_contract_str: str = None,
        data_contract: OpenDataContractStandard = None,
        schema_location: str = None,
        server: str = None,
        schema_name: str = "all",
        publish_url: str = None,
        spark: "SparkSession" = None,
        duckdb_connection: "DuckDBPyConnection" = None,
        inline_references: bool = True,
        ssl_verification: bool = True,
        publish_test_results: bool = False,
        all_errors: bool = False,
        check_categories: set[str] | None = None,
        dimensions: set[str] | None = None,
        quality_ids: set[str] | None = None,
        tags: set[str] | None = None,
        fastapi_url: str = None,
        include_failed_samples: bool = False,
        filter: str = None,
        filters: dict[str, str] | None = None,
        metadata_only: bool = False,
        dry_run: bool = False,
        untrusted_contract: bool = False,
        config: "Config | dict[str, str] | None" = None,
    ):
        self._data_contract_file = data_contract_file
        self._data_contract_str = data_contract_str
        self._data_contract = data_contract
        self._schema_location = schema_location
        self._server = server
        self._schema_name = schema_name
        self._publish_url = publish_url
        self._publish_test_results = publish_test_results
        self._spark = spark
        self._duckdb_connection = duckdb_connection
        self._inline_references = inline_references
        self._ssl_verification = ssl_verification
        self._all_errors = all_errors
        self._check_categories = check_categories
        self._dimensions = dimensions
        self._quality_ids = quality_ids
        self._tags = tags
        self._fastapi_url = fastapi_url
        self._include_failed_samples = include_failed_samples
        self._filter = filter
        self._filters = filters
        self._metadata_only = metadata_only
        self._dry_run = dry_run
        # The contract came from somewhere the caller does not control (the API
        # server), so the SQL it carries must not reach the host running it.
        self._untrusted_contract = untrusted_contract
        self._config = Config.resolve(config)

    @classmethod
    def init(cls, template: typing.Optional[str], schema: typing.Optional[str] = None) -> OpenDataContractStandard:
        template_str = get_init_template(template)
        return resolve.resolve_data_contract(data_contract_str=template_str, schema_location=schema)

    def lint(self) -> Run:
        """Lint the data contract by validating it against the JSON schema."""
        run = Run.create_run()
        try:
            run.log_info("Linting data contract")
            data_contract = resolve.resolve_data_contract(
                self._data_contract_file,
                self._data_contract_str,
                self._data_contract,
                self._schema_location,
                inline_references=self._inline_references,
                all_errors=self._all_errors,
                config=self._config,
            )
            run.checks.append(
                Check(
                    type="lint",
                    result=ResultEnum.passed,
                    name="Data contract is syntactically valid",
                    engine="datacontract-cli",
                )
            )
            run.dataContractId = data_contract.id
            run.dataContractVersion = data_contract.version
        except DataContractValidationErrors as e:
            for error in e.errors:
                run.checks.append(
                    Check(
                        type=error.type,
                        result=error.result,
                        name=error.name,
                        reason=error.reason,
                        engine=error.engine,
                    )
                )
                run.log_error(str(error))
        except DataContractException as e:
            run.checks.append(Check(type=e.type, result=e.result, name=e.name, reason=e.reason, engine=e.engine))
            run.log_error(str(e))
        except Exception as e:
            run.checks.append(
                Check(
                    type="general",
                    result=ResultEnum.error,
                    name="Check Data Contract",
                    reason=str(e),
                    engine="datacontract-cli",
                )
            )
            run.log_error(str(e))
        run.finish()
        return run

    def _runtime_info(self) -> str:
        try:
            version = metadata.version("datacontract-cli")
        except metadata.PackageNotFoundError:
            version = "unknown"
        if self._fastapi_url is not None:
            execution = f"running through FastAPI at {self._fastapi_url}"
        else:
            execution = "running as CLI locally"
        return f"Data Contract CLI {version} {execution}"

    def test(self) -> Run:
        run = Run.create_run()
        try:
            run.log_info("Testing data contract")
            run.log_info(self._runtime_info())
            data_contract = resolve.resolve_data_contract(
                self._data_contract_file,
                self._data_contract_str,
                self._data_contract,
                self._schema_location,
                inline_references=self._inline_references,
                config=self._config,
            )

            execute_data_contract_test(
                data_contract,
                run,
                self._server,
                self._spark,
                self._duckdb_connection,
                schema_name=self._schema_name,
                check_categories=self._check_categories,
                dimensions=self._dimensions,
                quality_ids=self._quality_ids,
                tags=self._tags,
                include_failed_samples=self._include_failed_samples,
                filter=self._filter,
                filters=self._filters,
                metadata_only=self._metadata_only,
                dry_run=self._dry_run,
                config=self._config,
                untrusted_contract=self._untrusted_contract,
            )

        except DataContractException as e:
            run.checks.append(
                Check(
                    type=e.type,
                    dimension=default_dimension(e.type),
                    name=e.name,
                    result=e.result,
                    reason=e.reason,
                    model=e.model,
                    engine=e.engine,
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
                    engine="datacontract-cli",
                )
            )
            logging.exception("Exception occurred")
            run.log_error(str(e))

        run.finish()

        if self._publish_url is not None or self._publish_test_results:
            if self._dry_run:
                run.log_warn("Publishing skipped (--dry-run is set).")
            else:
                run.publish_succeeded = publish_test_results_to_entropy_data(
                    run, self._publish_url, self._ssl_verification, config=self._config
                )

        return run

    def get_data_contract(self) -> OpenDataContractStandard:
        return resolve.resolve_data_contract(
            data_contract_location=self._data_contract_file,
            data_contract_str=self._data_contract_str,
            data_contract=self._data_contract,
            schema_location=self._schema_location,
            inline_references=self._inline_references,
            config=self._config,
        )

    def get_data_contract_file(self) -> str | None:
        return self._data_contract_file

    def export(
        self, export_format: ExportFormat, schema_name: str = "all", sql_server_type: str = "auto", **kwargs
    ) -> str | bytes:
        data_contract = resolve.resolve_data_contract(
            self._data_contract_file,
            self._data_contract_str,
            self._data_contract,
            schema_location=self._schema_location,
            inline_references=self._inline_references,
            config=self._config,
        )

        return exporter_factory.create(export_format).export(
            data_contract=data_contract,
            schema_name=schema_name,
            server=self._server,
            sql_server_type=sql_server_type,
            export_args=kwargs,
        )

    def changelog(self, other: "DataContract") -> ChangelogResult:
        """Generate a changelog between this data contract and another, returning a ChangelogResult."""
        from datacontract.changelog.changelog import build_changelog

        changelog = build_changelog(
            self.get_data_contract(),
            self.get_data_contract_file(),
            other.get_data_contract(),
            other.get_data_contract_file(),
        )

        v1_label = changelog["source_label"]
        v2_label = changelog["target_label"]
        result = ChangelogResult(v1=v1_label, v2=v2_label)
        for change in changelog["summary"]["changes"]:
            result.summary.append(
                ChangelogEntry(
                    path=change["path"],
                    type=ChangelogType(change["changeType"].lower()),
                )
            )
        for change in changelog["detail"]["changes"]:
            result.entries.append(
                ChangelogEntry(
                    path=change["path"],
                    type=ChangelogType(change["changeType"].lower()),
                    old_value=str(change["old_value"]) if change.get("old_value") is not None else None,
                    new_value=str(change["new_value"]) if change.get("new_value") is not None else None,
                )
            )
        return result

    def breaking(self, other: "DataContract", detector: BreakingChangeDetector | None = None) -> BreakingChangeResult:
        """Classify the changelog between this contract and another for compatibility impact."""
        changelog = self.changelog(other)
        return (detector or BreakingChangeDetector()).detect(changelog)

    @classmethod
    def import_from_source(
        cls,
        format: str,
        source: typing.Optional[str] = None,
        config: "Config | dict[str, str] | None" = None,
        **kwargs,
    ) -> OpenDataContractStandard:
        """Import a data contract from a source in a given format.

        All imports now return OpenDataContractStandard (ODCS) format.
        Credentials and connection options can be passed via ``config``.
        """
        id = kwargs.get("id")
        owner = kwargs.get("owner")

        importer = importer_factory.create(format)
        # Third-party importers registered before the config parameter existed may
        # still implement the two-argument signature; only pass config where declared.
        if "config" in inspect.signature(importer.import_source).parameters:
            odcs_imported = importer.import_source(source=source, import_args=kwargs, config=Config.resolve(config))
        else:
            odcs_imported = importer.import_source(source=source, import_args=kwargs)

        cls._overwrite_id_in_odcs(odcs_imported, id)
        cls._overwrite_owner_in_odcs(odcs_imported, owner)

        return odcs_imported

    @staticmethod
    def _overwrite_owner_in_odcs(odcs: OpenDataContractStandard, owner: str | None):
        if not owner:
            return

        if odcs.team is None:
            odcs.team = Team(name=owner)
        else:
            odcs.team.name = owner

    @staticmethod
    def _overwrite_id_in_odcs(odcs: OpenDataContractStandard, id: str | None):
        if not id:
            return

        odcs.id = id
