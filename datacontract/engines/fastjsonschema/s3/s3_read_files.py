import logging

from datacontract.config import Config
from datacontract.engines.ibis.connections import aws_credentials
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum


def yield_s3_files(s3_endpoint_url, s3_location, config: Config | None = None):
    fs = s3_fs(s3_endpoint_url, config)
    files = fs.glob(s3_location)
    for file in files:
        with fs.open(file) as f:
            logging.info(f"Downloading file {file}")
            yield f.read()


def s3_fs(s3_endpoint_url, config: Config | None = None):
    try:
        import s3fs
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result=ResultEnum.failed,
            name="s3 extra missing",
            reason="Install the extra s3 to use s3",
            engine="datacontract",
            original_exception=e,
        )

    configured = aws_credentials.client_kwargs(config=config)
    aws_access_key_id = configured["aws_access_key_id"]
    aws_secret_access_key = configured["aws_secret_access_key"]
    aws_session_token = configured["aws_session_token"]
    return s3fs.S3FileSystem(
        key=aws_access_key_id,
        secret=aws_secret_access_key,
        token=aws_session_token,
        anon=aws_access_key_id is None,
        client_kwargs={"endpoint_url": s3_endpoint_url},
    )
