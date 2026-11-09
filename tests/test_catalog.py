import os
from pathlib import PosixPath

from typer.testing import CliRunner

from datacontract.catalog.catalog import create_data_contract_page, create_index_md
from datacontract.cli import app

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli(tmp_path: PosixPath):
    runner = CliRunner()
    result = runner.invoke(app, ["catalog", "--files", "fixtures/catalog/*.yaml", "--output", tmp_path])
    assert result.exit_code == 0
    assert os.path.exists(tmp_path / "index.html")
    assert os.path.exists(tmp_path / "fixtures/catalog/datacontract-1.html")
    assert os.path.exists(tmp_path / "fixtures/catalog/datacontract-2.odcs.html")


def test_with_tags(tmp_path: PosixPath):
    runner = CliRunner()
    result = runner.invoke(
        app, ["catalog", "--files", "fixtures/catalog/datacontract-3.tags.yaml", "--output", tmp_path]
    )
    assert result.exit_code == 0
    assert os.path.exists(tmp_path / "index.html")

    with open(tmp_path / "index.html") as index:
        content = index.read()
        # naive assertion which only checks that it appears anywhere in the document
        assert "tag expected-tag" in content
        assert 'data-tag="expected-tag"' in content


def test_markdown_format(tmp_path: PosixPath):
    runner = CliRunner()
    result = runner.invoke(
        app, ["catalog", "--files", "fixtures/catalog/*.yaml", "--format", "markdown", "--output", tmp_path]
    )
    assert result.exit_code == 0
    assert not os.path.exists(tmp_path / "index.html")
    assert os.path.exists(tmp_path / "fixtures/catalog/datacontract-1.md")
    assert os.path.exists(tmp_path / "fixtures/catalog/datacontract-2.odcs.md")

    with open(tmp_path / "index.md") as index:
        content = index.read()
    assert "| Data Contract | Version | Owner | Description |" in content
    assert "(fixtures/catalog/datacontract-1.md)" in content
    assert "(fixtures/catalog/datacontract-2.odcs.md)" in content


def test_markdown_format_with_mermaid(tmp_path: PosixPath):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "catalog",
            "--files",
            "fixtures/catalog/datacontract-1.yaml",
            "--format",
            "markdown",
            "--mermaid",
            "--output",
            tmp_path,
        ],
    )
    assert result.exit_code == 0
    with open(tmp_path / "fixtures/catalog/datacontract-1.md") as page:
        assert "```mermaid" in page.read()


def test_mermaid_requires_markdown(tmp_path: PosixPath):
    runner = CliRunner()
    result = runner.invoke(app, ["catalog", "--files", "fixtures/catalog/*.yaml", "--mermaid", "--output", tmp_path])
    assert result.exit_code != 0


def test_markdown_index_escapes_the_title_of_the_link(tmp_path: PosixPath):
    contract = tmp_path / "contracts" / "orders.yaml"
    contract.parent.mkdir()
    contract.write_text(
        "apiVersion: v3.1.0\nkind: DataContract\nid: orders\nname: 'Orders [v2] \\ draft'\nversion: 1.0.0\nstatus: active\n"
        "schema:\n  - name: orders\n    properties:\n      - name: id\n        logicalType: string\n"
    )
    contracts = []
    create_data_contract_page(contracts, contract, tmp_path, None, "markdown")
    create_index_md(contracts, tmp_path)

    assert "[Orders \\[v2\\] \\\\ draft](" in (tmp_path / "index.md").read_text()
