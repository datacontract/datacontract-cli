import requests
from typer.testing import CliRunner

from datacontract.cli import app

runner = CliRunner()
_default_template_url = "https://datacontract.com/datacontract.init.yaml"
_custom_template_url = "https://studio.datacontract.com/s/ef47b7ea-879c-48d5-adf4-aa68b000b00f.yaml"


def test_download_datacontract_file_with_defaults(tmp_path):
    datacontract_test_path = tmp_path / "datacontract.yaml"
    runner.invoke(app, ["init", str(datacontract_test_path)])
    _compare_test_datacontract_with(str(datacontract_test_path), _default_template_url)


def test_download_datacontract_file_from_custom_url(tmp_path):
    datacontract_test_path = tmp_path / "datacontract.yaml"
    runner.invoke(app, ["init", str(datacontract_test_path), "--template", _custom_template_url])
    _compare_test_datacontract_with(str(datacontract_test_path), _custom_template_url)


def test_download_datacontract_file_file_exists(tmp_path):
    datacontract_test_path = tmp_path / "datacontract.yaml"
    # invoke twice to produce error
    runner.invoke(app, ["init", str(datacontract_test_path)])
    result = runner.invoke(app, ["init", str(datacontract_test_path), "--template", _custom_template_url])

    assert result.exit_code == 1
    assert "File already exists, use --overwrite to overwrite" in result.stdout
    _compare_test_datacontract_with(str(datacontract_test_path), _default_template_url)


def test_download_datacontract_file_overwrite_file(tmp_path):
    datacontract_test_path = tmp_path / "datacontract.yaml"
    runner.invoke(app, ["init", str(datacontract_test_path)])
    result = runner.invoke(
        app, ["init", str(datacontract_test_path), "--template", _custom_template_url, "--overwrite"]
    )

    assert result.exit_code == 0
    _compare_test_datacontract_with(str(datacontract_test_path), _custom_template_url)


def _compare_test_datacontract_with(datacontract_test_path, url: str):
    text = requests.get(url).text
    with open(datacontract_test_path, "r") as tmp:
        assert tmp.read().replace("\r", "") == text.replace("\r", "")
