from pathlib import Path

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "./fixtures/custom/export/datacontract.yaml",
            "--format",
            "custom",
            "--template",
            "./fixtures/custom/export/template.sql",
            "--schema-name",
            "line_items",
        ],
    )
    assert result.exit_code == 0


# --------------------------------------------------------------------------------------------------------
# test simple template.sql
# --------------------------------------------------------------------------------------------------------
def test_export_custom_schema_name():
    """test ol' datacontract.yaml with simple template.sql"""
    path_fixtures = Path("fixtures/custom/export_model")

    data_contract = DataContract(data_contract_file=str(path_fixtures / "datacontract.yaml"))
    template = path_fixtures / "template.sql"

    result = data_contract.export(export_format="custom", schema_name="line_items", template=template)

    with open(path_fixtures / "expected.sql", "r") as file:
        assert result == file.read()


def test_export_odcs_custom_schema_name():
    """test ODCS datacontract.odcs.yaml with staging template.sql"""
    path_fixtures = Path("fixtures/custom/export_model")

    data_contract = DataContract(data_contract_file=str(path_fixtures / "datacontract.odcs.yaml"))
    template = path_fixtures / "template.sql"

    result = data_contract.export(export_format="custom", schema_name="users", template=template)

    with open(path_fixtures / "expected_odcs_users.sql", "r") as file:
        assert result == file.read()


# --------------------------------------------------------------------------------------------------------
# test staging template_stg.sql
# --------------------------------------------------------------------------------------------------------


def test_export_custom_schema_name_stg():
    """test ol' datacontract.yaml with simple template.sql"""
    path_fixtures = Path("fixtures/custom/export_model")

    data_contract = DataContract(data_contract_file=str(path_fixtures / "datacontract.yaml"))
    template = path_fixtures / "template_stg.sql"

    result = data_contract.export(export_format="custom", schema_name="line_items", template=template)
    print(result)

    with open(path_fixtures / "expected_stg.sql", "r") as file:
        assert result == file.read()


def test_export_odcs_custom_schema_name_stg():
    """test ODCS datacontract.odcs.yaml with staging template_stg.sql"""
    path_fixtures = Path("fixtures/custom/export_model")

    data_contract = DataContract(data_contract_file=str(path_fixtures / "datacontract.odcs.yaml"))
    template = path_fixtures / "template_stg.sql"

    result = data_contract.export(export_format="custom", schema_name="users", template=template)
    print(result)

    with open(path_fixtures / "expected_odcs_stg_users.sql", "r") as file:
        assert result == file.read()
