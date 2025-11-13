import os
from time import sleep

import paramiko
import pytest
import yaml
from testcontainers.sftp import SFTPContainer, SFTPUser
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

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

protobuf_file_name = "sample_data"
protobuf_file_path = f"fixtures/protobuf/data/{protobuf_file_name}.proto3.data"
protobuf_sftp_path = f"{sftp_dir}/{protobuf_file_name}.proto3.data"


username = "demo"  # for emberstack
password = "demo"  # for emberstack
user = SFTPUser(name = username,password=password)


@pytest.fixture(scope="module")
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
            sftp.put(protobuf_file_path, protobuf_sftp_path)
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
    model = result.models[csv_file_name]
    assert model is not None
    assert len(model.fields["field_one"].examples) == 5
    assert len(model.fields["field_two"].examples) > 0
    assert len(model.fields["field_three"].examples) > 0

    for k in model.fields.keys():
        model.fields[k].examples = None

    expected = f"""
                dataContractSpecification: 1.2.1
                id: my-data-contract-id
                info:
                  title: My Data Contract
                  version: 0.0.1
                servers:
                  production:
                    type: local
                    format: csv
                    path: sftp://{host_ip}:{host_port}{csv_sftp_path}
                    delimiter: ','
                models:
                  {csv_file_name}:
                    description: Generated model of sftp://{host_ip}:{host_port}{csv_sftp_path}
                    type: table
                    fields:
                      field_one:
                        type: string
                        required: true
                        unique: true
                      field_two:
                        type: integer
                        required: true
                        unique: true
                        minimum: 14.0
                        maximum: 89.0
                      field_three:
                        type: timestamp
                        required: true
                        unique: true
                """
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    # Disable linters so we don't get "missing description" warnings
    assert DataContract(data_contract_str=expected).lint().has_passed()




def test_import_sftp_parquet(sftp_container):
    host_ip = sftp_container["host_ip"]
    host_port = sftp_container["host_port"]
    source = f"sftp://{host_ip}:{host_port}{parquet_sftp_path}"

    result = DataContract.import_from_source("parquet", source)
    model = result.models[parquet_file_name]
    assert model is not None
    assert model.fields["string_field"].type == "string"
    assert model.fields["blob_field"].type == "bytes"
    assert model.fields["boolean_field"].type == "boolean"
    assert DataContract(data_contract=result).lint().has_passed()

def test_import_sftp_avro(sftp_container):
    host_ip = sftp_container["host_ip"]
    host_port = sftp_container["host_port"]
    source = f"sftp://{host_ip}:{host_port}{avro_sftp_path}"

    result = DataContract.import_from_source("avro", source)
    model = result.models[avro_file_name]
    assert model is not None
    assert model.fields["ordertime"].type == "long"
    assert model.fields["orderid"].type == "int"
    assert model.fields["itemid"].type == "string"
    assert len(model.fields.keys()) == 9
    assert DataContract(data_contract=result).lint().has_passed()

def test_import_sftp_dbml(sftp_container):
    host_ip = sftp_container["host_ip"]
    host_port = sftp_container["host_port"]
    source = f"sftp://{host_ip}:{host_port}{dbml_sftp_path}"

    result = DataContract.import_from_source("dbml", source)
    assert(len(result.models.keys())) == 2
    assert DataContract(data_contract=result).lint().has_passed()

def test_import_sftp_dbt(sftp_container):
    host_ip = sftp_container["host_ip"]
    host_port = sftp_container["host_port"]
    source = f"sftp://{host_ip}:{host_port}{dbt_sftp_path}"
    result = DataContract.import_from_source("dbt", source)
    assert set(result.models.keys()) == {'orders', 'stg_customers', 'stg_orders', 'stg_payments', 'customers'}
    assert DataContract(data_contract=result).lint().has_passed()

def test_import_sftp_iceberg(sftp_container):
    host_ip = sftp_container["host_ip"]
    host_port = sftp_container["host_port"]
    source = f"sftp://{host_ip}:{host_port}{iceberg_sftp_path}"

    result = DataContract.import_from_source("iceberg", source)
    assert len(result.models.keys()) > 0
    assert DataContract(data_contract=result).lint().has_passed()

def test_import_sftp_jsonschema(sftp_container):
    host_ip = sftp_container["host_ip"]
    host_port = sftp_container["host_port"]
    source = f"sftp://{host_ip}:{host_port}{json_sftp_path}"
    result = DataContract.import_from_source("jsonschema", source)
    assert len(result.models.keys()) > 0
    assert DataContract(data_contract=result).lint().has_passed()

def test_import_sftp_odcs(sftp_container):
    host_ip = sftp_container["host_ip"]
    host_port = sftp_container["host_port"]
    source = f"sftp://{host_ip}:{host_port}{odcs_sftp_path}"
    result = DataContract.import_from_source("odcs", source)
    model = result.models["tbl_1"]
    assert model is not None
    assert DataContract(data_contract=result).lint().has_passed()
