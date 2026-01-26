import os

import yaml

from datacontract.model.exceptions import DataContractException


def to_athena_soda_configuration(server):
    s3_region = os.getenv("DATACONTRACT_S3_REGION")
    s3_access_key_id = os.getenv("DATACONTRACT_S3_ACCESS_KEY_ID")
    s3_secret_access_key = os.getenv("DATACONTRACT_S3_SECRET_ACCESS_KEY")
    s3_session_token = os.getenv("DATACONTRACT_S3_SESSION_TOKEN")

    # Validate required parameters
    if not s3_access_key_id:
        raise DataContractException(
            type="athena-connection",
            name="missing_access_key_id",
            reason="AWS access key ID is required. Set the DATACONTRACT_S3_ACCESS_KEY_ID environment variable.",
            engine="datacontract",
        )

    if not s3_secret_access_key:
        raise DataContractException(
            type="athena-connection",
            name="missing_secret_access_key",
            reason="AWS secret access key is required. Set the DATACONTRACT_S3_SECRET_ACCESS_KEY environment variable.",
            engine="datacontract",
        )

    if not hasattr(server, "schema_") or not server.schema_:
        raise DataContractException(
            type="athena-connection",
            name="missing_schema",
            reason="Schema is required for Athena connection. Specify the schema where your tables exist in the server configuration.",
            engine="datacontract",
        )

    if not hasattr(server, "stagingDir") or not server.stagingDir:
        raise DataContractException(
            type="athena-connection",
            name="missing_s3_staging_dir",
            reason="S3 staging directory is required for Athena connection. This should be the Amazon S3 Query Result Location (e.g., 's3://my-bucket/athena-results/').",
            engine="datacontract",
        )

    # Validate S3 staging directory format
    if not server.stagingDir.startswith("s3://"):
        raise DataContractException(
            type="athena-connection",
            name="invalid_s3_staging_dir",
            reason=f"S3 staging directory must start with 's3://'. Got: {server.s3_staging_dir}. Example: 's3://my-bucket/athena-results/'",
            engine="datacontract",
        )

    data_source = {
        "type": "athena",
        "access_key_id": s3_access_key_id,
        "secret_access_key": s3_secret_access_key,
        "schema": server.schema_,
        "staging_dir": server.stagingDir,
    }

    if s3_region:
        data_source["region_name"] = s3_region
    elif server.region_name:
        data_source["region_name"] = server.region_name

    if server.catalog:
        # Optional, Identify the name of the Data Source, also referred to as a Catalog. The default value is `awsdatacatalog`.
        data_source["catalog"] = server.catalog

    if s3_session_token:
        data_source["session_token"] = s3_session_token

    soda_configuration = {f"data_source {server.type}": data_source}

    soda_configuration_str = yaml.dump(soda_configuration)
    return soda_configuration_str
