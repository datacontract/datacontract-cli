"""Resolve the login for a Redshift connection: static password or IAM.

Redshift keeps two identities apart: the AWS IAM principal and the database
user. IAM authentication bridges them — AWS mints a short-lived database user +
password, which is then used for an ordinary login over the Postgres wire
protocol. That exchange is what this module does, so both ``datacontract test``
(ibis/psycopg) and ``datacontract import redshift`` (psycopg) authenticate
identically.

AWS credentials themselves come from the same variables Athena uses
(``DATACONTRACT_S3_*``), falling back to boto3's standard chain — ``aws sso
login``, ``AWS_PROFILE``, instance/task roles, GitHub OIDC.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Optional, Tuple

from datacontract.model.exceptions import DataContractException, require_env

logger = logging.getLogger(__name__)

SERVERLESS = "serverless"
PROVISIONED = "provisioned"

# <workgroup>.<account>.<region>.redshift-serverless.amazonaws.com
# <cluster>.<account>.<region>.redshift.amazonaws.com
_ENDPOINT_PATTERN = re.compile(
    r"^(?P<name>[^.]+)\.(?P<account>[^.]+)\.(?P<region>[^.]+)\.redshift(?P<serverless>-serverless)?\.amazonaws\.com$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RedshiftLogin:
    user: str
    password: Optional[str] = None
    sslmode: Optional[str] = None


def resolve_redshift_login(host: Optional[str], database: Optional[str]) -> RedshiftLogin:
    """Return the database login to connect with, per DATACONTRACT_REDSHIFT_AUTHENTICATION."""
    authentication = os.getenv("DATACONTRACT_REDSHIFT_AUTHENTICATION", "password").strip().lower()

    if authentication == "password":
        return RedshiftLogin(
            user=require_env("DATACONTRACT_REDSHIFT_USERNAME", server_type="redshift"),
            password=os.getenv("DATACONTRACT_REDSHIFT_PASSWORD"),
            sslmode=os.getenv("DATACONTRACT_REDSHIFT_SSLMODE"),
        )

    if authentication == "iam":
        user, password = _mint_iam_credentials(host, database)
        return RedshiftLogin(
            user=user,
            password=password,
            # Temporary credentials are only meaningful over TLS, and every
            # Redshift endpoint supports it; psycopg would otherwise default to
            # `prefer` and silently accept a plaintext connection.
            sslmode=os.getenv("DATACONTRACT_REDSHIFT_SSLMODE", "require"),
        )

    raise DataContractException(
        type="redshift-connection",
        name="unsupported_authentication",
        reason=(
            f"Unsupported DATACONTRACT_REDSHIFT_AUTHENTICATION value {authentication!r}. "
            "Supported values are: password, iam."
        ),
        engine="datacontract",
    )


def _mint_iam_credentials(host: Optional[str], database: Optional[str]) -> Tuple[str, str]:
    flavor, identifier, region = _resolve_endpoint(host)

    if flavor == SERVERLESS:
        client = _aws_client("redshift-serverless", region)
        kwargs = {"workgroupName": identifier}
        if database:
            kwargs["dbName"] = database
        duration = _duration_seconds()
        if duration:
            kwargs["durationSeconds"] = duration
        response = _call_aws(client.get_credentials, kwargs, "redshift-serverless:GetCredentials")
        return response["dbUser"], response["dbPassword"]

    client = _aws_client("redshift", region)
    db_user = os.getenv("DATACONTRACT_REDSHIFT_DB_USER") or os.getenv("DATACONTRACT_REDSHIFT_USERNAME")
    duration = _duration_seconds()

    if not db_user:
        # Derives the database user from the caller's IAM identity, so no
        # username has to be configured at all.
        kwargs = {"ClusterIdentifier": identifier}
        if database:
            kwargs["DbName"] = database
        if duration:
            kwargs["DurationSeconds"] = duration
        response = _call_aws(client.get_cluster_credentials_with_iam, kwargs, "redshift:GetClusterCredentialsWithIAM")
        return response["DbUser"], response["DbPassword"]

    kwargs = {"DbUser": db_user, "ClusterIdentifier": identifier}
    if database:
        kwargs["DbName"] = database
    if duration:
        kwargs["DurationSeconds"] = duration
    if _get_bool_env("DATACONTRACT_REDSHIFT_AUTO_CREATE", False):
        kwargs["AutoCreate"] = True
    db_groups = [
        group.strip() for group in os.getenv("DATACONTRACT_REDSHIFT_DB_GROUPS", "").split(",") if group.strip()
    ]
    if db_groups:
        kwargs["DbGroups"] = db_groups
    response = _call_aws(client.get_cluster_credentials, kwargs, "redshift:GetClusterCredentials")
    return response["DbUser"], response["DbPassword"]


def _resolve_endpoint(host: Optional[str]) -> Tuple[str, str, Optional[str]]:
    """Return ``(flavor, identifier, region)`` for the server's endpoint.

    Both are derivable from a standard endpoint host, so a plain contract needs
    no extra configuration. Custom domains and VPC endpoints don't follow that
    shape, hence the explicit overrides.
    """
    workgroup = os.getenv("DATACONTRACT_REDSHIFT_WORKGROUP")
    cluster = os.getenv("DATACONTRACT_REDSHIFT_CLUSTER_IDENTIFIER")
    region = os.getenv("DATACONTRACT_REDSHIFT_REGION") or os.getenv("DATACONTRACT_S3_REGION")

    match = _ENDPOINT_PATTERN.match(host.strip()) if host else None
    if match:
        flavor = SERVERLESS if match.group("serverless") else PROVISIONED
        return (
            SERVERLESS if workgroup else PROVISIONED if cluster else flavor,
            workgroup or cluster or match.group("name"),
            region or match.group("region"),
        )

    if workgroup:
        return SERVERLESS, workgroup, region
    if cluster:
        return PROVISIONED, cluster, region

    raise DataContractException(
        type="redshift-connection",
        name="unknown_redshift_endpoint",
        reason=(
            f"Could not derive the cluster or workgroup from the host {host!r}. "
            "Set DATACONTRACT_REDSHIFT_WORKGROUP (Redshift Serverless) or "
            "DATACONTRACT_REDSHIFT_CLUSTER_IDENTIFIER (provisioned cluster), "
            "plus DATACONTRACT_REDSHIFT_REGION."
        ),
        engine="datacontract",
    )


def _aws_client(service: str, region: Optional[str]):
    import boto3

    return boto3.client(
        service,
        region_name=region,
        aws_access_key_id=os.getenv("DATACONTRACT_S3_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("DATACONTRACT_S3_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("DATACONTRACT_S3_SESSION_TOKEN"),
    )


def _call_aws(operation, kwargs: dict, api_name: str) -> dict:
    try:
        return operation(**kwargs)
    except Exception as e:
        raise DataContractException(
            type="redshift-connection",
            name="iam_credentials_failed",
            reason=(
                f"Could not obtain temporary Redshift credentials via {api_name}: {e} "
                f"Check that the AWS identity is allowed to call {api_name} and that the region is correct."
            ),
            engine="datacontract",
            original_exception=e,
        )


def _duration_seconds() -> Optional[int]:
    value = os.getenv("DATACONTRACT_REDSHIFT_DURATION_SECONDS")
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        raise DataContractException(
            type="redshift-connection",
            name="invalid_duration_seconds",
            reason=f"DATACONTRACT_REDSHIFT_DURATION_SECONDS must be a whole number of seconds, got {value!r}.",
            engine="datacontract",
        )


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "y", "on")
