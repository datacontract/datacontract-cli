import logging
import os

from datacontract.model.exceptions import DataContractException


def yield_azure_files(azure_location, azure_account): # Azure servers do not require endpoint_url
    fs = ad_lfs(azure_account)
    files = fs.glob(azure_location)
    for file in files:
        with fs.open(file) as f:
            logging.info(f"Downloading file {file}")
            yield f.read()

def ad_lfs(azure_account):
    try:
        import adlfs
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="adlfs extra missing",
            reason="Install the extra datacontract-cli\\[azure] to use azure",
            engine="datacontract",
            original_exception=e,
        )
    azure_client_id = os.getenv("DATACONTRACT_AZURE_CLIENT_ID")
    azure_client_secret_key = os.getenv("DATACONTRACT_AZURE_CLIENT_SECRET")
    azure_tenant_id = os.getenv("DATACONTRACT_AZURE_TENANT_ID")
    return adlfs.AzureBlobFileSystem(
        account_name=azure_account,
        tenant_id=azure_tenant_id, 
        client_id=azure_client_id,
        client_secret=azure_client_secret_key,
    )
