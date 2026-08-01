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
import re
from dataclasses import dataclass
from typing import Optional, Tuple

from datacontract.config import Config
from datacontract.engines.ibis.connections import aws_credentials
from datacontract.model.exceptions import DataContractException

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


def resolve_redshift_login(
    host: Optional[str], database: Optional[str], config: Optional[Config] = None
) -> RedshiftLogin:
    """Return the database login to connect with.

    The method is inferred from what is configured, so the common cases need no
    extra variable. ``DATACONTRACT_REDSHIFT_AUTHENTICATION`` stays as an
    override for when the inference guesses wrong, matching the equivalent
    variables on Databricks, Snowflake, SQL Server and Trino.
    """
    config = Config.from_input(config)
    authentication = config.getenv("DATACONTRACT_REDSHIFT_AUTHENTICATION", "").strip().lower() or _infer_authentication(
        config
    )

    if authentication == "password":
        return RedshiftLogin(
            user=config.require("DATACONTRACT_REDSHIFT_USERNAME", server_type="redshift"),
            password=config.getenv("DATACONTRACT_REDSHIFT_PASSWORD"),
            sslmode=config.getenv("DATACONTRACT_REDSHIFT_SSLMODE"),
        )

    if authentication == "iam":
        user, password = _mint_iam_credentials(host, database, config)
        return RedshiftLogin(
            user=user,
            password=password,
            # Temporary credentials are only meaningful over TLS, and every
            # Redshift endpoint supports it; psycopg would otherwise default to
            # `prefer` and silently accept a plaintext connection.
            sslmode=config.getenv("DATACONTRACT_REDSHIFT_SSLMODE", "require"),
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


def _infer_authentication(config: Config) -> str:
    """Pick the authentication method from what is configured.

    Keyed on the password, not the username: IAM on a provisioned cluster also
    reads ``DATACONTRACT_REDSHIFT_USERNAME`` as the database user, so a set
    username says nothing about which method was intended.
    """
    if config.getenv("DATACONTRACT_REDSHIFT_PASSWORD"):
        return "password"
    if _aws_credentials_available(config):
        return "iam"
    raise DataContractException(
        type="redshift-connection",
        name="no_authentication_available",
        reason=(
            "Could not determine how to authenticate with Redshift. Set DATACONTRACT_REDSHIFT_USERNAME and "
            "DATACONTRACT_REDSHIFT_PASSWORD for a database login, or sign in to AWS (e.g. aws sso login) to use "
            "IAM authentication."
        ),
        engine="datacontract",
    )


def _aws_credentials_available(config: Config) -> bool:
    """True when boto3 can resolve credentials from anywhere in its chain."""
    configured = aws_credentials.client_kwargs(config=config)
    if configured["aws_access_key_id"] and configured["aws_secret_access_key"]:
        return True
    try:
        import boto3

        return boto3.Session().get_credentials() is not None
    except Exception as e:  # boto3 missing, or a broken profile/config file
        logger.debug("could not resolve AWS credentials: %s", e)
        return False


def _mint_iam_credentials(host: Optional[str], database: Optional[str], config: Config) -> Tuple[str, str]:
    flavor, identifier, region = _resolve_endpoint(host, config)

    if flavor == SERVERLESS:
        client = _aws_client("redshift-serverless", region, config)
        kwargs = {"workgroupName": identifier}
        if database:
            kwargs["dbName"] = database
        duration = _duration_seconds(config)
        if duration:
            kwargs["durationSeconds"] = duration
        response = _call_aws(client.get_credentials, kwargs, "redshift-serverless:GetCredentials")
        return response["dbUser"], response["dbPassword"]

    client = _aws_client("redshift", region, config)
    db_user = config.getenv("DATACONTRACT_REDSHIFT_DB_USER") or config.getenv("DATACONTRACT_REDSHIFT_USERNAME")
    duration = _duration_seconds(config)

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
    if config.get_bool("DATACONTRACT_REDSHIFT_AUTO_CREATE", False):
        kwargs["AutoCreate"] = True
    db_groups = [
        group.strip() for group in config.getenv("DATACONTRACT_REDSHIFT_DB_GROUPS", "").split(",") if group.strip()
    ]
    if db_groups:
        kwargs["DbGroups"] = db_groups
    response = _call_aws(client.get_cluster_credentials, kwargs, "redshift:GetClusterCredentials")
    return response["DbUser"], response["DbPassword"]


def _resolve_endpoint(host: Optional[str], config: Config) -> Tuple[str, str, Optional[str]]:
    """Return ``(flavor, identifier, region)`` for the server's endpoint.

    Both are derivable from a standard endpoint host, so a plain contract needs
    no extra configuration. Custom domains and VPC endpoints don't follow that
    shape, hence the explicit overrides.
    """
    workgroup = config.getenv("DATACONTRACT_REDSHIFT_WORKGROUP")
    cluster = config.getenv("DATACONTRACT_REDSHIFT_CLUSTER_IDENTIFIER")
    region = config.getenv("DATACONTRACT_REDSHIFT_REGION") or config.getenv("DATACONTRACT_S3_REGION")

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


def _aws_client(service: str, region: Optional[str], config: Config):
    return aws_credentials.client(service, region, config)


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


def _duration_seconds(config: Config) -> Optional[int]:
    value = config.getenv("DATACONTRACT_REDSHIFT_DURATION_SECONDS")
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
