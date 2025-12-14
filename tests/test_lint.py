from open_data_contract_standard.model import OpenDataContractStandard
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.INFO, force=True)

runner = CliRunner()


def test_lint_valid_data_contract():
    data_contract_file = "fixtures/lint/valid_datacontract.yaml"
    data_contract = DataContract(data_contract_file=data_contract_file)

    run = data_contract.lint()
    assert run.result == "passed"


def test_lint_cli_valid():
    data_contract_file = "fixtures/lint/valid_datacontract.yaml"
    expected_output = "🟢 data contract is valid. Run 1 checks."

    result = runner.invoke(app, ["lint", data_contract_file])

    assert result.exit_code == 0
    assert expected_output in result.stdout


def test_lint_custom_schema():
    data_contract_file = "fixtures/lint/custom_datacontract.yaml"
    schema_file = "fixtures/lint/custom_datacontract.schema.json"
    data_contract = DataContract(data_contract_file=data_contract_file, schema_location=schema_file)

    run = data_contract.lint()

    assert run.result == "passed"


def test_lint_valid_odcs_schema():
    data_contract_file = "fixtures/lint/valid.odcs.yaml"
    data_contract = DataContract(data_contract_file=data_contract_file)

    run = data_contract.lint()

    assert run.result == "passed"


def test_lint_invalid_odcs_schema():
    data_contract_file = "fixtures/lint/invalid.odcs.yaml"
    data_contract = DataContract(data_contract_file=data_contract_file)

    run = data_contract.lint()

    assert run.result == "failed"


def test_lint_valid_odcs_3_1_0_schema():
    data_contract_file = "fixtures/lint/valid-3.1.0.odcs.yaml"
    data_contract = DataContract(data_contract_file=data_contract_file)

    run = data_contract.lint()
    print(run.pretty())

    assert run.result == "passed"


def test_lint_with_ref():
    data_contract = DataContract(
        data_contract_file="fixtures/lint/valid_datacontract_ref.yaml", inline_definitions=True
    )

    run = data_contract.lint()
    OpenDataContractStandard.model_validate(data_contract.get_data_contract())

    assert run.result == "passed"


def test_lint_with_references():
    data_contract = DataContract(data_contract_file="fixtures/lint/valid_datacontract_references.yaml")

    run = data_contract.lint()

    assert run.result == "passed"
