"""Resolve AWS credentials for connections that need them handed over explicitly.

duckdb cannot resolve an AWS session itself — its ``PROVIDER credential_chain``
does not read an SSO cache — so a caller that needs credentials in hand asks
here, and boto3 resolves the whole chain: `aws sso login`, `AWS_PROFILE`,
EC2/ECS/EKS instance roles, GitHub OIDC in CI.

Sits beside ``redshift_credentials``, which does the same job for the other
AWS connection that cannot use the chain directly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from datacontract.config import Config

logger = logging.getLogger(__name__)

ACCESS_KEY_ID = "DATACONTRACT_S3_ACCESS_KEY_ID"
SECRET_ACCESS_KEY = "DATACONTRACT_S3_SECRET_ACCESS_KEY"
SESSION_TOKEN = "DATACONTRACT_S3_SESSION_TOKEN"
REGION = "DATACONTRACT_S3_REGION"


def configured_region(default: Optional[str] = None, config: Optional[Config] = None) -> Optional[str]:
    return Config.from_input(config).getenv(REGION) or default


def client_kwargs(region: Optional[str] = None, config: Optional[Config] = None) -> Dict[str, Any]:
    """boto3 client kwargs for the configured credentials.

    A region passed by the caller wins: it comes from a `--region` flag or from
    the endpoint host, both of which are more specific than the variable. Unset
    values stay ``None``, which is how boto3 is told to fall back to its own
    chain, so an `aws sso login` session works without any variable.
    """
    config = Config.from_input(config)
    return {
        "region_name": region or config.getenv(REGION),
        "aws_access_key_id": config.getenv(ACCESS_KEY_ID),
        "aws_secret_access_key": config.getenv(SECRET_ACCESS_KEY),
        "aws_session_token": config.getenv(SESSION_TOKEN),
    }


def client(service: str, region: Optional[str] = None, config: Optional[Config] = None):
    """A boto3 client that honours the DATACONTRACT_S3_* variables.

    Every AWS service the CLI talks to reads the same variables, so they are
    resolved in one place rather than per service.
    """
    import boto3

    return boto3.client(service, **client_kwargs(region, config))


@dataclass(frozen=True)
class AwsCredentials:
    access_key_id: str
    secret_access_key: str
    session_token: Optional[str] = None
    region: Optional[str] = None


def resolve_aws_credentials() -> Optional[AwsCredentials]:
    """Return the credentials boto3 resolves, or ``None`` when nothing resolves.

    ``None`` is a legitimate answer, not an error: reading a public bucket needs
    no credentials at all, and signing that request could only make it fail.
    """
    try:
        import boto3

        session = boto3.Session()
        credentials = session.get_credentials()
        if credentials is None:
            return None
        frozen = credentials.get_frozen_credentials()
    except Exception as e:
        # An expired SSO session raises here while trying to refresh.
        logger.debug("could not resolve AWS credentials: %s", e)
        return None

    return AwsCredentials(
        access_key_id=frozen.access_key,
        secret_access_key=frozen.secret_key,
        session_token=frozen.token,
        region=session.region_name,
    )
