import logging
import os

from datacontract.model.exceptions import DataContractException


def yield_az_files(az_storageAccount, az_location):
    fs = az_fs(az_storageAccount)
    files = fs.glob(az_location)
    for file in files:
        with fs.open(file) as f:
            logging.info(f"Downloading file {file}")
            yield f.read()

def az_fs(az_storageAccount):
    try:
        import adlfs
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="az extra missing",
            reason="Install the extra datacontract-cli\\[azure] to use az",
            engine="datacontract",
            original_exception=e,
        )

    az_client_id = os.getenv("DATACONTRACT_AZURE_CLIENT_ID")
    az_client_secret = os.getenv("DATACONTRACT_AZURE_CLIENT_SECRET")
    az_tenant_id = os.getenv("DATACONTRACT_AZURE_TENANT_ID")
    return adlfs.AzureBlobFileSystem(
        account_name=az_storageAccount,
        client_id=az_client_id,
        client_secret=az_client_secret,
        tenant_id=az_tenant_id,
        anon=az_client_id is None,
    )
