"""Create a data contract from files in an S3 bucket.

The objects are read with duckdb through the same connection setup that
``datacontract test`` uses, so the import authenticates identically and infers
the column types from exactly the reader that will later verify them.
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

_READERS = {
    "json": "read_json_auto('{location}', hive_partitioning=1)",
    "csv": "read_csv_auto('{location}', hive_partitioning=1)",
    "parquet": "read_parquet('{location}', hive_partitioning=1)",
    "delta": "delta_scan('{location}')",
}


class S3Importer(Importer):
    def import_source(self, source: str, import_args: dict) -> OpenDataContractStandard:
        return import_s3(
            location=source,
            format=import_args.get("s3_format"),
            delimiter=import_args.get("delimiter"),
            endpoint_url=import_args.get("endpoint_url"),
        )


def import_s3(
    location: Optional[str],
    format: Optional[str] = None,
    delimiter: Optional[str] = None,
    endpoint_url: Optional[str] = None,
) -> OpenDataContractStandard:
    if not location:
        raise DataContractException(
            type="source",
            name="s3 import source",
            reason="The S3 location is required for the s3 import, e.g. --source s3://my-bucket/orders/*.json",
            engine="datacontract",
        )

    format = (format or detect_format(location) or "").lower()
    if format not in SUPPORTED_FORMATS:
        raise DataContractException(
            type="source",
            name="s3 import format",
            reason=(
                f"Could not tell the format of '{location}'. "
                f"Pass --format with one of: {', '.join(sorted(SUPPORTED_FORMATS))}."
            ),
            engine="datacontract",
        )

    server = create_server(
        name="production",
        server_type="s3",
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
    from datacontract.engines.ibis.connections.duckdb_connection import _import_duckdb, setup_s3_connection

    duckdb = _import_duckdb()
    con = duckdb.connect(database=":memory:")
    setup_s3_connection(con, server)
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
