"""Load the metadata of the objects in an S3 location as a table, one row per object.

An ``s3`` server with ``format: metadata`` stands for the
files themselves rather than the records inside them. The properties of its
schemas name object attributes (``size``, ``contentType``, ``lastModified``, ...), so once the
listing is a table, every check the contract can express runs on it unchanged:
``required``, types, enums, patterns, quality metrics, SQL rules, row filters,
and the freshness and retention service levels.
"""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import urlparse

from open_data_contract_standard.model import SchemaObject, Server

from datacontract.config import Config
from datacontract.engines.ibis.connections.aws_credentials import resolve_aws_credentials
from datacontract.model.exceptions import DataContractException

logger = logging.getLogger(__name__)

# Returned by ListObjectsV2 for every object: column -> (response key, duckdb type)
_LIST_COLUMNS = {
    "name": ("Key", "VARCHAR"),
    "size": ("Size", "BIGINT"),
    "lastModified": ("LastModified", "TIMESTAMPTZ"),
    "etag": ("ETag", "VARCHAR"),
    "storageClass": ("StorageClass", "VARCHAR"),
}

# Returned only by HeadObject, one request per object, so fetched only when a property asks for one
_HEAD_COLUMNS = {
    "contentType": ("ContentType", "VARCHAR"),
    "contentEncoding": ("ContentEncoding", "VARCHAR"),
    "contentLanguage": ("ContentLanguage", "VARCHAR"),
    "contentDisposition": ("ContentDisposition", "VARCHAR"),
    "cacheControl": ("CacheControl", "VARCHAR"),
    "serverSideEncryption": ("ServerSideEncryption", "VARCHAR"),
    "versionId": ("VersionId", "VARCHAR"),
}

_HEAD_WORKERS = 16


def list_object_metadata(
    server: Server, schema_obj: SchemaObject, location: str, config: Config
) -> tuple[dict[str, str], list[list[Any]]]:
    """The columns (name -> duckdb type) and rows of the metadata table: one row per object at ``location``."""
    bucket, pattern = _split_location(location)
    declared = {prop.name: prop for prop in schema_obj.properties or []}
    head_columns = {name: spec for name, spec in _HEAD_COLUMNS.items() if name in declared}
    columns = _LIST_COLUMNS | head_columns
    # User-defined metadata (x-amz-meta-*): a struct of the keys the contract declares, else a map of all of them
    metadata_keys = None
    if "metadata" in declared:
        metadata_keys = [p.name for p in declared["metadata"].properties or []]
        struct = ", ".join('"' + key.replace('"', '""') + '" VARCHAR' for key in metadata_keys)
        columns |= {"metadata": ("Metadata", f"STRUCT({struct})" if metadata_keys else "MAP(VARCHAR, VARCHAR)")}

    client = _s3_client(server, config)
    objects = _list_objects(client, bucket, pattern)
    if head_columns or metadata_keys is not None:
        with ThreadPoolExecutor(max_workers=_HEAD_WORKERS) as executor:
            heads = executor.map(lambda o: client.head_object(Bucket=bucket, Key=o["Key"]), objects)
            objects = [o | head for o, head in zip(objects, heads)]
    if metadata_keys:
        # S3 stores the keys in lower case
        objects = [o | {"Metadata": {k: o.get("Metadata", {}).get(k.lower()) for k in metadata_keys}} for o in objects]
    logger.info("Found %d object(s) at %s", len(objects), location)
    rows = [[o.get(response_key) for response_key, _ in columns.values()] for o in objects]
    return {name: duckdb_type for name, (_, duckdb_type) in columns.items()}, rows


def _split_location(location: str) -> tuple[str, str]:
    """The bucket and the key pattern of an ``s3://bucket/key-pattern`` location."""
    parsed = urlparse(location)
    if parsed.scheme not in ("s3", "s3a") or not parsed.netloc:
        raise DataContractException(
            type="schema",
            name="Check that the S3 location is valid",
            reason=f"Cannot list the objects of '{location}': expected s3://<bucket>/<prefix or glob>.",
            engine="datacontract-cli",
        )
    return parsed.netloc, parsed.path.lstrip("/")


def _s3_client(server: Server, config: Config):
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config as BotoConfig

    credentials = resolve_aws_credentials(config)
    boto_config = BotoConfig(
        # a public bucket needs no credentials, and signing with none would fail
        signature_version=UNSIGNED if credentials is None else None,
        # S3-compatible stores such as MinIO need path-style addressing
        s3={"addressing_style": "path"} if server.endpointUrl else None,
    )
    if credentials is None:
        return boto3.client("s3", region_name=server.region, endpoint_url=server.endpointUrl, config=boto_config)
    return boto3.client(
        "s3",
        region_name=credentials.region or server.region,
        endpoint_url=server.endpointUrl,
        aws_access_key_id=credentials.access_key_id,
        aws_secret_access_key=credentials.secret_access_key,
        aws_session_token=credentials.session_token,
        config=boto_config,
    )


def _list_objects(client, bucket: str, pattern: str) -> list[dict[str, Any]]:
    """The objects whose key matches ``pattern``: a glob, or else a prefix."""
    glob_start = min((i for i in (pattern.find(c) for c in "*?[") if i >= 0), default=-1)
    prefix = pattern if glob_start < 0 else pattern[:glob_start]
    matches = _glob_regex(pattern).fullmatch if glob_start >= 0 else None
    objects = []
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            # a key ending in a slash is a folder placeholder, not a file
            if key.endswith("/") or (matches is not None and not matches(key)):
                continue
            objects.append(obj)
    return objects


def _glob_regex(pattern: str) -> re.Pattern:
    """A glob as duckdb reads it: ``*`` and ``?`` stay within one path segment, ``**`` crosses them."""
    parts = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            parts.append(".*")
            i += 2
        elif pattern[i] == "*":
            parts.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            parts.append("[^/]")
            i += 1
        elif pattern[i] == "[" and "]" in pattern[i + 1 :]:
            end = pattern.index("]", i + 1)
            members = pattern[i + 1 : end].replace("\\", "\\\\")
            parts.append("[" + ("^" + members[1:] if members.startswith("!") else members) + "]")
            i = end + 1
        else:
            parts.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(parts))
