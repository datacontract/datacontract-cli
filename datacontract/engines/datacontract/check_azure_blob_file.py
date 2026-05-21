from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from open_data_contract_standard.model import (
    DataQuality,
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
)

from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Check, ResultEnum, Run

if TYPE_CHECKING:
    from azure.storage.blob import BlobProperties, BlobServiceClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# BlobProperties extractor registry
# Maps ODCS property name (camelCase) → callable(BlobProperties) → value
# ---------------------------------------------------------------------------

_BLOB_EXTRACTORS: Dict[str, Callable[["BlobProperties"], Any]] = {
    "name": lambda b: b.name,
    "size": lambda b: b.size,
    "lastModified": lambda b: _as_utc(b.last_modified),
    "creationTime": lambda b: _as_utc(b.creation_time),
    "lastAccessedOn": lambda b: _as_utc(b.last_accessed_on),
    "contentType": lambda b: _cs(b, "content_type"),
    "contentEncoding": lambda b: _cs(b, "content_encoding"),
    "contentLanguage": lambda b: _cs(b, "content_language"),
    "contentDisposition": lambda b: _cs(b, "content_disposition"),
    "cacheControl": lambda b: _cs(b, "cache_control"),
    "contentMd5": lambda b: _cs(b, "content_md5"),
    "etag": lambda b: b.etag,
    "blobType": lambda b: _enum_value(b.blob_type),
    "blobTier": lambda b: _enum_value(b.blob_tier),
    "archiveStatus": lambda b: b.archive_status,
    "serverEncrypted": lambda b: b.server_encrypted,
    "deleted": lambda b: b.deleted,
    "snapshotId": lambda b: b.snapshot,
    "versionId": lambda b: b.version_id,
    "tagCount": lambda b: b.tag_count,
}

# Quality metrics on SchemaObject interpreted as file-count thresholds
_FILE_COUNT_METRICS = {"rowCount"}

# Properties whose values are datetimes — auto-checked "not in future" when declared
_DATETIME_PROPS = {"lastModified", "creationTime", "lastAccessedOn"}

# Property names where MIME parameter stripping is applied before comparison
_MIMETYPE_PROPS = {"contentType"}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def check_azure_blob_file(
    run: Run,
    data_contract: OpenDataContractStandard,
    server: Server,
) -> None:
    """Run Azure Blob Storage metadata checks for all file-physicalType schemas.

    Only schemas with ``physicalType == "file"`` are processed; others are skipped.
    No exception is raised if the server is not Azure or if no file schemas exist —
    the function simply returns without adding checks.
    """
    if data_contract.schema_ is None:
        return

    file_schemas = [s for s in data_contract.schema_ if (s.physicalType or "").lower() == "file"]
    if not file_schemas:
        return

    location = server.location if server else None
    if not location:
        _append_check(
            run,
            check_type="azure_file_configuration",
            category="schema",
            name="Azure Blob File — server location",
            model=None,
            result=ResultEnum.failed,
            reason="Server block has no 'location' property. Cannot resolve container and prefix.",
        )
        return

    try:
        blob_service_client = _build_blob_service_client(location)
    except Exception as exc:
        _append_check(
            run,
            check_type="azure_file_connection",
            category="schema",
            name="Azure Blob File — connection",
            model=None,
            result=ResultEnum.error,
            reason=f"Could not connect to Azure Blob Storage: {exc}",
        )
        return

    container_name, prefix = _parse_location(location)
    if container_name is None:
        _append_check(
            run,
            check_type="azure_file_configuration",
            category="schema",
            name="Azure Blob File — location parse",
            model=None,
            result=ResultEnum.failed,
            reason=f"Could not extract container name from location '{location}'. "
            "Supported formats: https://<account>.blob.core.windows.net/<container>/<prefix>, "
            "abfss://<container>@<account>.dfs.core.windows.net/<prefix>, "
            "azure://<container>@<account>.blob.core.windows.net/<prefix>, "
            "wasbs://<container>@<account>.blob.core.windows.net/<prefix>.",
        )
        return

    run.log_info(
        f"Azure Blob File checks: container='{container_name}', prefix='{prefix}', {len(file_schemas)} file schema(s)"
    )

    for schema in file_schemas:
        _check_schema(run, schema, blob_service_client, container_name, prefix)


# ---------------------------------------------------------------------------
# Per-schema checks
# ---------------------------------------------------------------------------


def _check_schema(
    run: Run,
    schema: SchemaObject,
    blob_service_client: "BlobServiceClient",
    container_name: str,
    prefix: str,
) -> None:
    schema_name = schema.name or "unknown"

    # List all blobs under the resolved prefix for this schema
    try:
        container_client = blob_service_client.get_container_client(container_name)
        blobs: List["BlobProperties"] = list(container_client.list_blobs(name_starts_with=prefix or None))
    except Exception as exc:
        _append_check(
            run,
            check_type="azure_file_list",
            category="schema",
            name=f"[{schema_name}] Azure Blob File — list blobs",
            model=schema_name,
            result=ResultEnum.error,
            reason=f"Failed to list blobs in container '{container_name}' with prefix '{prefix}': {exc}",
        )
        return

    # ── Check: location not empty ─────────────────────────────────────────────
    _check_location_not_empty(run, schema_name, blobs, prefix)

    if not blobs:
        return

    file_count = len(blobs)
    run.log_info(f"[{schema_name}] Found {file_count} blob(s) under prefix '{prefix}'")

    # ── Per-property checks (driven by schema.properties) ────────────────────
    if schema.properties:
        for prop in schema.properties:
            _check_property(run, schema_name, prop, blobs)

    # ── Quality file-count thresholds on the schema object ───────────────────
    if schema.quality:
        _check_file_count_quality(run, schema_name, schema.quality, file_count)


# ---------------------------------------------------------------------------
# Per-property checks
# ---------------------------------------------------------------------------


def _check_property(
    run: Run,
    schema_name: str,
    prop: SchemaProperty,
    blobs: List["BlobProperties"],
) -> None:
    """Run required + quality checks for one declared schema property across all blobs."""
    prop_name = prop.name
    extractor = _BLOB_EXTRACTORS.get(prop_name)

    if extractor is None:
        run.log_warn(f"[{schema_name}] No BlobProperties extractor for property '{prop_name}' — skipped")
        return

    # ── required check ────────────────────────────────────────────────────────
    if prop.required:
        missing = [b.name for b in blobs if extractor(b) is None]
        if missing:
            _append_check(
                run,
                check_type="azure_file_property_required",
                category="schema",
                name=f"Check schema[{schema_name}].properties[{prop_name}] is required",
                model=schema_name,
                field=prop_name,
                result=ResultEnum.failed,
                reason=f"{len(missing)} blob(s) have no value for '{prop_name}'.",
                details="; ".join(missing[:5]) + (" …" if len(missing) > 5 else ""),
            )
        else:
            _append_check(
                run,
                check_type="azure_file_property_required",
                category="schema",
                name=f"Check schema[{schema_name}].properties[{prop_name}] is required",
                model=schema_name,
                field=prop_name,
                result=ResultEnum.passed,
                reason=f"All {len(blobs)} blob(s) have a value for '{prop_name}'.",
            )

    # ── quality constraints ────────────────────────────────────────────────────
    if not prop.quality:
        return

    for quality in prop.quality:
        violations: List[Tuple[str, str]] = []  # (blob.name, human-readable reason)

        for blob in blobs:
            value = extractor(blob)
            if value is None:
                # Skip None values in quality checks; use required: true to catch missing.
                continue
            passed, reason = _evaluate_quality_constraint(quality, value, prop_name)
            if not passed:
                violations.append((blob.name, reason))

        constraint_desc = _describe_quality_constraint(quality)
        check_name = f"Check schema[{schema_name}].properties[{prop_name}] has {constraint_desc}"

        if violations:
            details = "; ".join(f"{name}: {r}" for name, r in violations[:5])
            if len(violations) > 5:
                details += f" … and {len(violations) - 5} more"
            _append_check(
                run,
                check_type="azure_file_property_quality",
                category="quality",
                name=check_name,
                model=schema_name,
                field=prop_name,
                result=ResultEnum.failed,
                reason=f"{len(violations)} blob(s) violate '{prop_name} {constraint_desc}'.",
                details=details,
            )
        else:
            _append_check(
                run,
                check_type="azure_file_property_quality",
                category="quality",
                name=check_name,
                model=schema_name,
                field=prop_name,
                result=ResultEnum.passed,
                reason=f"All {len(blobs)} blob(s) satisfy '{prop_name} {constraint_desc}'.",
            )


# ---------------------------------------------------------------------------
# Quality constraint evaluation
# ---------------------------------------------------------------------------


def _evaluate_quality_constraint(quality: DataQuality, value: Any, prop_name: str) -> Tuple[bool, str]:
    """Evaluate a single quality constraint against *value* for one blob.

    Returns ``(passed, human-readable reason)``.
    """

    def _normalize(v: Any) -> Any:
        """Strip MIME parameters from content-type strings."""
        if prop_name in _MIMETYPE_PROPS and isinstance(v, str):
            return v.split(";")[0].strip().lower()
        return v

    norm_value = _normalize(value)

    if quality.mustBe is not None:
        expected = _normalize(quality.mustBe)
        return norm_value == expected, f"value is {value!r}; expected {quality.mustBe!r}"

    if quality.mustNotBe is not None:
        expected = _normalize(quality.mustNotBe)
        return norm_value != expected, f"value is {value!r}; must not be {quality.mustNotBe!r}"

    if quality.mustBeGreaterThan is not None:
        threshold = quality.mustBeGreaterThan
        try:
            return value > threshold, f"value is {value!r}; must be > {threshold!r}"
        except TypeError:
            return False, f"Cannot compare {value!r} > {threshold!r}"

    if quality.mustBeGreaterOrEqualTo is not None:
        threshold = quality.mustBeGreaterOrEqualTo
        try:
            return value >= threshold, f"value is {value!r}; must be >= {threshold!r}"
        except TypeError:
            return False, f"Cannot compare {value!r} >= {threshold!r}"

    if quality.mustBeLessThan is not None:
        threshold = quality.mustBeLessThan
        try:
            return value < threshold, f"value is {value!r}; must be < {threshold!r}"
        except TypeError:
            return False, f"Cannot compare {value!r} < {threshold!r}"

    if quality.mustBeLessOrEqualTo is not None:
        threshold = quality.mustBeLessOrEqualTo
        try:
            return value <= threshold, f"value is {value!r}; must be <= {threshold!r}"
        except TypeError:
            return False, f"Cannot compare {value!r} <= {threshold!r}"

    if quality.mustBeBetween is not None and len(quality.mustBeBetween) == 2:
        lo, hi = quality.mustBeBetween[0], quality.mustBeBetween[1]
        try:
            return lo <= value <= hi, f"value is {value!r}; must be between {lo!r} and {hi!r}"
        except TypeError:
            return False, f"Cannot compare {lo!r} <= {value!r} <= {hi!r}"

    if quality.mustNotBeBetween is not None and len(quality.mustNotBeBetween) == 2:
        lo, hi = quality.mustNotBeBetween[0], quality.mustNotBeBetween[1]
        try:
            return not (lo <= value <= hi), f"value is {value!r}; must not be between {lo!r} and {hi!r}"
        except TypeError:
            return False, f"Cannot compare {lo!r} <= {value!r} <= {hi!r}"

    return True, f"value is {value!r}; no threshold specified"


def _describe_quality_constraint(quality: DataQuality) -> str:
    """Return a short human-readable description of a quality constraint."""
    if quality.mustBe is not None:
        return f"= {quality.mustBe!r}"
    if quality.mustNotBe is not None:
        return f"!= {quality.mustNotBe!r}"
    if quality.mustBeGreaterThan is not None:
        return f"> {quality.mustBeGreaterThan!r}"
    if quality.mustBeGreaterOrEqualTo is not None:
        return f">= {quality.mustBeGreaterOrEqualTo!r}"
    if quality.mustBeLessThan is not None:
        return f"< {quality.mustBeLessThan!r}"
    if quality.mustBeLessOrEqualTo is not None:
        return f"<= {quality.mustBeLessOrEqualTo!r}"
    if quality.mustBeBetween is not None:
        return f"between {quality.mustBeBetween[0]!r} and {quality.mustBeBetween[1]!r}"
    if quality.mustNotBeBetween is not None:
        return f"not between {quality.mustNotBeBetween[0]!r} and {quality.mustNotBeBetween[1]!r}"
    return "(no constraint)"


# ---------------------------------------------------------------------------
# Location-not-empty check  (schema-level, not property-level)
# ---------------------------------------------------------------------------


def _check_location_not_empty(
    run: Run,
    schema_name: str,
    blobs: list,
    prefix: str,
) -> None:
    check_type = "azure_file_location_not_empty"
    if blobs:
        _append_check(
            run,
            check_type=check_type,
            category="schema",
            name=f"Check schema[{schema_name}] has a location not empty",
            model=schema_name,
            result=ResultEnum.passed,
            reason=f"Found {len(blobs)} blob(s) under prefix '{prefix}'.",
        )
    else:
        _append_check(
            run,
            check_type=check_type,
            category="schema",
            name=f"Check schema[{schema_name}] has a location not empty",
            model=schema_name,
            result=ResultEnum.failed,
            reason=f"No blobs found under prefix '{prefix}'. The location appears to be empty.",
        )


def _check_file_count_quality(
    run: Run,
    schema_name: str,
    quality_list: List[DataQuality],
    file_count: int,
) -> None:
    """Evaluate schema-level quality thresholds interpreted as file-count constraints."""
    for quality in quality_list:
        if getattr(quality, "metric", None) not in _FILE_COUNT_METRICS:
            continue
        passed, reason = _evaluate_quality_constraint(quality, file_count, "fileCount")
        constraint_desc = _describe_quality_constraint(quality)
        _append_check(
            run,
            check_type="azure_file_count_quality",
            category="quality",
            name=f"Check schema[{schema_name}] has {quality.metric} {constraint_desc}",
            model=schema_name,
            result=ResultEnum.passed if passed else ResultEnum.failed,
            reason=reason,
        )


# ---------------------------------------------------------------------------
# Azure connection helpers
# ---------------------------------------------------------------------------


def _build_blob_service_client(location: str) -> "BlobServiceClient":
    """Create a ``BlobServiceClient`` using available credentials."""
    try:
        from azure.storage.blob import BlobServiceClient
    except ImportError as exc:
        raise DataContractException(
            type="schema",
            result="failed",
            name="azure-storage extra missing",
            reason="Install the extra datacontract-cli[azure] to use azure",
            engine="datacontract",
            original_exception=exc,
        )

    # 1. Connection string
    conn_str = os.getenv("DATACONTRACT_AZURE_CONNECTION_STRING")
    if conn_str:
        return BlobServiceClient.from_connection_string(conn_str)

    # Derive account_url from location
    account_url = _account_url_from_location(location)

    # 2. Storage account key
    account_key = os.getenv("DATACONTRACT_AZURE_STORAGE_ACCOUNT_KEY")
    if account_key and account_url:
        return BlobServiceClient(account_url=account_url, credential=account_key)

    # 3. Service principal
    tenant_id = os.getenv("DATACONTRACT_AZURE_TENANT_ID")
    client_id = os.getenv("DATACONTRACT_AZURE_CLIENT_ID")
    client_secret = os.getenv("DATACONTRACT_AZURE_CLIENT_SECRET")
    if tenant_id and client_id and client_secret:
        try:
            from azure.identity import ClientSecretCredential
        except ImportError as exc:
            raise DataContractException(
                type="schema",
                result="failed",
                name="azure-identity extra missing",
                reason="Install the extra datacontract-cli[azure] to use azure",
                engine="datacontract",
                original_exception=exc,
            )
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )
        return BlobServiceClient(account_url=account_url, credential=credential)

    # 4. DefaultAzureCredential (managed identity, CLI, workload identity, …)
    try:
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:
        raise DataContractException(
            type="schema",
            result="failed",
            name="azure-identity extra missing",
            reason="Install the extra datacontract-cli[azure] to use azure",
            engine="datacontract",
            original_exception=exc,
        )
    return BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())


def _account_url_from_location(location: str) -> str:
    """Derive the BlobServiceClient account URL from a storage location string."""
    parsed = urlparse(location)

    # https://<account>.blob.core.windows.net/<container>/...
    if parsed.scheme in ("https", "http") and ".blob.core.windows.net" in parsed.netloc:
        return f"https://{parsed.netloc}"

    # abfss://<container>@<account>.dfs.core.windows.net/<path>
    if parsed.scheme in ("abfss", "abfs"):
        m = re.match(r"[^@]+@(.+)", parsed.netloc)
        if m:
            dfs_host = m.group(1)
            account = dfs_host.split(".")[0]
            return f"https://{account}.blob.core.windows.net"

    # wasbs://<container>@<account>.blob.core.windows.net/<path>
    if parsed.scheme in ("wasbs", "wasb", "azure"):
        m = re.match(r"[^@]+@(.+)", parsed.netloc)
        if m:
            return f"https://{m.group(1)}"

    # Fallback: return the bare location as-is and let the SDK handle it
    return location


def _parse_location(location: str) -> Tuple[Optional[str], str]:
    """Return ``(container_name, blob_prefix)`` from a storage location string.

    Returns ``(None, "")`` when the container name cannot be determined.
    """
    parsed = urlparse(location)

    # https://<account>.blob.core.windows.net/<container>/<prefix...>
    if parsed.scheme in ("https", "http") and ".blob.core.windows.net" in parsed.netloc:
        path_parts = parsed.path.lstrip("/").split("/", 1)
        container = path_parts[0] if path_parts else None
        prefix = path_parts[1] if len(path_parts) > 1 else ""
        return container or None, prefix

    # abfss://<container>@<account>.dfs.core.windows.net/<prefix>
    if parsed.scheme in ("abfss", "abfs"):
        m = re.match(r"([^@]+)@", parsed.netloc)
        container = m.group(1) if m else None
        prefix = parsed.path.lstrip("/")
        return container or None, prefix

    # wasbs://<container>@<account>.blob.core.windows.net/<prefix>
    if parsed.scheme in ("wasbs", "wasb", "azure"):
        m = re.match(r"([^@]+)@", parsed.netloc)
        container = m.group(1) if m else None
        prefix = parsed.path.lstrip("/")
        return container or None, prefix

    return None, ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Return *dt* as a timezone-aware UTC datetime, or ``None``."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _cs(blob: "BlobProperties", attr: str) -> Optional[str]:
    """Extract an attribute from ``blob.content_settings`` safely."""
    cs = getattr(blob, "content_settings", None)
    return getattr(cs, attr, None) if cs is not None else None


def _enum_value(v: Any) -> Optional[str]:
    """Return the ``.value`` of an enum, or ``str(v)``, or ``None``."""
    if v is None:
        return None
    return v.value if hasattr(v, "value") else str(v)


def _append_check(
    run: Run,
    *,
    check_type: str,
    category: str,
    name: str,
    model: Optional[str],
    result: ResultEnum,
    reason: str,
    field: Optional[str] = None,
    details: Optional[str] = None,
) -> None:
    run.checks.append(
        Check(
            id=str(uuid.uuid4()),
            key=f"{model or 'global'}__{field}__{check_type}",
            category=category,
            type=check_type,
            name=name,
            model=model,
            field=field,
            engine="datacontract",
            language="python",
            result=result,
            reason=reason,
            details=details,
        )
    )
