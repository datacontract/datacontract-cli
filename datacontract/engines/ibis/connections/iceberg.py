"""Read Apache Iceberg tables through a REST catalog (ODCS v3.2.0 `type: iceberg`).

The server names the catalog (``catalog``), its REST endpoint (``catalogUrl``),
and optionally the ``namespace`` and ``warehouse``. Each schema object is one
table in that namespace. The table is loaded with pyiceberg, scanned to Arrow,
and registered in DuckDB, where the checks run like they do for file sources.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Optional

from open_data_contract_standard.model import OpenDataContractStandard, Server

from datacontract.config import Config
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum, Run

if TYPE_CHECKING:
    import duckdb
    from pyiceberg.catalog import Catalog
    from pyiceberg.table import Table


def catalog_properties(server: Server, config: Config | None = None) -> dict[str, str]:
    """The pyiceberg properties of the server's REST catalog.

    The configuration overrides win over the contract, like the other server
    details. Credentials come from the configuration only: an OAuth2 client
    credential (``DATACONTRACT_ICEBERG_CREDENTIAL``, ``client_id:client_secret``),
    a bearer token (``DATACONTRACT_ICEBERG_TOKEN``), or SigV4 signing with the
    AWS credentials for Amazon S3 Tables and Glue (detected from the endpoint,
    or set with ``DATACONTRACT_ICEBERG_SIGNING_NAME``), plus the S3 options for
    the data files. ``DATACONTRACT_ICEBERG_PROPERTIES`` passes anything else
    through to pyiceberg.
    """
    config = Config.resolve(config)
    uri = config.get_iceberg_catalog_url() or getattr(server, "catalogUrl", None)
    if not uri:
        raise DataContractException(
            type="iceberg-connection",
            name="missing_catalog_url",
            reason="catalogUrl is required for an Iceberg server (the catalog's REST endpoint or connection URI).",
            engine="datacontract-cli",
        )
    # pyiceberg catalog implementations: rest (default), sql, glue, hive, dynamodb, in-memory
    properties: dict[str, str] = {"type": config.get_iceberg_catalog_type() or "rest", "uri": uri}
    warehouse = config.get_iceberg_warehouse() or server.warehouse
    if warehouse:
        properties["warehouse"] = warehouse
    credential = config.get_iceberg_credential()
    if credential:
        properties["credential"] = credential
    token = config.get_iceberg_token()
    if token:
        properties["token"] = token
    # The S3 options serve the data files (``s3.*``) and, as pyiceberg's generic AWS
    # client options (``client.*``), the SigV4 signing of catalog requests.
    for option, key in (
        (config.get_s3_access_key_id(), "access-key-id"),
        (config.get_s3_secret_access_key(), "secret-access-key"),
        (config.get_s3_session_token(), "session-token"),
        (config.get_s3_region(), "region"),
    ):
        if option:
            properties[f"s3.{key}"] = option
            properties[f"client.{key}"] = option
    endpoint = config.get_iceberg_s3_endpoint()
    if endpoint:
        # an S3-compatible store such as MinIO; pyarrow's S3 file system then uses path-style addressing
        properties["s3.endpoint"] = endpoint
    signing_name = config.get_iceberg_signing_name() or aws_signing_name(uri)
    if signing_name:
        # Amazon S3 Tables and the Glue REST endpoint authenticate catalog requests
        # with SigV4 instead of a token; boto3's credential chain supplies the keys
        # when the S3 options are not set. S3 Tables vends the data file credentials.
        properties["rest.sigv4-enabled"] = "true"
        properties["rest.signing-name"] = signing_name
        region = config.get_s3_region() or aws_region(uri)
        if region:
            properties["rest.signing-region"] = region
    extra = config.get_iceberg_properties()
    if extra:
        properties.update(_parse_properties(extra))
    return properties


_AWS_ENDPOINT = re.compile(r"^https?://(?P<service>s3tables|glue)\.(?P<region>[a-z0-9-]+)\.amazonaws\.com(/|$)", re.I)


def aws_signing_name(catalog_url: str) -> Optional[str]:
    """``s3tables`` or ``glue`` for the AWS-hosted Iceberg REST endpoints, else ``None``."""
    match = _AWS_ENDPOINT.match(catalog_url or "")
    return match.group("service").lower() if match else None


def aws_region(catalog_url: str) -> Optional[str]:
    """The region in an AWS-hosted catalog endpoint, else ``None``."""
    match = _AWS_ENDPOINT.match(catalog_url or "")
    return match.group("region") if match else None


def _parse_properties(text: str) -> dict[str, str]:
    """Extra pyiceberg catalog properties: a JSON object, or ``key=value`` pairs separated by commas."""
    text = text.strip()
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            raise DataContractException(
                type="iceberg-connection",
                name="invalid_properties",
                reason=f"DATACONTRACT_ICEBERG_PROPERTIES is not valid JSON: {e}",
                engine="datacontract-cli",
            )
        return {str(k): str(v) for k, v in parsed.items()}
    pairs = (pair.partition("=") for pair in text.split(",") if pair.strip())
    return {key.strip(): value.strip() for key, _, value in pairs if key.strip()}


def load_iceberg_catalog(server: Server, config: Config | None = None) -> Catalog:
    """Open the server's REST catalog with pyiceberg."""
    try:
        from pyiceberg.catalog import load_catalog
    except ImportError as e:
        raise DataContractException(
            type="iceberg-connection",
            name="missing_dependency",
            reason=f"pyiceberg is required for Iceberg servers: pip install 'datacontract-cli[iceberg]' ({e})",
            engine="datacontract-cli",
        )
    config = Config.resolve(config)
    name = config.get_iceberg_catalog() or server.catalog or "default"
    return load_catalog(name, **catalog_properties(server, config))


def table_identifier(server: Server, table_name: str, config: Config | None = None) -> str:
    """``namespace.table`` for the catalog; a table name that already carries a namespace is kept."""
    config = Config.resolve(config)
    namespace = config.get_iceberg_namespace() or server.namespace
    if namespace and "." not in table_name:
        return f"{namespace}.{table_name}"
    return table_name


def load_iceberg_table(catalog: Catalog, server: Server, table_name: str, config: Config | None = None) -> Table:
    identifier = table_identifier(server, table_name, config)
    try:
        from pyiceberg.exceptions import NoSuchTableError
    except ImportError:  # pragma: no cover - pyiceberg is present when a catalog was loaded
        NoSuchTableError = Exception
    try:
        return catalog.load_table(identifier)
    except NoSuchTableError as e:
        raise DataContractException(
            type="iceberg-connection",
            name="missing_table",
            reason=f"Table '{identifier}' was not found in the Iceberg catalog: {e}",
            engine="datacontract-cli",
        )


def read_iceberg_tables(
    data_contract: OpenDataContractStandard,
    server: Server,
    run: Run,
    duckdb_connection: duckdb.DuckDBPyConnection | None = None,
    schema_name: str = "all",
    config: Config | None = None,
) -> duckdb.DuckDBPyConnection:
    """Register every schema object of the contract as a DuckDB view over the Iceberg table's Arrow data."""
    import duckdb

    con = duckdb_connection if duckdb_connection is not None else duckdb.connect(database=":memory:")
    catalog = load_iceberg_catalog(server, config)
    for schema_obj in data_contract.schema_ or []:
        if schema_name != "all" and schema_obj.name != schema_name:
            continue
        table_name = schema_obj.physicalName or schema_obj.name
        run.log_info(f"Reading Iceberg table {table_identifier(server, table_name, config)}")
        try:
            table = load_iceberg_table(catalog, server, table_name, config)
            arrow_table = table.scan().to_arrow()
        except DataContractException:
            raise
        except Exception as e:
            raise DataContractException(
                type="iceberg-connection",
                name="read_table",
                result=ResultEnum.failed,
                reason=f"Cannot read Iceberg table '{table_name}': {e}",
                engine="datacontract-cli",
            )
        con.register(schema_obj.name, arrow_table)
    return con
