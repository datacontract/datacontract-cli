"""Create a data contract from files in object storage: S3, GCS or Azure.

The objects are read with duckdb through the same connection setup that
``datacontract test`` uses, so the import authenticates identically and infers
the column types from exactly the reader that will later verify them. One
importer serves all three: it takes the server type from the format it was
registered under.
"""

from __future__ import annotations

import re
from typing import Optional

from open_data_contract_standard.model import OpenDataContractStandard, Server

from datacontract.imports.csv_importer import map_type_from_duckdb
from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import create_odcs, create_property, create_schema_object, create_server
from datacontract.model.exceptions import DataContractException

# The formats the s3 server type can be tested against.
FORMATS_BY_SUFFIX = {
    ".json": "json",
    ".ndjson": "json",
    ".jsonl": "json",
    ".csv": "csv",
    ".parquet": "parquet",
}
SUPPORTED_FORMATS = {"json", "csv", "parquet", "delta"}

# The import format is the name a user types; the server type is what goes into
# the contract. They differ for ADLS, which ODCS calls `azure`, and for GCS,
# which ODCS has no server type for at all.
SERVER_TYPES = {"s3": "s3", "gcs": "s3", "adls": "azure"}

# GCS speaks the S3 protocol through its interoperability endpoint, so a GCS
# import writes an ODCS `s3` server pinned to that endpoint. Credentials are the
# bucket's HMAC key, supplied through the DATACONTRACT_S3_* variables.
GCS_ENDPOINT_URL = "https://storage.googleapis.com"
DEFAULT_ENDPOINT_URLS = {"gcs": GCS_ENDPOINT_URL}

_EXAMPLE_LOCATIONS = {
    "s3": "s3://my-bucket/orders/*.json",
    "azure": "abfss://my-container/orders/*.json",
}

_READERS = {
    "json": "read_json_auto('{location}', hive_partitioning=1)",
    "csv": "read_csv_auto('{location}', hive_partitioning=1)",
    "parquet": "read_parquet('{location}', hive_partitioning=1)",
    "delta": "delta_scan('{location}')",
}


class ObjectStorageImporter(Importer):
    def import_source(self, source: str, import_args: dict) -> OpenDataContractStandard:
        return import_object_storage(
            location=normalize_location(source, self.import_format),
            server_type=SERVER_TYPES[self.import_format],
            format=import_args.get("file_format"),
            delimiter=import_args.get("delimiter"),
            endpoint_url=import_args.get("endpoint_url") or DEFAULT_ENDPOINT_URLS.get(self.import_format),
        )


def import_object_storage(
    location: Optional[str],
    server_type: str = "s3",
    format: Optional[str] = None,
    delimiter: Optional[str] = None,
    endpoint_url: Optional[str] = None,
) -> OpenDataContractStandard:
    if not location:
        raise DataContractException(
            type="source",
            name=f"{server_type} import source",
            reason=(
                f"The location is required for the {server_type} import, "
                f"e.g. --source {_EXAMPLE_LOCATIONS[server_type]}"
            ),
            engine="datacontract",
        )

    format = (format or detect_format(location) or "").lower()
    if format not in SUPPORTED_FORMATS:
        raise DataContractException(
            type="source",
            name=f"{server_type} import format",
            reason=(
                f"Could not tell the format of '{location}'. "
                f"Pass --format with one of: {', '.join(sorted(SUPPORTED_FORMATS))}."
            ),
            engine="datacontract",
        )

    server = create_server(
        name="production",
        server_type=server_type,
        location=location,
        format=format,
    )
    if delimiter:
        server.delimiter = delimiter
    if endpoint_url:
        server.endpointUrl = endpoint_url

    columns = _read_columns(server, location, format)
    if not columns:
        raise DataContractException(
            type="schema",
            result="failed",
            name="no columns found",
            reason=f"No columns found at '{location}'.",
            engine="datacontract",
        )

    odcs = create_odcs()
    odcs.servers = [server]
    odcs.schema_ = [
        create_schema_object(
            name=schema_name(location),
            properties=[
                create_property(name=name, logical_type=map_type_from_duckdb(duckdb_type))
                for name, duckdb_type in columns
            ],
        )
    ]
    return odcs


def normalize_location(location: Optional[str], import_format: str) -> Optional[str]:
    """Rewrite a GCS location to the s3:// scheme duckdb's S3 reader expects."""
    if location and import_format == "gcs":
        for scheme in ("gs://", "gcs://"):
            if location.startswith(scheme):
                return "s3://" + location[len(scheme) :]
    return location


def detect_format(location: str) -> Optional[str]:
    """Derive the format from the object suffix; delta has none, so it needs --format."""
    match = re.search(r"(\.[A-Za-z0-9]+)(?:\?.*)?$", location)
    return FORMATS_BY_SUFFIX.get(match.group(1).lower()) if match else None


def schema_name(location: str) -> str:
    """Name the schema after the object, or after the prefix when the path is a glob."""
    segment = location.rstrip("/").rsplit("/", 1)[-1]
    if "*" in segment or "?" in segment or not segment:
        segment = location.rstrip("/").rsplit("/", 2)[-2] if "/" in location.rstrip("/") else segment
    segment = re.sub(r"\.[A-Za-z0-9]+$", "", segment)
    return re.sub(r"[^0-9A-Za-z_]+", "_", segment).strip("_") or "data"


def _read_columns(server: Server, location: str, format: str):
    from datacontract.engines.ibis.connections.duckdb_connection import (
        _import_duckdb,
        setup_azure_connection,
        setup_s3_connection,
    )

    setup = {"s3": setup_s3_connection, "azure": setup_azure_connection}[server.type]
    duckdb = _import_duckdb()
    con = duckdb.connect(database=":memory:")
    setup(con, server)
    if format == "delta":
        con.sql("update extensions;")
    reader = _READERS[format].format(location=location)
    try:
        return [(row[0], row[1]) for row in con.sql(f"DESCRIBE SELECT * FROM {reader};").fetchall()]
    except Exception as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="s3 read failed",
            reason=f"Could not read '{location}' as {format}: {e}",
            engine="datacontract",
            original_exception=e,
        )
    finally:
        con.close()
