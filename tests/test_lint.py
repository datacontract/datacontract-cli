import os
from time import sleep

import paramiko
from datacontract_specification.model import Server
from testcontainers.sftp import SFTPContainer, SFTPUser
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract, DataContractSpecification

# logging.basicConfig(level=logging.INFO, force=True)

runner = CliRunner()


def test_lint_valid_data_contract():
    data_contract_file = "fixtures/lint/valid_datacontract.yaml"
    data_contract = DataContract(data_contract_file=data_contract_file)

    run = data_contract.lint()
    assert run.result == "passed"


def test_lint_invalid_data_contract():
    data_contract_file = "fixtures/lint/invalid_datacontract.yaml"
    data_contract = DataContract(data_contract_file=data_contract_file)

    run = data_contract.lint()

    assert run.result == "failed"


def test_lint_cli_valid():
    data_contract_file = "fixtures/lint/valid_datacontract.yaml"
    expected_output = "🟢 data contract is valid. Run 1 checks."

    result = runner.invoke(app, ["lint", data_contract_file])

    assert result.exit_code == 0
    assert expected_output in result.stdout


def test_lint_cli_invalid():
    data_contract_file = "fixtures/lint/invalid_datacontract.yaml"
    expected_output = "🔴 data contract is invalid, found the following errors:\n1) Check that data contract YAML is valid: data must contain ['id'] properties\n"

    result = runner.invoke(app, ["lint", data_contract_file])

    assert result.exit_code == 1
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
    DataContractSpecification.model_validate(data_contract.get_data_contract_specification())

    assert run.result == "passed"


def test_lint_with_references():
    data_contract = DataContract(data_contract_file="fixtures/lint/valid_datacontract_references.yaml")

    run = data_contract.lint()

    assert run.result == "passed"




def test_lint_sftp():
    sftp_dir = "/sftp/data"
    sftp_path = f"{sftp_dir}/valid_datacontract.yaml"
    datacontract = "fixtures/lint/valid_datacontract.yaml"
    username = "demo"  # for emberstack
    password = "demo"  # for emberstack
    user = SFTPUser(name=username, password=password)
    os.environ["DATACONTRACT_SFTP_USER"] =  username
    os.environ["DATACONTRACT_SFTP_PASSWORD"] =  password

    # that image is both compatible with Mac and Linux which is not the case with the default image
    with SFTPContainer(image="emberstack/sftp:latest",users=[user]) as sftp_container:
        host_ip = sftp_container.get_container_host_ip()
        host_port = sftp_container.get_exposed_sftp_port()
        sleep(3) #waiting for the container to be really ready
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host_ip, host_port, username, password)
        sftp = ssh.open_sftp()
        dc = DataContract(data_contract_file=datacontract).get_data_contract_specification()
        try:
            sftp.mkdir(sftp_dir)
            sftp.put(datacontract, sftp_path)
            dc.servers["my-server"]=Server(location =f"sftp://{host_ip}:{host_port}{sftp_path}")
            run = DataContract(data_contract=dc).lint()
            assert run.result == "passed"
        finally:
            sftp.close()
            ssh.close()
