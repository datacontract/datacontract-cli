from time import sleep

import paramiko
import pytest

from datacontract.data_contract import DataContract
import os
datacontract = "fixtures/sftp-csv/datacontract.yaml"
file_name = "fixtures/sftp-csv/data/sample_data.csv"
sftp_dir = "/sftp/data"
sftp_path = f"{sftp_dir}/sample_data.csv"
from testcontainers.sftp import SFTPContainer, SFTPUser

username = "demo"  # for emberstack
password = "demo"  # for emberstack
user = SFTPUser(name = username,password=password)

def test_test_sftp_csv():
    # Utiliser une image compatible ARM64
    os.environ["DATACONTRACT_SFTP_USER"] =  username
    os.environ["DATACONTRACT_SFTP_PASSWORD"] =  password
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
            sftp.put(file_name, sftp_path)
            dc.servers["my-server"].location = f"sftp://{host_ip}:{host_port}{sftp_path}"
            run = DataContract(data_contract=dc).test()
            assert run.result == "passed"
        finally:
            sftp.close()
            ssh.close()
