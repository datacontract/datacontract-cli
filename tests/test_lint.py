from unittest.mock import MagicMock, patch

from open_data_contract_standard.model import OpenDataContractStandard
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.config import Config
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


def test_lint_extra_top_level_field_rejected_without_custom_schema():
    """Without --json-schema, extra top-level fields must fail (default ODCS is strict)."""
    data_contract_file = "fixtures/lint/odcs_with_extra_top_level.yaml"
    data_contract = DataContract(data_contract_file=data_contract_file)

    run = data_contract.lint()

    assert run.result == "failed"


def test_lint_extra_top_level_field_allowed_with_custom_schema():
    """With --json-schema, the custom schema is the source of truth and the
    Pydantic step must accept extra top-level fields it allows."""
    data_contract_file = "fixtures/lint/odcs_with_extra_top_level.yaml"
    schema_file = "fixtures/lint/odcs_with_extra_top_level.schema.json"
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


def test_lint_invalid_odcs_schema_multiple_errors():
    data_contract_file = "fixtures/lint/invalid_multiple_schema_errors.odcs.yaml"
    result = runner.invoke(app, ["lint", data_contract_file])

    assert result.exit_code == 1
    assert "data.schema.no_description_schema.description must be " in result.stdout


def test_lint_invalid_odcs_schema_all_errors_api():
    data_contract_file = "fixtures/lint/invalid_multiple_errors.odcs.yaml"
    data_contract = DataContract(data_contract_file=data_contract_file, all_errors=True)

    run = data_contract.lint()

    assert run.result == "failed"
    assert len(run.checks) > 1
    assert all(check.result == "failed" for check in run.checks)


def test_lint_cli_invalid_odcs_schema_all_errors():
    data_contract_file = "fixtures/lint/invalid_multiple_errors.odcs.yaml"
    result = runner.invoke(app, ["lint", data_contract_file, "--all-errors"])

    assert result.exit_code == 1
    assert "found the following errors" in result.stdout
    assert "1)" in result.stdout
    assert "2)" in result.stdout


def test_lint_valid_odcs_3_1_0_schema():
    data_contract_file = "fixtures/lint/valid-3.1.0.odcs.yaml"
    data_contract = DataContract(data_contract_file=data_contract_file)

    run = data_contract.lint()
    print(run.pretty())

    assert run.result == "passed"


def test_lint_valid_odcs_3_2_0_schema():
    data_contract_file = "fixtures/lint/valid-3.2.0.odcs.yaml"
    data_contract = DataContract(data_contract_file=data_contract_file)

    run = data_contract.lint()
    print(run.pretty())

    assert run.result == "passed"


def test_lint_with_ref():
    data_contract = DataContract(data_contract_file="fixtures/lint/valid_datacontract_ref.yaml", inline_references=True)

    run = data_contract.lint()
    OpenDataContractStandard.model_validate(data_contract.get_data_contract())

    assert run.result == "passed"


def test_lint_with_references():
    data_contract = DataContract(data_contract_file="fixtures/lint/valid_datacontract_references.yaml")

    run = data_contract.lint()

    assert run.result == "passed"


def _mock_s3_client_returning(yaml_bytes: bytes) -> MagicMock:
    mock_body = MagicMock()
    mock_body.read.return_value = yaml_bytes
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": mock_body}
    return mock_s3


def test_lint_reads_data_contract_from_s3():
    with open("fixtures/lint/valid_datacontract.yaml", "rb") as f:
        yaml_bytes = f.read()
    mock_s3 = _mock_s3_client_returning(yaml_bytes)

    with patch("boto3.client", return_value=mock_s3):
        data_contract = DataContract(data_contract_file="s3://my-bucket/contracts/datacontract.yaml")
        run = data_contract.lint()

    assert run.result == "passed"
    mock_s3.get_object.assert_called_once_with(Bucket="my-bucket", Key="contracts/datacontract.yaml")


def test_lint_reads_data_contract_from_s3_with_configured_credentials():
    with open("fixtures/lint/valid_datacontract.yaml", "rb") as f:
        yaml_bytes = f.read()
    mock_s3 = _mock_s3_client_returning(yaml_bytes)
    config = Config(
        s3_access_key_id="my-access-key",
        s3_secret_access_key="my-secret-key",
        s3_region="eu-central-1",
    )

    with patch("boto3.client", return_value=mock_s3) as mock_client:
        data_contract = DataContract(data_contract_file="s3://my-bucket/contracts/datacontract.yaml", config=config)
        run = data_contract.lint()

    assert run.result == "passed"
    mock_client.assert_called_once_with(
        "s3",
        region_name="eu-central-1",
        aws_access_key_id="my-access-key",
        aws_secret_access_key="my-secret-key",
        aws_session_token=None,
    )
