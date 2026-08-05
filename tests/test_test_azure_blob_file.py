"""Unit tests for Azure Blob Storage / ADLS Gen2 metadata checks.

All Azure SDK calls are mocked with unittest.mock so no real Azure account is required.

Schema properties bind directly to BlobProperties attributes (azure.storage.blob):
  name, size, lastModified, contentType, blobType, etag, …
Each property's quality constraints are validated per-blob.
Schema-level quality (rowCount / itemCount / fileCount) is validated as a file count.
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
# Fixture path (relative to tests/ CWD)
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
    blob_type: str = "BlockBlob",
    etag: str = '"abc123"',
) -> MagicMock:
    """Create a mock BlobProperties object mirroring azure.storage.blob.BlobProperties."""
    if last_modified is None:
        last_modified = datetime.now(timezone.utc) - timedelta(hours=1)

    blob = MagicMock()
    blob.name = name
    blob.size = size
    blob.last_modified = last_modified
    blob.etag = etag

    # Simulate blob_type enum with .value
    bt = MagicMock()
    bt.value = blob_type
    blob.blob_type = bt

    cs = MagicMock()
    cs.content_type = content_type
    cs.content_encoding = None
    cs.content_language = None
    blob.content_settings = cs
    return blob


def _make_run() -> Run:
    return Run.create_run()


def _checks_by_type(run: Run, check_type: str) -> list:
    return [c for c in run.checks if c.type == check_type]


def _checks_by_field(run: Run, field: str) -> list:
    return [c for c in run.checks if c.field == field]


# ---------------------------------------------------------------------------
# Unit tests — URL parsing helpers
# ---------------------------------------------------------------------------


class TestParseLocation:
    def test_https_blob_url_with_prefix(self):
        container, prefix = _parse_location("https://myaccount.blob.core.windows.net/mycontainer/raw/orders/")
        assert container == "mycontainer"
        assert prefix == "raw/orders/"

    def test_https_blob_url_no_prefix(self):
        container, prefix = _parse_location("https://myaccount.blob.core.windows.net/mycontainer")
        assert container == "mycontainer"
        assert prefix == ""

    def test_abfss_url(self):
        container, prefix = _parse_location("abfss://mycontainer@myaccount.dfs.core.windows.net/raw/orders/")
        assert container == "mycontainer"
        assert prefix == "raw/orders/"

    def test_wasbs_url(self):
        container, prefix = _parse_location("wasbs://mycontainer@myaccount.blob.core.windows.net/raw/")
        assert container == "mycontainer"
        assert prefix == "raw/"

    def test_unknown_scheme_returns_none_container(self):
        container, _ = _parse_location("s3://bucket/key")
        assert container is None

    def test_abfs_url(self):
        container, prefix = _parse_location("abfs://mycontainer@myaccount.dfs.core.windows.net/path/to/data")
        assert container == "mycontainer"
        assert prefix == "path/to/data"


class TestAccountUrlFromLocation:
    def test_https_blob(self):
        url = _account_url_from_location("https://myaccount.blob.core.windows.net/mycontainer/raw/")
        assert url == "https://myaccount.blob.core.windows.net"

    def test_abfss(self):
        url = _account_url_from_location("abfss://mycontainer@myaccount.dfs.core.windows.net/path/")
        assert url == "https://myaccount.blob.core.windows.net"

    def test_wasbs(self):
        url = _account_url_from_location("wasbs://mycontainer@myaccount.blob.core.windows.net/raw/")
        assert url == "https://myaccount.blob.core.windows.net"


# ---------------------------------------------------------------------------
# Integration-style tests — mocked BlobServiceClient
# ---------------------------------------------------------------------------


def _patched_client(blobs: List[MagicMock]):
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
    """Property-driven per-blob checks with mocked BlobServiceClient."""

    def _run_with_blobs(self, blobs: List[MagicMock]) -> Run:
        data_contract = _load_contract()
        server = data_contract.servers[0]
        run = _make_run()
        with patch(
            "datacontract.engines.datacontract.check_azure_blob_file._build_blob_service_client",
            return_value=_patched_client(blobs),
        ):
            check_azure_blob_file(run, data_contract, server)
        return run

    # ── Property: size ──────────────────────────────────────────────────────

    def test_oversized_blob_fails_size_quality(self):
        blobs = [_make_blob("raw/orders/big.json", size=6 * 1024 * 1024)]
        run = self._run_with_blobs(blobs)
        checks = [c for c in _checks_by_type(run, "azure_file_property_quality") if c.field == "size"]
        assert checks and checks[0].result == ResultEnum.failed

    def test_exact_size_limit_passes(self):
        blobs = [_make_blob("raw/orders/exact.json", size=5 * 1024 * 1024)]
        run = self._run_with_blobs(blobs)
        checks = [c for c in _checks_by_type(run, "azure_file_property_quality") if c.field == "size"]
        assert checks and checks[0].result == ResultEnum.passed

    def test_small_blob_passes_size(self):
        blobs = [_make_blob("raw/orders/small.json", size=512)]
        run = self._run_with_blobs(blobs)
        checks = [c for c in _checks_by_type(run, "azure_file_property_quality") if c.field == "size"]
        assert checks and checks[0].result == ResultEnum.passed

    # ── Property: contentType (MIME normalisation) ──────────────────────────

    def test_wrong_content_type_fails(self):
        blobs = [_make_blob("raw/orders/file.csv", content_type="text/csv")]
        run = self._run_with_blobs(blobs)
        checks = [c for c in _checks_by_type(run, "azure_file_property_quality") if c.field == "contentType"]
        assert checks and checks[0].result == ResultEnum.failed

    def test_correct_content_type_passes(self):
        blobs = [_make_blob("raw/orders/file.json", content_type="application/json")]
        run = self._run_with_blobs(blobs)
        checks = [c for c in _checks_by_type(run, "azure_file_property_quality") if c.field == "contentType"]
        assert checks and checks[0].result == ResultEnum.passed

    def test_content_type_with_mime_params_passes(self):
        """'application/json; charset=utf-8' must match 'application/json'."""
        blobs = [_make_blob("raw/orders/file.json", content_type="application/json; charset=utf-8")]
        run = self._run_with_blobs(blobs)
        checks = [c for c in _checks_by_type(run, "azure_file_property_quality") if c.field == "contentType"]
        assert checks and checks[0].result == ResultEnum.passed

    def test_none_content_type_skipped_in_quality(self):
        """None contentType is skipped in quality checks; use required: true to catch missing."""
        blobs = [_make_blob("raw/orders/file.json", content_type=None)]
        run = self._run_with_blobs(blobs)
        checks = [c for c in _checks_by_type(run, "azure_file_property_quality") if c.field == "contentType"]
        # All values None → no violations → passes
        assert checks and checks[0].result == ResultEnum.passed

    # ── Property: required ──────────────────────────────────────────────────

    def test_all_required_properties_present_passes(self):
        blobs = [_make_blob("raw/orders/a.json")]
        run = self._run_with_blobs(blobs)
        failed = [c for c in _checks_by_type(run, "azure_file_property_required") if c.result == ResultEnum.failed]
        assert not failed, f"Unexpected required failures: {[(c.field, c.reason) for c in failed]}"

    def test_required_name_always_present(self):
        blobs = [_make_blob("raw/orders/a.json")]
        run = self._run_with_blobs(blobs)
        checks = [c for c in _checks_by_type(run, "azure_file_property_required") if c.field == "name"]
        assert checks and checks[0].result == ResultEnum.passed

    # ── Property: blobType ──────────────────────────────────────────────────

    def test_block_blob_type_passes(self):
        blobs = [_make_blob("raw/orders/a.json", blob_type="BlockBlob")]
        run = self._run_with_blobs(blobs)
        checks = [c for c in _checks_by_type(run, "azure_file_property_quality") if c.field == "blobType"]
        assert checks and checks[0].result == ResultEnum.passed

    def test_page_blob_type_fails(self):
        blobs = [_make_blob("raw/orders/a.json", blob_type="PageBlob")]
        run = self._run_with_blobs(blobs)
        checks = [c for c in _checks_by_type(run, "azure_file_property_quality") if c.field == "blobType"]
        assert checks and checks[0].result == ResultEnum.failed

    # ── Schema-level quality (file count) ──────────────────────────────────

    def test_quality_rowcount_passes_with_one_file(self):
        run = self._run_with_blobs([_make_blob("raw/orders/file1.json")])
        checks = _checks_by_type(run, "azure_file_count_quality")
        assert checks and checks[0].result == ResultEnum.passed

    def test_quality_rowcount_not_checked_on_empty_folder(self):
        """Quality count check is short-circuited when the folder is empty."""
        run = self._run_with_blobs([])
        assert not _checks_by_type(run, "azure_file_count_quality")

    # ── Multiple blobs — all passing ────────────────────────────────────────

    def test_multiple_blobs_all_passing(self):
        blobs = [
            _make_blob("raw/orders/a.json", size=1024),
            _make_blob("raw/orders/b.json", size=2048),
        ]
        run = self._run_with_blobs(blobs)
        failed = [c for c in run.checks if c.result in (ResultEnum.failed, ResultEnum.error)]
        assert not failed, f"Unexpected failures: {[(c.type, c.field, c.reason) for c in failed]}"

    def test_mixed_content_types_only_one_violation(self):
        blobs = [
            _make_blob("raw/orders/a.json", content_type="application/json"),
            _make_blob("raw/orders/b.csv", content_type="text/csv"),
        ]
        run = self._run_with_blobs(blobs)
        checks = [c for c in _checks_by_type(run, "azure_file_property_quality") if c.field == "contentType"]
        assert checks and checks[0].result == ResultEnum.failed
        assert "1 blob" in checks[0].reason

    # ── No file schemas → no checks ─────────────────────────────────────────

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

    # ── Missing location ────────────────────────────────────────────────────

    def test_missing_location_adds_config_error(self):
        from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, Server

        dc = OpenDataContractStandard()
        dc.servers = [Server(server="prod", type="azure")]
        dc.schema_ = [SchemaObject(name="files", logicalType="blob")]
        run = _make_run()
        check_azure_blob_file(run, dc, dc.servers[0])
        checks = _checks_by_type(run, "azure_blob_configuration")
        assert checks and checks[0].result == ResultEnum.failed

    # ── Connection error ────────────────────────────────────────────────────

    def test_connection_error_adds_error_check(self):
        from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, Server

        dc = OpenDataContractStandard()
        dc.servers = [Server(server="prod", type="azure", location="https://acct.blob.core.windows.net/c/")]
        dc.schema_ = [SchemaObject(name="files", logicalType="blob")]
        run = _make_run()
        with patch(
            "datacontract.engines.datacontract.check_azure_blob_file._build_blob_service_client",
            side_effect=Exception("auth failed"),
        ):
            check_azure_blob_file(run, dc, dc.servers[0])
        checks = _checks_by_type(run, "azure_blob_connection")
        assert checks and checks[0].result == ResultEnum.error


class TestEndToEndWiring:
    def test_blob_checks_run_through_data_contract_test(self):
        from datacontract.data_contract import DataContract

        blobs = [_make_blob("raw/orders/a.json", size=1024)]
        with patch(
            "datacontract.engines.datacontract.check_azure_blob_file._build_blob_service_client",
            return_value=_patched_client(blobs),
        ):
            run = DataContract(data_contract_file=FIXTURE_PATH).test()

        azure_checks = [c for c in run.checks if str(c.type).startswith("azure_")]
        assert azure_checks, "check_azure_blob_file was not wired into DataContract.test()"
        assert all(c.result == ResultEnum.passed for c in azure_checks), [
            (c.type, c.field, c.result, c.reason) for c in azure_checks
        ]

        # the SQL engine must not generate checks for a blob schema
        ibis_checks = [c for c in run.checks if c.engine == "ibis"]
        assert not ibis_checks, [(c.type, c.field) for c in ibis_checks]
        assert run.result == ResultEnum.passed, [
            (c.type, c.name, c.result, c.reason) for c in run.checks if c.result != ResultEnum.passed
        ]


class TestDimensionFilter:
    """`--dimension` also selects the Azure blob quality checks."""

    def _run_with_dimensions(self, dimensions: set[str] | None) -> Run:
        data_contract = _load_contract()
        schema = data_contract.schema_[0]
        # The fixture declares no dimensions; tag two rules so the filter has
        # something to select on.
        schema.quality[0].dimension = "coverage"
        size_prop = next(p for p in schema.properties if p.name == "size")
        size_prop.quality[0].dimension = "conformity"

        run = _make_run()
        with patch(
            "datacontract.engines.datacontract.check_azure_blob_file._build_blob_service_client",
            return_value=_patched_client([_make_blob("raw/orders/a.json", size=1024)]),
        ):
            check_azure_blob_file(run, data_contract, data_contract.servers[0], dimensions=dimensions)
        return run

    def test_author_dimension_selects_only_that_rule(self):
        """`coverage` is declared by the file-count rule alone."""
        run = self._run_with_dimensions({"coverage"})
        assert [c.type for c in run.checks] == ["azure_file_count_quality"]

    def test_selects_only_the_matching_property_rule(self):
        run = self._run_with_dimensions({"conformity"})
        assert [c.type for c in run.checks] == ["azure_file_property_quality"]
        assert run.checks[0].field == "size"

    def test_required_checks_map_to_completeness(self):
        run = self._run_with_dimensions({"completeness"})
        assert _checks_by_type(run, "azure_file_property_required")
        assert all(c.type == "azure_file_property_required" for c in run.checks)

    def test_rules_without_a_dimension_are_never_selected(self):
        """The contentType/blobType quality rules declare none, so nothing selects them."""
        for dimension in ("accuracy", "completeness", "conformity", "coverage", "timeliness", "uniqueness"):
            run = self._run_with_dimensions({dimension})
            undimensioned = [
                c
                for c in run.checks
                if c.type == "azure_file_property_quality" and c.field in ("contentType", "blobType")
            ]
            assert not undimensioned, dimension

    def test_no_filter_still_runs_everything(self):
        run = self._run_with_dimensions(None)
        assert _checks_by_type(run, "azure_file_property_required")
        assert _checks_by_type(run, "azure_file_count_quality")


class TestQualityIdAndTagFilter:
    """`--quality-id` and `--tag` also select the Azure blob quality checks."""

    def _run(self, **kwargs) -> Run:
        data_contract = _load_contract()
        schema = data_contract.schema_[0]
        # The fixture identifies no rules; identify two so the filters have
        # something to select on.
        schema.quality[0].id = "enough_files"
        schema.quality[0].tags = ["critical"]
        size_prop = next(p for p in schema.properties if p.name == "size")
        size_prop.quality[0].id = "file_size"
        size_prop.quality[0].tags = ["critical", "cheap"]

        run = _make_run()
        with patch(
            "datacontract.engines.datacontract.check_azure_blob_file._build_blob_service_client",
            return_value=_patched_client([_make_blob("raw/orders/a.json", size=1024)]),
        ):
            check_azure_blob_file(run, data_contract, data_contract.servers[0], **kwargs)
        return run

    def test_quality_id_selects_a_single_rule(self):
        run = self._run(quality_ids={"enough_files"})
        assert [c.type for c in run.checks] == ["azure_file_count_quality"]
        assert run.checks[0].qualityId == "enough_files"

    def test_tag_selects_every_rule_carrying_it(self):
        run = self._run(tags={"critical"})
        assert sorted(c.type for c in run.checks) == ["azure_file_count_quality", "azure_file_property_quality"]

    def test_tag_excludes_the_rules_without_it(self):
        run = self._run(tags={"cheap"})
        assert [c.type for c in run.checks] == ["azure_file_property_quality"]
        assert run.checks[0].field == "size"
        assert run.checks[0].tags == ["critical", "cheap"]
