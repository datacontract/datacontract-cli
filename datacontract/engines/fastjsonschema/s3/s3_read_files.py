import logging
import os

from datacontract.model.exceptions import DataContractException


def yield_s3_files(s3_endpoint_url, s3_location):
    fs = s3_fs(s3_endpoint_url)
    files = fs.glob(s3_location)
    for file in files:
        with fs.open(file) as f:
            logging.info(f"Downloading file {file}")
            yield f.read()

def yield_azure_files(azure_location): # Azure servers do not require endpoint_url
    fs = ad_lfs()
    files = fs.glob(azure_location)
    for file in files:
        with fs.open(file) as f:
            logging.info(f"Downloading file {file}")
            yield f.read()

def s3_fs(s3_endpoint_url):
    try:
        import s3fs
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="s3 extra missing",
            reason="Install the extra datacontract-cli\[s3] to use s3",
            engine="datacontract",
            original_exception=e,
        )

    aws_access_key_id = os.getenv("DATACONTRACT_S3_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("DATACONTRACT_S3_SECRET_ACCESS_KEY")
    aws_session_token = os.getenv("DATACONTRACT_S3_SESSION_TOKEN")
    return s3fs.S3FileSystem(
        key=aws_access_key_id,
        secret=aws_secret_access_key,
        token=aws_session_token,
        anon=aws_access_key_id is None,
        client_kwargs={"endpoint_url": s3_endpoint_url},
    )

def ad_lfs(): #azure_account):
    try:
        import adlfs
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="adlfs extra missing",
            reason="Install the extra datacontract-cli\[azure] to use azure",
            engine="datacontract",
            original_exception=e,
        )
    azure_client_id = os.getenv("DATACONTRACT_AZURE_CLIENT_ID")
    azure_client_secret_key = os.getenv("DATACONTRACT_AZURE_CLIENT_SECRET")
    azure_tenant_id = os.getenv("DATACONTRACT_AZURE_TENANT_ID")
    return adlfs.AzureBlobFileSystem(
        # account_name=azure_account,
        tenant_id=azure_tenant_id, 
        client_id=azure_client_id,
        client_secret=azure_client_secret_key,
    )
