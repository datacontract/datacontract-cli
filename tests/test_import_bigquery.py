import logging
import os

from typer.testing import CliRunner
from pytest import skip

from datacontract.cli import app

logging.basicConfig(level=logging.DEBUG, force=True)

_service_account_path = ""
_full_table_id = ""
_billing_project_id = ""


def test_cli():
    if not _service_account_path or "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
        skip("Service account path not set")

    if _service_account_path:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _service_account_path

    if not _full_table_id:
        skip("Full table id not set")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "bigquery",
        ],
        input="%s" % _full_table_id,
    )
    assert result.exit_code == 0


def test_import_table():
    # TODO: Implement test
    skip("Not implemented yet")
