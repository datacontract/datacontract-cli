import logging
import typing

from open_data_contract_standard.model import OpenDataContractStandard, Team

if typing.TYPE_CHECKING:
    from pyspark.sql import SparkSession

from duckdb.duckdb import DuckDBPyConnection

from datacontract.engines.data_contract_test import execute_data_contract_test
from datacontract.export.exporter import ExportFormat
from datacontract.export.exporter_factory import exporter_factory
from datacontract.imports.importer_factory import importer_factory
from datacontract.init.init_template import get_init_template
from datacontract.integration.entropy_data import publish_test_results_to_entropy_data
from datacontract.lint import resolve
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Check, ResultEnum, Run


class DataContract:
    def __init__(
        self,
        data_contract_file: str = None,
        data_contract_str: str = None,
        data_contract: OpenDataContractStandard = None,
        schema_location: str = None,
        server: str = None,
        publish_url: str = None,
        spark: "SparkSession" = None,
        duckdb_connection: DuckDBPyConnection = None,
        inline_definitions: bool = True,
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
        self._ssl_verification = ssl_verification

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
                inline_definitions=self._inline_definitions,
            )
            run.checks.append(
                Check(
                    type="lint",
                    result=ResultEnum.passed,
                    name="Data contract is syntactically valid",
                    engine="datacontract",
                )
            )
            run.dataContractId = data_contract.id
            run.dataContractVersion = data_contract.version
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
            publish_test_results_to_entropy_data(run, self._publish_url, self._ssl_verification)

        return run

    def get_data_contract(self) -> OpenDataContractStandard:
        return resolve.resolve_data_contract(
            data_contract_location=self._data_contract_file,
            data_contract_str=self._data_contract_str,
            data_contract=self._data_contract,
            schema_location=self._schema_location,
            inline_definitions=self._inline_definitions,
        )

    def export(
        self, export_format: ExportFormat, schema_name: str = "all", sql_server_type: str = "auto", **kwargs
    ) -> str | bytes:
        if (
            export_format == ExportFormat.html
            or export_format == ExportFormat.mermaid
            or export_format == ExportFormat.excel
        ):
            data_contract = resolve.resolve_data_contract(
                self._data_contract_file,
                self._data_contract_str,
                self._data_contract,
                schema_location=self._schema_location,
                inline_definitions=self._inline_definitions,
            )

            return exporter_factory.create(export_format).export(
                data_contract=data_contract,
                schema_name=schema_name,
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
            )

            return exporter_factory.create(export_format).export(
                data_contract=data_contract,
                schema_name=schema_name,
                server=self._server,
                sql_server_type=sql_server_type,
                export_args=kwargs,
            )

    @classmethod
    def import_from_source(
        cls,
        format: str,
        source: typing.Optional[str] = None,
        template: typing.Optional[str] = None,
        **kwargs,
    ) -> OpenDataContractStandard:
        """Import a data contract from a source in a given format.

        All imports now return OpenDataContractStandard (ODCS) format.
        """
        id = kwargs.get("id")
        owner = kwargs.get("owner")

        odcs_imported = importer_factory.create(format).import_source(
            source=source, import_args=kwargs
        )

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
