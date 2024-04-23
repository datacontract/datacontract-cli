import logging
from os import environ
from string import Template

from typer.testing import CliRunner

from datacontract.cli import app
from pytest import skip

runner = CliRunner()

logging.basicConfig(level=logging.DEBUG, force=True)

# Set the following environment variables to run the tests
_GOOGLE_CLOUD_PROJECT_ID = None
_GOOGLE_CLOUD_BUCKET_NAME = None or "datacontract"
DATACONTRACT_STORAGE__STORAGE_OPTIONS = Template('{"project_id": "$PROJECT", "bucket_name": "$BUCKET"}')


def test_init():
    if environ.get("GOOGLE_APPLICATION_CREDENTIALS") is None:
        skip("Google Cloud service account path is not provided")
    environ["DATACONTRACT_STORAGE__STORAGE_OPTIONS"] = DATACONTRACT_STORAGE__STORAGE_OPTIONS.substitute(
        PROJECT=_GOOGLE_CLOUD_PROJECT_ID, BUCKET=_GOOGLE_CLOUD_BUCKET_NAME
    )
    environ["DATACONTRACT_STORAGE__STORAGE_CLASS"] = "google_cloud"
    result = runner.invoke(app, ["init", "--overwrite"])
    assert result.exit_code == 0


def test_file_does_not_exist():
    if environ.get("GOOGLE_APPLICATION_CREDENTIALS") is None:
        skip("Google Cloud service account path is not provided")
    environ["DATACONTRACT_STORAGE__STORAGE_OPTIONS"] = DATACONTRACT_STORAGE__STORAGE_OPTIONS.substitute(
        PROJECT=_GOOGLE_CLOUD_PROJECT_ID, BUCKET=_GOOGLE_CLOUD_BUCKET_NAME
    )
    environ["DATACONTRACT_STORAGE__STORAGE_CLASS"] = "google_cloud"
    result = runner.invoke(app, ["test", "unknown.yaml"])
    assert result.exit_code == 1
    assert "The file 'unknown.yaml' does not exist." in result.stdout
