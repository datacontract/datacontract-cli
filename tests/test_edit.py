from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.command_edit import BUNDLED_EDITOR_ASSETS_DIR, create_app, resolve_editor_assets_url

YAML_CONTENT = """apiVersion: v3.1.0
kind: DataContract
id: orders
name: Orders
version: 1.0.0
status: active
"""


@pytest.fixture
def contract_file(tmp_path) -> Path:
    file_path = tmp_path / "datacontract.yaml"
    file_path.write_text(YAML_CONTENT, encoding="utf-8")
    return file_path


@pytest.fixture
def client(contract_file) -> TestClient:
    return TestClient(create_app(contract_file))


def test_edit_offers_to_initialize_a_missing_file(tmp_path):
    runner = CliRunner()
    file_path = tmp_path / "new.yaml"
    with patch("uvicorn.run") as mock_run:
        result = runner.invoke(app, ["edit", str(file_path), "--no-open"], input="y\n")
    assert result.exit_code == 0
    # the file is initialized with the init template before the editor starts
    assert "apiVersion" in file_path.read_text(encoding="utf-8")
    mock_run.assert_called_once()


def test_edit_aborts_when_initialization_is_declined(tmp_path):
    runner = CliRunner()
    file_path = tmp_path / "missing.yaml"
    result = runner.invoke(app, ["edit", str(file_path), "--no-open"], input="n\n")
    assert result.exit_code == 1
    assert "datacontract init" in result.output
    assert not file_path.exists()


def test_index_serves_editor_page(client, contract_file):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    # assets must be loaded same-origin (proxied), otherwise Monaco workers fail
    assert "/editor/datacontract-editor.es.js" in response.text
    assert "/editor/datacontract-editor.css" in response.text
    assert f"/api/files/{contract_file.name}" in response.text
    # the editor's test runner must point back to this server
    assert "dataContractCliApiServerUrl: window.location.origin" in response.text
    # saving must give feedback via the editor's toast notifications
    assert "addNotification" in response.text
    assert "type: 'success'" in response.text
    assert "type: 'error'" in response.text


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_config(client, contract_file):
    response = client.get("/api/config")
    assert response.status_code == 200
    assert response.json() == {
        "mode": "CLI",
        "filename": contract_file.name,
        "filepath": str(contract_file),
    }


def test_read_file(client):
    response = client.get("/api/files/datacontract.yaml")
    assert response.status_code == 200
    assert "text/yaml" in response.headers["content-type"]
    assert response.text == YAML_CONTENT


def test_write_file(client, contract_file):
    updated = YAML_CONTENT.replace("version: 1.0.0", "version: 1.1.0")
    response = client.put(
        "/api/files/datacontract.yaml",
        content=updated,
        headers={"Content-Type": "text/yaml"},
    )
    assert response.status_code == 200
    assert response.json() == {"success": True, "filename": "datacontract.yaml"}
    assert contract_file.read_text(encoding="utf-8") == updated


def test_read_other_file_is_forbidden(client):
    response = client.get("/api/files/other.yaml")
    assert response.status_code == 403


def test_write_other_file_is_forbidden(client, contract_file):
    response = client.put("/api/files/other.yaml", content="malicious")
    assert response.status_code == 403
    assert contract_file.read_text(encoding="utf-8") == YAML_CONTENT


def test_test_endpoint_is_available(client):
    # the edit server doubles as the editor's test runner
    response = client.post("/test", content="invalid: [yaml", headers={"Content-Type": "text/plain"})
    assert response.status_code == 200
    assert response.json()["result"] == "failed"


def test_editor_assets_are_proxied_and_cached(contract_file):
    upstream_response = MagicMock()
    upstream_response.status_code = 200
    upstream_response.content = b"console.log('editor');"
    upstream_response.headers = {"content-type": "application/javascript; charset=utf-8"}

    client = TestClient(create_app(contract_file, editor_assets_url="https://example.com/editor/dist/"))
    with patch("requests.get", return_value=upstream_response) as mock_get:
        response = client.get("/editor/datacontract-editor.es.js")
        assert response.status_code == 200
        assert response.content == b"console.log('editor');"
        assert "application/javascript" in response.headers["content-type"]
        mock_get.assert_called_once_with("https://example.com/editor/dist/datacontract-editor.es.js", timeout=30)

        # second request is served from the cache
        response = client.get("/editor/datacontract-editor.es.js")
        assert response.status_code == 200
        assert mock_get.call_count == 1


def test_resolve_editor_assets_url():
    # no version and no URL means the bundled assets are used
    assert resolve_editor_assets_url(None, None) is None
    assert resolve_editor_assets_url("latest", None) == "https://cdn.jsdelivr.net/npm/datacontract-editor@latest/dist"
    assert resolve_editor_assets_url("0.1.9", None) == "https://cdn.jsdelivr.net/npm/datacontract-editor@0.1.9/dist"
    # an explicit assets URL takes precedence over the version
    assert resolve_editor_assets_url("0.1.9", "https://example.com/editor/dist") == "https://example.com/editor/dist"


def test_bundled_editor_assets_are_shipped_with_the_package():
    # the editor must work offline, without loading anything from a CDN
    assert (BUNDLED_EDITOR_ASSETS_DIR / "datacontract-editor.es.js").is_file()
    assert (BUNDLED_EDITOR_ASSETS_DIR / "datacontract-editor.css").is_file()


def test_editor_assets_are_served_from_bundled_files_without_network(contract_file):
    client = TestClient(create_app(contract_file))
    with patch("requests.get") as mock_get:
        response = client.get("/editor/datacontract-editor.es.js")
        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"]
        response = client.get("/editor/datacontract-editor.css")
        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]
        mock_get.assert_not_called()


def test_missing_local_editor_asset_returns_404(contract_file, tmp_path):
    client = TestClient(create_app(contract_file, editor_assets_dir=tmp_path))
    response = client.get("/editor/does-not-exist.js")
    assert response.status_code == 404


def test_editor_assets_path_traversal_is_rejected(contract_file):
    client = TestClient(create_app(contract_file))
    with patch("requests.get") as mock_get:
        response = client.get("/editor/..%2f..%2fsecrets.txt")
        assert response.status_code == 404
        mock_get.assert_not_called()
