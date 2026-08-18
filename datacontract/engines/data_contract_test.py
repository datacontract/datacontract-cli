import atexit
import tempfile
import typing

import requests
from open_data_contract_standard.model import OpenDataContractStandard, Server

from datacontract.config import Config
from datacontract.engines.checks.create_checks import create_checks, to_schema_name
from datacontract.engines.checks.dimensions import default_dimension

if typing.TYPE_CHECKING:
    from duckdb.duckdb import DuckDBPyConnection
    from pyspark.sql import SparkSession

from datacontract.engines.datacontract.check_azure_blob_file import check_azure_blob_file
from datacontract.engines.datacontract.check_that_datacontract_contains_valid_servers_configuration import (
    check_that_datacontract_contains_valid_server_configuration,
)
from datacontract.engines.fastjsonschema.check_jsonschema import check_jsonschema
from datacontract.engines.ibis.ibis_check_execute import build_check_stubs, execute_ibis_checks, set_result
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum, Run


def execute_data_contract_test(
    data_contract: OpenDataContractStandard,
    run: Run,
    server_name: str = None,
    spark: "SparkSession" = None,
    duckdb_connection: "DuckDBPyConnection" = None,
    schema_name: str = "all",
    check_categories: set[str] | None = None,
    dimensions: set[str] | None = None,
    quality_ids: set[str] | None = None,
    tags: set[str] | None = None,
    include_failed_samples: bool = False,
    filter: str | None = None,
    filters: dict[str, str] | None = None,
    metadata_only: bool = False,
    config: Config | None = None,
    untrusted_contract: bool = False,
):
    config = Config.resolve(config)
    if data_contract.schema_ is None or len(data_contract.schema_) == 0:
        raise DataContractException(
            type="lint",
            name="Check that data contract contains models",
            result=ResultEnum.warning,
            reason="Schema block is missing. Skip executing tests.",
            engine="datacontract",
        )
    if server_name is None and data_contract.servers is not None and len(data_contract.servers) > 0:
        server_name = data_contract.servers[0].server
    server = get_server(data_contract, server_name)
    run.log_info(f"Running tests for data contract {data_contract.id} with server {server_name}")
    run.dataContractId = data_contract.id
    run.dataContractVersion = data_contract.version
    run.dataProductId = data_contract.dataProduct
    run.outputPortId = None  # ODCS doesn't have outputPortId
    run.server = server_name

    if schema_name != "all":
        schema_names = {s.name for s in data_contract.schema_} if data_contract.schema_ else set()
        if schema_name not in schema_names:
            raise DataContractException(
                type="lint",
                name="Check that schema name exists",
                result=ResultEnum.failed,
                reason=f"Schema '{schema_name}' not found in data contract. Available schemas: {sorted(schema_names)}",
                engine="datacontract",
            )

    if quality_ids is not None:
        # A quality rule id is a precise reference, like --schema-name: an id that
        # matches nothing is a typo, and silently testing nothing would pass.
        check_that_quality_ids_exist(data_contract, quality_ids, schema_name)

    if server.type == "api":
        server = process_api_response(run, server, config)

    model_filters = resolve_row_filters(data_contract, server, run, filter, filters, schema_name)

    specs = create_checks(data_contract, server, schema_name=schema_name)
    if check_categories is not None:
        specs = [s for s in specs if s.category in check_categories]
        if not specs:
            run.log_warn(f"No checks found for categories: {', '.join(sorted(check_categories))}")
    # Every check carries a dimension: the rule's own ODCS `quality.dimension`,
    # or the one the built-in check measures (see checks/dimensions.py).
    if dimensions is not None:
        specs = [s for s in specs if s.dimension in dimensions]
        if not specs:
            run.log_warn(f"No checks found for dimensions: {', '.join(sorted(dimensions))}")
    # Only quality rules carry an id and tags, so these filters exclude the
    # built-in schema and service level checks entirely.
    if quality_ids is not None:
        specs = [s for s in specs if s.quality_id in quality_ids]
        if not specs:
            run.log_warn(f"No checks found for quality rule ids: {', '.join(sorted(quality_ids))}")
    if tags is not None:
        specs = [s for s in specs if s.tags and not tags.isdisjoint(s.tags)]
        if not specs:
            run.log_warn(f"No checks found for tags: {', '.join(sorted(tags))}")
    run.checks.extend(build_check_stubs(specs))

    if metadata_only:
        executable = []
        for spec in specs:
            if spec.requires_data_read:
                set_result(run, spec.key, ResultEnum.skipped, "Row-value check disabled by --metadata-only")
            else:
                executable.append(spec)
        specs = executable

    # TODO check server is supported type for nicer error messages
    # TODO check server credentials are complete for nicer error messages
    if server.format == "json" and server.type != "kafka":
        # The JSON Schema validation emits checks of type "schema" throughout,
        # so it is out of scope once a quality rule is selected by id or tag.
        if (
            (check_categories is None or "schema" in check_categories)
            and (dimensions is None or default_dimension("schema") in dimensions)
            and quality_ids is None
            and tags is None
        ):
            check_jsonschema(run, data_contract, server, schema_name=schema_name, config=config)
    # Azure Blob / ADLS Gen2 file-metadata checks (logicalType=blob schemas)
    if server.type == "azure" and _has_blob_schemas(data_contract, schema_name):
        check_azure_blob_file(
            run,
            data_contract,
            server,
            schema_name=schema_name,
            check_categories=check_categories,
            dimensions=dimensions,
            quality_ids=quality_ids,
            tags=tags,
            config=config,
        )
    execute_ibis_checks(
        run,
        data_contract,
        server,
        specs,
        spark,
        duckdb_connection,
        schema_name=schema_name,
        include_failed_samples=include_failed_samples,
        model_filters=model_filters,
        config=config,
        untrusted_contract=untrusted_contract,
    )


def resolve_row_filters(
    data_contract: OpenDataContractStandard,
    server: Server,
    run: Run,
    filter: str | None,
    filters: dict[str, str] | None,
    schema_name: str = "all",
) -> dict[str, str] | None:
    """Normalize --filter/--filters into a mapping of physical model name to predicate.

    Filters are given per contract schema name; the engine addresses tables by
    their physical name. Records the applied filters on the run.
    """
    if filter is not None and filter.strip() == "":
        filter = None
    if filter is not None and filters:
        raise DataContractException(
            type="lint",
            name="Check row filter arguments",
            result=ResultEnum.failed,
            reason="Use either a single filter predicate or per-schema filters, not both.",
            engine="datacontract",
        )
    schema_objects = data_contract.schema_ or []
    if filter is not None:
        candidates = [s for s in schema_objects if schema_name == "all" or s.name == schema_name]
        if len(candidates) != 1:
            raise DataContractException(
                type="lint",
                name="Check row filter arguments",
                result=ResultEnum.failed,
                reason=f"--filter is ambiguous, as the data contract has multiple schemas: "
                f"{sorted(s.name for s in candidates)}. "
                f'Use --filters \'{{"<schema>": "<predicate>"}}\' or select a single schema with --schema-name.',
                engine="datacontract",
            )
        filters = {candidates[0].name: filter.strip()}
    if not filters:
        return None
    schema_by_name = {s.name: s for s in schema_objects}
    unknown = sorted(set(filters) - set(schema_by_name))
    if unknown:
        raise DataContractException(
            type="lint",
            name="Check that filter schema exists",
            result=ResultEnum.failed,
            reason=f"Filter schema(s) not found in data contract: {', '.join(unknown)}. "
            f"Available schemas: {sorted(schema_by_name)}",
            engine="datacontract",
        )
    run.filters = dict(filters)
    for name, predicate in filters.items():
        run.log_info(f"Applying row filter to schema {name}: {predicate}")
    server_type = server.type if server else None
    return {to_schema_name(schema_by_name[name], server_type): predicate for name, predicate in filters.items()}


def quality_rule_ids(data_contract: OpenDataContractStandard, schema_name: str = "all") -> set[str]:
    """The ids declared by the quality rules of the contract, on schemas and properties."""
    ids: set[str] = set()

    def collect(quality_list) -> None:
        for quality in quality_list or []:
            if quality.id is not None:
                ids.add(quality.id)

    for schema_object in data_contract.schema_ or []:
        if schema_name != "all" and schema_object.name != schema_name:
            continue
        collect(schema_object.quality)
        for prop in schema_object.properties or []:
            collect(prop.quality)
    return ids


def check_that_quality_ids_exist(
    data_contract: OpenDataContractStandard, quality_ids: set[str], schema_name: str = "all"
) -> None:
    available = quality_rule_ids(data_contract, schema_name)
    unknown = sorted(quality_ids - available)
    if not unknown:
        return
    raise DataContractException(
        type="lint",
        name="Check that quality rule id exists",
        result=ResultEnum.failed,
        reason=(
            f"Quality rule id(s) not found in data contract: {', '.join(unknown)}. "
            f"Available quality rule ids: {sorted(available)}"
        ),
        engine="datacontract",
    )


def get_server(data_contract: OpenDataContractStandard, server_name: str = None) -> Server | None:
    """Get the server configuration from the data contract.

    Args:
        data_contract: The data contract
        server_name: Optional name of the server to use. If not provided, uses the first server.

    Returns:
        The selected server configuration
    """

    check_that_datacontract_contains_valid_server_configuration(data_contract, server_name)

    if data_contract.servers is None:
        return None

    if server_name is not None:
        server = next((s for s in data_contract.servers if s.server == server_name), None)
    else:
        server = data_contract.servers[0] if data_contract.servers else None
    return server


def process_api_response(run, server, config: Config | None = None):
    config = Config.resolve(config)
    tmp_dir = tempfile.TemporaryDirectory(prefix="datacontract_cli_api_")
    atexit.register(tmp_dir.cleanup)
    headers = {}
    if config.get_api_header_authorization() is not None:
        headers["Authorization"] = config.get_api_header_authorization()
    try:
        response = requests.get(server.location, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise DataContractException(
            type="connection",
            name="API server connection error",
            result=ResultEnum.error,
            reason=f"Failed to fetch API response from {server.location}: {e}",
            engine="datacontract",
        )
    with open(f"{tmp_dir.name}/api_response.json", "w") as f:
        f.write(response.text)
    run.log_info(f"Saved API response to {tmp_dir.name}/api_response.json")
    new_server = Server(
        server="api_local",
        type="local",
        format="json",
        path=f"{tmp_dir.name}/api_response.json",
        delimiter=server.delimiter,
    )
    return new_server


def _has_blob_schemas(data_contract: OpenDataContractStandard, schema_name: str) -> bool:
    """Return True if the (possibly filtered) schema list contains any logicalType='blob' schema."""
    if data_contract.schema_ is None:
        return False
    for s in data_contract.schema_:
        if schema_name != "all" and s.name != schema_name:
            continue
        if (s.logicalType or "").lower() == "blob":
            return True
    return False
