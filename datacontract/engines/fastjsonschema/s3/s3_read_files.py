import logging
import os

import s3fs


def yield_s3_files(s3_endpoint_url, s3_location):
    fs = s3_fs(s3_endpoint_url)
    files = fs.glob(s3_location)
    for file in files:
        with fs.open(file) as f:
            logging.info(f"Reading file {file}")
            yield f.read()


def s3_fs(s3_endpoint_url):
    aws_access_key_id = os.getenv('DATACONTRACT_S3_ACCESS_KEY_ID')
    aws_secret_access_key = os.getenv('DATACONTRACT_S3_SECRET_ACCESS_KEY')
    return s3fs.S3FileSystem(key=aws_access_key_id,
                             secret=aws_secret_access_key,
                             anon=aws_access_key_id is None,
                             client_kwargs={'endpoint_url': s3_endpoint_url})
