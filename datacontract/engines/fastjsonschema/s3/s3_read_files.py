import logging

from datacontract.config import Config
from datacontract.engines.ibis.connections import aws_credentials
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum

logger = logging.getLogger(__name__)


def yield_s3_files(s3_endpoint_url, s3_location, config: Config | None = None):
    fs = s3_fs(s3_endpoint_url, config)
    files = fs.glob(s3_location)
    for file in files:
        with fs.open(file) as f:
            logger.info(f"Downloading file {file}")
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
            engine="datacontract-cli",
            original_exception=e,
        )

    credentials = aws_credentials.resolve_aws_credentials(config)
    if credentials is None:
        return s3fs.S3FileSystem(anon=True, client_kwargs={"endpoint_url": s3_endpoint_url})
    return s3fs.S3FileSystem(
        key=credentials.access_key_id,
        secret=credentials.secret_access_key,
        token=credentials.session_token,
        client_kwargs={"endpoint_url": s3_endpoint_url},
    )
