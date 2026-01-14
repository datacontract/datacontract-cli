import os

os.environ["TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE"]="/var/run/docker.sock"
from time import sleep

import paramiko
import pytest
import yaml
from testcontainers.sftp import SFTPContainer, SFTPUser
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.imports.excel_importer import import_excel_as_odcs

sftp_dir = "/sftp/data"

csv_file_name = "sample_data"
csv_file_path = f"fixtures/csv/data/{csv_file_name}.csv"
csv_sftp_path = f"{sftp_dir}/{csv_file_name}.csv"

parquet_file_name = "combined_no_time"
parquet_file_path = f"fixtures/parquet/data/{parquet_file_name}.parquet"
parquet_sftp_path = f"{sftp_dir}/{parquet_file_name}.parquet"

avro_file_name = "orders"
avro_file_path = f"fixtures/avro/data/{avro_file_name}.avsc"
avro_sftp_path = f"{sftp_dir}/{avro_file_name}.avsc"

dbml_file_name = "dbml"
dbml_file_path = f"fixtures/dbml/import/{dbml_file_name}.txt"
dbml_sftp_path = f"{sftp_dir}/{dbml_file_name}.txt"

dbt_file_name = "manifest_jaffle_duckdb"
dbt_file_path = f"fixtures/dbt/import/{dbt_file_name}.json"
dbt_sftp_path = f"{sftp_dir}/{dbt_file_name}.json"

iceberg_file_name = "simple_schema"
iceberg_file_path = f"fixtures/iceberg/{iceberg_file_name}.json"
iceberg_sftp_path = f"{sftp_dir}/{iceberg_file_name}.json"

json_file_name = "orders"
json_file_path = f"fixtures/import/{json_file_name}.json"
json_sftp_path = f"{sftp_dir}/{json_file_name}.json"

odcs_file_name = "full-example"
odcs_file_path = f"fixtures/odcs_v3/{odcs_file_name}.odcs.yaml"
odcs_sftp_path = f"{sftp_dir}/{odcs_file_name}.odcs.yaml"

excel_file_path = "./fixtures/excel/shipments-odcs.xlsx"
excel_sftp_path = f"{sftp_dir}/shipments-odcs.xlsx"
username = "demo"  # for emberstack
password = "demo"  # for emberstack
user = SFTPUser(name = username,password=password)


@pytest.fixture
def sftp_container():
    """
    Initialize and provide an SFTP container for all tests in this module.
    Sets up the container, uploads the test file, and provides connection details.
    """
    # that image is both compatible with Mac and Linux which is not the case with the default image

    with SFTPContainer(image="emberstack/sftp:latest", users=[user]) as container:
        host_ip = container.get_container_host_ip()
        host_port = container.get_exposed_sftp_port()

        # Set environment variables for SFTP authentication
        os.environ["DATACONTRACT_SFTP_USER"] = username
        os.environ["DATACONTRACT_SFTP_PASSWORD"] = password

        # Wait for the container to be ready
        sleep(3)

        # Upload test files to SFTP server
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host_ip, host_port, username, password)
        sftp = ssh.open_sftp()
        try:
            sftp.mkdir(sftp_dir)
            sftp.put(avro_file_path, avro_sftp_path)
            sftp.put(dbml_file_path, dbml_sftp_path)
            sftp.put(dbt_file_path, dbt_sftp_path)
            sftp.put(csv_file_path, csv_sftp_path)
            sftp.put(iceberg_file_path, iceberg_sftp_path)
            sftp.put(json_file_path, json_sftp_path)
            sftp.put(odcs_file_path, odcs_sftp_path)
            sftp.put(parquet_file_path, parquet_sftp_path)
            sftp.put(excel_file_path, excel_sftp_path)
        finally:
            sftp.close()
            ssh.close()


        yield {
            "host_ip": host_ip,
            "host_port": host_port,
            "container": container
        }


def test_cli(sftp_container):
    host_ip = sftp_container["host_ip"]
    host_port = sftp_container["host_port"]
    source = f"sftp://{host_ip}:{host_port}{csv_sftp_path}"

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "csv",
            "--source",
            source,
        ],
    )
    assert result.exit_code == 0

def test_import_sftp_csv(sftp_container):
    host_ip = sftp_container["host_ip"]
    host_port = sftp_container["host_port"]
    source = f"sftp://{host_ip}:{host_port}{csv_sftp_path}"

    result = DataContract.import_from_source("csv", source)
    model = result.schema_[0].properties
    assert model is not None
    fields = {x.name:x for x in model}
    assert "field_one" in fields
    assert "field_two" in fields
    assert "field_three" in fields

    assert model is not None





def test_import_sftp_parquet(sftp_container):
    host_ip = sftp_container["host_ip"]
    host_port = sftp_container["host_port"]
    source = f"sftp://{host_ip}:{host_port}{parquet_sftp_path}"

    result = DataContract.import_from_source("parquet", source)
    model = result.schema_[0].properties
    assert model is not None
    fields = {x.name:x for x in model}
    assert fields["string_field"].logicalType == "string"
    assert fields["blob_field"].logicalType == "array"
    assert fields["boolean_field"].logicalType == "boolean"
    assert fields["struct_field"].logicalType == "object"
    assert DataContract(data_contract=result).lint().has_passed()


def test_import_sftp_jsonschema(sftp_container):
    host_ip = sftp_container["host_ip"]
    host_port = sftp_container["host_port"]
    source = f"sftp://{host_ip}:{host_port}{json_sftp_path}"
    result = DataContract.import_from_source("jsonschema", source)
    assert len(result.schema_) > 0
    assert DataContract(data_contract=result).lint().has_passed()


def test_import_excel_odcs(sftp_container):
        host_ip = sftp_container["host_ip"]
        host_port = sftp_container["host_port"]
        source = f"sftp://{host_ip}:{host_port}{excel_sftp_path}"
        result = import_excel_as_odcs(source)
        expected_datacontract = read_file("fixtures/excel/shipments-odcs.yaml")
        assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected_datacontract)

def read_file(file):
    if not os.path.exists(file):
        print(f"The file '{file}' does not exist.")
        raise FileNotFoundError(f"The file '{file}' does not exist.")
    with open(file, "r") as file:
        file_content = file.read()
    return file_content
