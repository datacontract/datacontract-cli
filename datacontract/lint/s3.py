from urllib.parse import urlparse

import boto3

from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum


def fetch_resource(url: str) -> str:
    parsed_url = urlparse(url)
    bucket = parsed_url.netloc
    key = parsed_url.path.lstrip("/")
    try:
        response = boto3.client("s3").get_object(Bucket=bucket, Key=key)
        body = response["Body"].read()
        return body.decode("utf-8")
    except Exception as e:
        raise DataContractException(
            type="lint",
            name=f"Reading data contract from {url}",
            reason=f"Cannot read resource from {url}. Error: {e}",
            engine="datacontract",
            result=ResultEnum.error,
            original_exception=e,
        )
