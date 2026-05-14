"""Azure Blob Storage / ADLS Gen2 metadata checks for schemas with physicalType='file'.

This engine validates file-level metadata exposed by Azure Blob Storage (or ADLS Gen2)
against the constraints declared in an ODCS v3.1 data contract:

  - ``lastModified`` is not in the future (no blob should have a future modification date).
  - ``contentLength`` does not exceed the declared maximum (default 5 MiB = 5,242,880 bytes;
    override with ``customProperties.maxContentLengthBytes`` on the schema object).
  - ``contentType`` of each blob matches the value declared in
    ``customProperties.contentType`` on the schema object.
  - The resolved ``location`` path contains at least one blob (non-empty folder check).
  - Quality constraints on the schema (``metric: rowCount`` or ``metric: itemCount``) are
    evaluated as a *file count* threshold.

Supported ``location`` URL formats (on the server block):
  - ``https://<account>.blob.core.windows.net/<container>/<prefix>``
  - ``abfss://<container>@<account>.dfs.core.windows.net/<prefix>``
  - ``abfs://<container>@<account>.dfs.core.windows.net/<prefix>``
  - ``wasbs://<container>@<account>.blob.core.windows.net/<prefix>``

Authentication (environment variables, evaluated in priority order):
  1. ``DATACONTRACT_AZURE_CONNECTION_STRING`` — full storage connection string.
  2. ``DATACONTRACT_AZURE_STORAGE_ACCOUNT_KEY`` — storage-account key
     (requires account name to be extractable from the URL).
  3. Service-principal OAuth2 (requires all three):
     ``DATACONTRACT_AZURE_TENANT_ID``, ``DATACONTRACT_AZURE_CLIENT_ID``,
     ``DATACONTRACT_AZURE_CLIENT_SECRET``.
  4. ``DefaultAzureCredential`` as a final fallback (picks up managed identity,
     Azure CLI login, workload identity, etc.).
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional, Tuple
from urllib.parse import urlparse

from open_data_contract_standard.model import DataQuality, OpenDataContractStandard, SchemaObject, Server

from datacontract.model.run import Check, ResultEnum, Run

if TYPE_CHECKING:
    from azure.storage.blob import BlobProperties, BlobServiceClient

logger = logging.getLogger(__name__)

# Default maximum blob size in bytes (5 MiB)
_DEFAULT_MAX_CONTENT_LENGTH_BYTES = 5 * 1024 * 1024  # 5,242,880

# Custom property keys (on SchemaObject.customProperties)
_CP_CONTENT_TYPE = "contentType"
_CP_MAX_BYTES = "maxContentLengthBytes"

# Quality metrics interpreted as file counts
_FILE_COUNT_METRICS = {"rowCount", "itemCount", "fileCount"}


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
            "abfss://<container>@<account>.dfs.core.windows.net/<prefix>.",
        )
        return

    run.log_info(
        f"Azure Blob File checks: container='{container_name}', prefix='{prefix}', "
        f"{len(file_schemas)} file schema(s)"
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

    # Resolve check configuration from schema customProperties
    expected_content_type = _get_custom_property(schema, _CP_CONTENT_TYPE)
    max_bytes_raw = _get_custom_property(schema, _CP_MAX_BYTES)
    max_bytes = int(max_bytes_raw) if max_bytes_raw is not None else _DEFAULT_MAX_CONTENT_LENGTH_BYTES

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

    # ── Check 1: location not empty ──────────────────────────────────────────
    _check_location_not_empty(run, schema_name, blobs, prefix)

    if not blobs:
        # No further per-blob checks make sense when the folder is empty
        return

    file_count = len(blobs)
    run.log_info(f"[{schema_name}] Found {file_count} blob(s) under prefix '{prefix}'")

    # ── Check 2: lastModified not in the future ───────────────────────────────
    _check_last_modified_not_future(run, schema_name, blobs)

    # ── Check 3: contentLength ≤ max ─────────────────────────────────────────
    _check_content_length(run, schema_name, blobs, max_bytes)

    # ── Check 4: contentType matches ─────────────────────────────────────────
    if expected_content_type:
        _check_content_type(run, schema_name, blobs, expected_content_type)

    # ── Check 5: quality file-count thresholds ───────────────────────────────
    if schema.quality:
        _check_file_count_quality(run, schema_name, schema.quality, file_count)


# ---------------------------------------------------------------------------
# Individual check implementations
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
            name=f"[{schema_name}] Azure Blob File — location not empty",
            model=schema_name,
            result=ResultEnum.passed,
            reason=f"Found {len(blobs)} blob(s) under prefix '{prefix}'.",
        )
    else:
        _append_check(
            run,
            check_type=check_type,
            category="schema",
            name=f"[{schema_name}] Azure Blob File — location not empty",
            model=schema_name,
            result=ResultEnum.failed,
            reason=f"No blobs found under prefix '{prefix}'. The location appears to be empty.",
        )


def _check_last_modified_not_future(
    run: Run,
    schema_name: str,
    blobs: list,
) -> None:
    check_type = "azure_file_last_modified_not_future"
    now = datetime.now(timezone.utc)
    future_blobs = []

    for blob in blobs:
        last_modified: Optional[datetime] = getattr(blob, "last_modified", None)
        if last_modified is None:
            continue
        # Ensure timezone-aware comparison
        if last_modified.tzinfo is None:
            last_modified = last_modified.replace(tzinfo=timezone.utc)
        if last_modified > now:
            future_blobs.append((blob.name, last_modified.isoformat()))

    if future_blobs:
        details = "; ".join(f"{name} ({ts})" for name, ts in future_blobs[:5])
        if len(future_blobs) > 5:
            details += f" … and {len(future_blobs) - 5} more"
        _append_check(
            run,
            check_type=check_type,
            category="schema",
            name=f"[{schema_name}] Azure Blob File — lastModified not in future",
            model=schema_name,
            result=ResultEnum.failed,
            reason=f"{len(future_blobs)} blob(s) have a lastModified date in the future.",
            details=details,
        )
    else:
        _append_check(
            run,
            check_type=check_type,
            category="schema",
            name=f"[{schema_name}] Azure Blob File — lastModified not in future",
            model=schema_name,
            result=ResultEnum.passed,
            reason=f"All {len(blobs)} blob(s) have a lastModified date in the past.",
        )


def _check_content_length(
    run: Run,
    schema_name: str,
    blobs: list,
    max_bytes: int,
) -> None:
    check_type = "azure_file_content_length"
    oversized = []

    for blob in blobs:
        size = getattr(blob, "size", None)
        if size is None:
            size = getattr(blob, "content_length", None)
        if size is None:
            continue
        if size > max_bytes:
            oversized.append((blob.name, size))

    max_mb = max_bytes / (1024 * 1024)
    if oversized:
        details = "; ".join(f"{name} ({sz:,} bytes)" for name, sz in oversized[:5])
        if len(oversized) > 5:
            details += f" … and {len(oversized) - 5} more"
        _append_check(
            run,
            check_type=check_type,
            category="schema",
            name=f"[{schema_name}] Azure Blob File — contentLength ≤ {max_mb:.1f} MiB",
            model=schema_name,
            result=ResultEnum.failed,
            reason=f"{len(oversized)} blob(s) exceed the maximum size of {max_bytes:,} bytes ({max_mb:.1f} MiB).",
            details=details,
        )
    else:
        _append_check(
            run,
            check_type=check_type,
            category="schema",
            name=f"[{schema_name}] Azure Blob File — contentLength ≤ {max_mb:.1f} MiB",
            model=schema_name,
            result=ResultEnum.passed,
            reason=f"All {len(blobs)} blob(s) are within the {max_bytes:,} bytes limit.",
        )


def _check_content_type(
    run: Run,
    schema_name: str,
    blobs: list,
    expected_content_type: str,
) -> None:
    check_type = "azure_file_content_type"
    mismatched = []

    for blob in blobs:
        content_settings = getattr(blob, "content_settings", None)
        actual_ct: Optional[str] = None
        if content_settings is not None:
            actual_ct = getattr(content_settings, "content_type", None)
        if actual_ct is None:
            # BlobProperties may expose content_type directly on newer SDK versions
            actual_ct = getattr(blob, "content_type", None)

        if actual_ct is None:
            mismatched.append((blob.name, "<not set>"))
            continue

        # Normalise: strip parameters (e.g. "application/json; charset=utf-8" → "application/json")
        actual_base = actual_ct.split(";")[0].strip().lower()
        expected_base = expected_content_type.split(";")[0].strip().lower()

        if actual_base != expected_base:
            mismatched.append((blob.name, actual_ct))

    if mismatched:
        details = "; ".join(f"{name} (got '{ct}')" for name, ct in mismatched[:5])
        if len(mismatched) > 5:
            details += f" … and {len(mismatched) - 5} more"
        _append_check(
            run,
            check_type=check_type,
            category="schema",
            name=f"[{schema_name}] Azure Blob File — contentType is '{expected_content_type}'",
            model=schema_name,
            result=ResultEnum.failed,
            reason=f"{len(mismatched)} blob(s) have an unexpected content-type (expected '{expected_content_type}').",
            details=details,
        )
    else:
        _append_check(
            run,
            check_type=check_type,
            category="schema",
            name=f"[{schema_name}] Azure Blob File — contentType is '{expected_content_type}'",
            model=schema_name,
            result=ResultEnum.passed,
            reason=f"All {len(blobs)} blob(s) have content-type '{expected_content_type}'.",
        )


def _check_file_count_quality(
    run: Run,
    schema_name: str,
    quality_list: List[DataQuality],
    file_count: int,
) -> None:
    """Evaluate ODCS quality thresholds that are interpreted as file-count constraints."""
    for quality in quality_list:
        metric = getattr(quality, "metric", None)
        if metric not in _FILE_COUNT_METRICS:
            continue

        check_type = "azure_file_count_quality"
        passed, reason = _evaluate_threshold(quality, file_count)
        threshold_desc = _describe_threshold(quality)
        name = f"[{schema_name}] Azure Blob File — {metric} {threshold_desc}"

        _append_check(
            run,
            check_type=check_type,
            category="quality",
            name=name,
            model=schema_name,
            result=ResultEnum.passed if passed else ResultEnum.failed,
            reason=reason,
        )


def _evaluate_threshold(quality: DataQuality, value: int) -> Tuple[bool, str]:
    """Return (passed, reason) for a quality threshold applied to a numeric value."""
    if quality.mustBe is not None:
        ok = value == quality.mustBe
        return ok, f"File count is {value}; expected exactly {quality.mustBe}."
    if quality.mustNotBe is not None:
        ok = value != quality.mustNotBe
        return ok, f"File count is {value}; must not be {quality.mustNotBe}."
    if quality.mustBeGreaterThan is not None:
        ok = value > quality.mustBeGreaterThan
        return ok, f"File count is {value}; must be > {quality.mustBeGreaterThan}."
    if quality.mustBeGreaterOrEqualTo is not None:
        ok = value >= quality.mustBeGreaterOrEqualTo
        return ok, f"File count is {value}; must be >= {quality.mustBeGreaterOrEqualTo}."
    if quality.mustBeLessThan is not None:
        ok = value < quality.mustBeLessThan
        return ok, f"File count is {value}; must be < {quality.mustBeLessThan}."
    if quality.mustBeLessOrEqualTo is not None:
        ok = value <= quality.mustBeLessOrEqualTo
        return ok, f"File count is {value}; must be <= {quality.mustBeLessOrEqualTo}."
    if quality.mustBeBetween is not None and len(quality.mustBeBetween) == 2:
        lo, hi = quality.mustBeBetween
        ok = lo <= value <= hi
        return ok, f"File count is {value}; must be between {lo} and {hi}."
    if quality.mustNotBeBetween is not None and len(quality.mustNotBeBetween) == 2:
        lo, hi = quality.mustNotBeBetween
        ok = not (lo <= value <= hi)
        return ok, f"File count is {value}; must not be between {lo} and {hi}."
    return True, f"File count is {value}; no threshold specified."


def _describe_threshold(quality: DataQuality) -> str:
    if quality.mustBe is not None:
        return f"= {quality.mustBe}"
    if quality.mustNotBe is not None:
        return f"!= {quality.mustNotBe}"
    if quality.mustBeGreaterThan is not None:
        return f"> {quality.mustBeGreaterThan}"
    if quality.mustBeGreaterOrEqualTo is not None:
        return f">= {quality.mustBeGreaterOrEqualTo}"
    if quality.mustBeLessThan is not None:
        return f"< {quality.mustBeLessThan}"
    if quality.mustBeLessOrEqualTo is not None:
        return f"<= {quality.mustBeLessOrEqualTo}"
    if quality.mustBeBetween is not None:
        return f"between {quality.mustBeBetween[0]} and {quality.mustBeBetween[1]}"
    return ""


# ---------------------------------------------------------------------------
# Azure connection helpers
# ---------------------------------------------------------------------------


def _build_blob_service_client(location: str) -> "BlobServiceClient":
    """Create a ``BlobServiceClient`` using available credentials."""
    try:
        from azure.storage.blob import BlobServiceClient
    except ImportError as exc:
        raise ImportError(
            "The 'azure-storage-blob' package is required for Azure Blob File checks. "
            "Install it with: pip install azure-storage-blob"
        ) from exc

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
            raise ImportError(
                "The 'azure-identity' package is required for service-principal authentication. "
                "Install it with: pip install azure-identity"
            ) from exc
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
        raise ImportError(
            "The 'azure-identity' package is required for DefaultAzureCredential authentication. "
            "Install it with: pip install azure-identity"
        ) from exc
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
    if parsed.scheme in ("wasbs", "wasb"):
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
    if parsed.scheme in ("wasbs", "wasb"):
        m = re.match(r"([^@]+)@", parsed.netloc)
        container = m.group(1) if m else None
        prefix = parsed.path.lstrip("/")
        return container or None, prefix

    return None, ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_custom_property(schema: SchemaObject, key: str) -> Optional[str]:
    if schema.customProperties is None:
        return None
    for cp in schema.customProperties:
        if cp.property == key:
            return str(cp.value) if cp.value is not None else None
    return None


def _append_check(
    run: Run,
    *,
    check_type: str,
    category: str,
    name: str,
    model: Optional[str],
    result: ResultEnum,
    reason: str,
    details: Optional[str] = None,
) -> None:
    run.checks.append(
        Check(
            id=str(uuid.uuid4()),
            key=f"{model or 'global'}__{check_type}",
            category=category,
            type=check_type,
            name=name,
            model=model,
            engine="datacontract",
            language="python",
            result=result,
            reason=reason,
            details=details,
        )
    )
