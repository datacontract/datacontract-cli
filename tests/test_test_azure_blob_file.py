"""Unit tests for Azure Blob Storage / ADLS Gen2 metadata checks.

All Azure SDK calls are mocked with unittest.mock so no real Azure account is required.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from unittest.mock import MagicMock, patch

from datacontract.engines.datacontract.check_azure_blob_file import (
    _account_url_from_location,
    _parse_location,
    check_azure_blob_file,
)
from datacontract.model.run import ResultEnum, Run

# ---------------------------------------------------------------------------
# Fixture path (relative to tests/ CWD or absolute)
# ---------------------------------------------------------------------------

FIXTURE_PATH = "fixtures/azure-blob-file/datacontract.yaml"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_blob(
    name: str,
    size: int = 1024,
    last_modified: Optional[datetime] = None,
    content_type: Optional[str] = "application/json",
) -> MagicMock:
    """Create a mock BlobProperties object."""
    if last_modified is None:
        last_modified = datetime.now(timezone.utc) - timedelta(hours=1)
    blob = MagicMock()
    blob.name = name
    blob.size = size
    blob.last_modified = last_modified
    cs = MagicMock()
    cs.content_type = content_type
    blob.content_settings = cs
    return blob


def _make_run() -> Run:
    return Run.create_run()


def _check_results(run: Run) -> dict[str, ResultEnum]:
    """Return {check_type: result} mapping for all checks in the run."""
    return {c.type: c.result for c in run.checks}


def _checks_by_type(run: Run, check_type: str) -> list:
    return [c for c in run.checks if c.type == check_type]


# ---------------------------------------------------------------------------
# Unit tests for URL parsing helpers
# ---------------------------------------------------------------------------


class TestParseLocation:
    def test_https_blob_url_with_prefix(self):
        container, prefix = _parse_location(
            "https://myaccount.blob.core.windows.net/mycontainer/raw/orders/"
        )
        assert container == "mycontainer"
        assert prefix == "raw/orders/"

    def test_https_blob_url_no_prefix(self):
        container, prefix = _parse_location(
            "https://myaccount.blob.core.windows.net/mycontainer"
        )
        assert container == "mycontainer"
        assert prefix == ""

    def test_abfss_url(self):
        container, prefix = _parse_location(
            "abfss://mycontainer@myaccount.dfs.core.windows.net/raw/orders/"
        )
        assert container == "mycontainer"
        assert prefix == "raw/orders/"

    def test_wasbs_url(self):
        container, prefix = _parse_location(
            "wasbs://mycontainer@myaccount.blob.core.windows.net/raw/"
        )
        assert container == "mycontainer"
        assert prefix == "raw/"

    def test_unknown_scheme_returns_none_container(self):
        container, prefix = _parse_location("s3://bucket/key")
        assert container is None

    def test_abfs_url(self):
        container, prefix = _parse_location(
            "abfs://mycontainer@myaccount.dfs.core.windows.net/path/to/data"
        )
        assert container == "mycontainer"
        assert prefix == "path/to/data"


class TestAccountUrlFromLocation:
    def test_https_blob(self):
        url = _account_url_from_location(
            "https://myaccount.blob.core.windows.net/mycontainer/raw/"
        )
        assert url == "https://myaccount.blob.core.windows.net"

    def test_abfss(self):
        url = _account_url_from_location(
            "abfss://mycontainer@myaccount.dfs.core.windows.net/path/"
        )
        assert url == "https://myaccount.blob.core.windows.net"

    def test_wasbs(self):
        url = _account_url_from_location(
            "wasbs://mycontainer@myaccount.blob.core.windows.net/raw/"
        )
        assert url == "https://myaccount.blob.core.windows.net"


# ---------------------------------------------------------------------------
# Integration-style tests using mocked BlobServiceClient
# ---------------------------------------------------------------------------


def _patched_client(blobs: List[MagicMock]):
    """Return a MagicMock BlobServiceClient whose list_blobs returns *blobs*."""
    container_client = MagicMock()
    container_client.list_blobs.return_value = blobs

    service_client = MagicMock()
    service_client.get_container_client.return_value = container_client

    return service_client


def _load_contract():
    from datacontract.data_contract import DataContract

    dc = DataContract(data_contract_file=FIXTURE_PATH)
    return dc.get_data_contract()


class TestCheckAzureBlobFile:
    """Tests for check_azure_blob_file() with a mocked BlobServiceClient."""

    def _run_with_blobs(self, blobs: List[MagicMock]) -> Run:
        data_contract = _load_contract()
        server = data_contract.servers[0] if data_contract.servers else None
        run = _make_run()
        with patch(
            "datacontract.engines.datacontract.check_azure_blob_file._build_blob_service_client",
            return_value=_patched_client(blobs),
        ):
            check_azure_blob_file(run, data_contract, server)
        return run

    # ── Location not empty ──────────────────────────────────────────────────

    def test_empty_location_fails(self):
        run = self._run_with_blobs([])
        checks = _checks_by_type(run, "azure_file_location_not_empty")
        assert checks, "Expected location-not-empty check"
        assert checks[0].result == ResultEnum.failed

    def test_non_empty_location_passes(self):
        run = self._run_with_blobs([_make_blob("raw/orders/orders_2024.json")])
        checks = _checks_by_type(run, "azure_file_location_not_empty")
        assert checks[0].result == ResultEnum.passed

    # ── lastModified not in the future ──────────────────────────────────────

    def test_future_last_modified_fails(self):
        future = datetime.now(timezone.utc) + timedelta(days=1)
        blobs = [_make_blob("raw/orders/future.json", last_modified=future)]
        run = self._run_with_blobs(blobs)
        checks = _checks_by_type(run, "azure_file_last_modified_not_future")
        assert checks[0].result == ResultEnum.failed
        assert "future" in checks[0].reason.lower()

    def test_past_last_modified_passes(self):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        blobs = [_make_blob("raw/orders/old.json", last_modified=past)]
        run = self._run_with_blobs(blobs)
        checks = _checks_by_type(run, "azure_file_last_modified_not_future")
        assert checks[0].result == ResultEnum.passed

    def test_naive_datetime_treated_as_utc(self):
        """A timezone-naive datetime slightly in the past should pass."""
        past_naive = datetime.now() - timedelta(hours=2)
        blobs = [_make_blob("raw/orders/naive.json", last_modified=past_naive)]
        run = self._run_with_blobs(blobs)
        checks = _checks_by_type(run, "azure_file_last_modified_not_future")
        assert checks[0].result == ResultEnum.passed

    # ── Content length ──────────────────────────────────────────────────────

    def test_oversized_blob_fails(self):
        big = 6 * 1024 * 1024  # 6 MiB > 5 MiB default
        blobs = [_make_blob("raw/orders/big.json", size=big)]
        run = self._run_with_blobs(blobs)
        checks = _checks_by_type(run, "azure_file_content_length")
        assert checks[0].result == ResultEnum.failed

    def test_blob_exactly_at_limit_passes(self):
        exact = 5 * 1024 * 1024  # exactly 5 MiB
        blobs = [_make_blob("raw/orders/exact.json", size=exact)]
        run = self._run_with_blobs(blobs)
        checks = _checks_by_type(run, "azure_file_content_length")
        assert checks[0].result == ResultEnum.passed

    def test_small_blob_passes_content_length(self):
        blobs = [_make_blob("raw/orders/small.json", size=512)]
        run = self._run_with_blobs(blobs)
        checks = _checks_by_type(run, "azure_file_content_length")
        assert checks[0].result == ResultEnum.passed

    # ── Content type ────────────────────────────────────────────────────────

    def test_wrong_content_type_fails(self):
        blobs = [_make_blob("raw/orders/file.csv", content_type="text/csv")]
        run = self._run_with_blobs(blobs)
        checks = _checks_by_type(run, "azure_file_content_type")
        assert checks[0].result == ResultEnum.failed

    def test_correct_content_type_passes(self):
        blobs = [_make_blob("raw/orders/file.json", content_type="application/json")]
        run = self._run_with_blobs(blobs)
        checks = _checks_by_type(run, "azure_file_content_type")
        assert checks[0].result == ResultEnum.passed

    def test_content_type_with_params_passes(self):
        """'application/json; charset=utf-8' should match 'application/json'."""
        blobs = [_make_blob("raw/orders/file.json", content_type="application/json; charset=utf-8")]
        run = self._run_with_blobs(blobs)
        checks = _checks_by_type(run, "azure_file_content_type")
        assert checks[0].result == ResultEnum.passed

    def test_none_content_type_fails(self):
        blobs = [_make_blob("raw/orders/file.json", content_type=None)]
        run = self._run_with_blobs(blobs)
        checks = _checks_by_type(run, "azure_file_content_type")
        assert checks[0].result == ResultEnum.failed

    # ── Quality file-count thresholds ───────────────────────────────────────

    def test_quality_rowcount_passes_when_at_least_one_file(self):
        # Fixture specifies mustBeGreaterOrEqualTo: 1
        blobs = [_make_blob("raw/orders/file1.json")]
        run = self._run_with_blobs(blobs)
        quality_checks = _checks_by_type(run, "azure_file_count_quality")
        assert quality_checks, "Expected quality check"
        assert quality_checks[0].result == ResultEnum.passed

    def test_quality_rowcount_fails_on_empty(self):
        run = self._run_with_blobs([])
        # Empty folder triggers location check + no further checks → no quality check
        quality_checks = _checks_by_type(run, "azure_file_count_quality")
        # Quality check is NOT run when folder is empty (short-circuit after location check)
        assert not quality_checks

    # ── Multiple blobs with mixed issues ───────────────────────────────────

    def test_multiple_blobs_all_passing(self):
        blobs = [
            _make_blob("raw/orders/a.json", size=1024),
            _make_blob("raw/orders/b.json", size=2048),
        ]
        run = self._run_with_blobs(blobs)
        results = _check_results(run)
        assert results.get("azure_file_location_not_empty") == ResultEnum.passed
        assert results.get("azure_file_last_modified_not_future") == ResultEnum.passed
        assert results.get("azure_file_content_length") == ResultEnum.passed
        assert results.get("azure_file_content_type") == ResultEnum.passed
        assert results.get("azure_file_count_quality") == ResultEnum.passed

    def test_mixed_content_types_reports_only_mismatched(self):
        blobs = [
            _make_blob("raw/orders/a.json", content_type="application/json"),
            _make_blob("raw/orders/b.csv", content_type="text/csv"),
        ]
        run = self._run_with_blobs(blobs)
        checks = _checks_by_type(run, "azure_file_content_type")
        assert checks[0].result == ResultEnum.failed
        assert "1 blob" in checks[0].reason  # only 1 mismatch

    # ── No file schemas → no checks added ──────────────────────────────────

    def test_no_file_schemas_produces_no_checks(self):
        from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, Server

        dc = OpenDataContractStandard()
        dc.servers = [Server(server="prod", type="azure", location="https://acct.blob.core.windows.net/c/p/")]
        dc.schema_ = [SchemaObject(name="my_table", physicalType="table")]
        run = _make_run()
        with patch(
            "datacontract.engines.datacontract.check_azure_blob_file._build_blob_service_client",
        ) as mock_build:
            check_azure_blob_file(run, dc, dc.servers[0])
            mock_build.assert_not_called()
        assert not run.checks

    # ── Missing location → configuration check ──────────────────────────────

    def test_missing_location_adds_config_error(self):
        from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, Server

        dc = OpenDataContractStandard()
        dc.servers = [Server(server="prod", type="azure")]
        dc.schema_ = [SchemaObject(name="files", physicalType="file")]
        run = _make_run()
        check_azure_blob_file(run, dc, dc.servers[0])
        config_checks = _checks_by_type(run, "azure_file_configuration")
        assert config_checks, "Expected configuration error check"
        assert config_checks[0].result == ResultEnum.failed

    # ── Connection error ────────────────────────────────────────────────────

    def test_connection_error_adds_error_check(self):
        from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, Server

        dc = OpenDataContractStandard()
        dc.servers = [Server(server="prod", type="azure", location="https://acct.blob.core.windows.net/c/")]
        dc.schema_ = [SchemaObject(name="files", physicalType="file")]
        run = _make_run()
        with patch(
            "datacontract.engines.datacontract.check_azure_blob_file._build_blob_service_client",
            side_effect=Exception("auth failed"),
        ):
            check_azure_blob_file(run, dc, dc.servers[0])
        conn_checks = _checks_by_type(run, "azure_file_connection")
        assert conn_checks
        assert conn_checks[0].result == ResultEnum.error
