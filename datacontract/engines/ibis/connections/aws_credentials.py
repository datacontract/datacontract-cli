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
from typing import Optional

logger = logging.getLogger(__name__)


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
    except Exception as e:
        logger.debug("could not resolve AWS credentials: %s", e)
        return None

    if credentials is None:
        return None

    frozen = credentials.get_frozen_credentials()
    return AwsCredentials(
        access_key_id=frozen.access_key,
        secret_access_key=frozen.secret_key,
        session_token=frozen.token,
        region=session.region_name,
    )
