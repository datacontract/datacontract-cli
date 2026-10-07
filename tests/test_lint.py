from unittest.mock import MagicMock, patch

from open_data_contract_standard.model import OpenDataContractStandard
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.config import Config
from datacontract.data_contract import DataContract
from datacontract.lint.resolve import resolve_data_contract

# logging.basicConfig(level=logging.INFO, force=True)

runner = CliRunner()


def test_lint_valid_data_contract():
    data_contract_file = "fixtures/lint/valid_datacontract.yaml"
    data_contract = DataContract(data_contract_file=data_contract_file)

    run = data_contract.lint()
    assert run.result == "passed"


def test_lint_cli_valid():
    data_contract_file = "fixtures/lint/valid_datacontract.yaml"
    expected_output = "🟢 Data contract is valid. Ran 1 checks."

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


def test_lint_custom_schema_rejects_the_fields_it_does_not_define():
    data_contract_file = "fixtures/lint/misspelled_property_key.odcs.yaml"
    schema_file = "fixtures/lint/strict_property_keys.schema.json"
    data_contract = DataContract(data_contract_file=data_contract_file, schema_location=schema_file)

    run = data_contract.lint()

    assert run.result == "failed"
    assert "'qualiti' was unexpected" in run.checks[0].reason


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


def test_lint_warns_about_a_misspelled_property_key():
    data_contract_file = "fixtures/lint/misspelled_property_key.odcs.yaml"
    data_contract = DataContract(data_contract_file=data_contract_file)

    run = data_contract.lint()

    assert run.result == "warning"
    assert [check.reason for check in run.checks if check.result == "warning"] == [
        "data.schema.orders.properties.email: unknown fields are ignored: 'qualiti'. "
        "This will become an error in the next major version."
    ]


def test_lint_warns_about_a_misspelled_property_key_once_with_all_errors():
    data_contract_file = "fixtures/lint/misspelled_property_key.odcs.yaml"
    data_contract = DataContract(data_contract_file=data_contract_file, all_errors=True)

    run = data_contract.lint()

    assert [check.result for check in run.checks] == ["passed", "warning"]


def test_test_warns_about_a_misspelled_property_key():
    data_contract_file = "fixtures/lint/misspelled_property_key.odcs.yaml"
    data_contract = DataContract(data_contract_file=data_contract_file)

    run = data_contract.test()

    assert run.result == "warning"
    assert "'qualiti'" in next(check.reason for check in run.checks if check.result == "warning")


def test_lint_invalid_odcs_schema_multiple_errors():
    data_contract_file = "fixtures/lint/invalid_multiple_schema_errors.odcs.yaml"
    result = runner.invoke(app, ["lint", data_contract_file])

    assert result.exit_code == 1
    assert "data.schema.no_description_schema.description: None is not of type" in result.stdout


def test_lint_points_into_the_matching_one_of_branch():
    contract = """
apiVersion: v3.1.0
kind: DataContract
id: team-typo
version: "1"
status: active
team:
  - username: alice
    rol: owner
"""
    run = DataContract(data_contract_str=contract).lint()

    assert run.checks[0].reason == "data.team[0]: Additional properties are not allowed ('rol' was unexpected)"


def test_lint_says_when_several_one_of_branches_match():
    contract = """
apiVersion: v3.1.0
kind: DataContract
id: two-operators
version: "1"
status: active
schema:
  - name: orders
    quality:
      - type: library
        metric: rowCount
        mustBe: 0
        mustBeGreaterThan: 1
"""
    run = DataContract(data_contract_str=contract).lint()

    assert run.checks[0].reason == (
        "data.schema.orders.quality[0]: must match exactly one of 8 definitions, but matches several"
    )


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


def _contract(api_version: str, logical_type: str = "timestamp") -> str:
    return f"""
apiVersion: {api_version}
kind: DataContract
id: declared-version
version: "1"
status: active
schema:
  - name: orders
    properties:
      - name: created_at
        logicalType: {logical_type}
"""


def test_lint_uses_the_schema_for_the_declared_api_version():
    # timestamp is a logicalType from ODCS v3.1.0, so a contract claiming v3.0.2 is invalid.
    run = DataContract(data_contract_str=_contract("v3.0.2")).lint()

    assert run.result == "failed"
    assert run.checks[0].name == "Check that data contract is valid against ODCS v3.0.2"


def test_lint_names_the_schema_that_ran():
    run = DataContract(data_contract_str=_contract("v3.1.0")).lint()

    assert run.result == "passed"
    assert run.checks[0].name == "Data contract is valid against ODCS v3.1.0"


def test_lint_maps_every_v3_0_x_to_the_v3_0_2_schema():
    for api_version in ["v3.0.0", "v3.0.1", "v3.0.2"]:
        run = DataContract(data_contract_str=_contract(api_version, logical_type="string")).lint()

        assert run.result == "passed"
        assert run.checks[0].name == "Data contract is valid against ODCS v3.0.2"


def test_lint_falls_back_to_the_newest_schema_for_an_unknown_api_version():
    run = DataContract(data_contract_str=_contract("v3.9.9")).lint()

    assert run.result == "failed"
    assert run.checks[0].name == "Check that data contract is valid against ODCS v3.2.0"
    assert "apiVersion" in run.checks[0].reason


def test_only_lint_honours_the_declared_api_version():
    contract = _contract("v3.0.2")

    assert DataContract(data_contract_str=contract).lint().result == "failed"
    assert resolve_data_contract(data_contract_str=contract).apiVersion == "v3.0.2"
