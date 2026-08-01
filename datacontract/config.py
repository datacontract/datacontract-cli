"""Programmatic configuration for credentials and connection options.

All connection credentials and options the CLI reads from ``DATACONTRACT_*``
environment variables can also be provided programmatically through
:class:`Config` (or a plain dict keyed by the env var names) via
``DataContract(config=...)``.

Resolution: an active config is held in a :class:`~contextvars.ContextVar`
keyed by the env var names, and :func:`getenv` checks it before falling back
to the process environment. ContextVars propagate per thread and per asyncio
task, so concurrent operations with different credentials do not interfere.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PREFIX = "DATACONTRACT_"

_context_config: ContextVar[dict[str, str]] = ContextVar("datacontract_config", default={})


def getenv(key: str, default: str | None = None) -> str | None:
    """Return a config value: active programmatic config first, then the environment."""
    value = _context_config.get().get(key)
    if value is not None:
        return value
    return os.environ.get(key, default)


@contextmanager
def config_context(config: "Config | dict[str, str] | None"):
    """Activate ``config`` for the duration of the block.

    Accepts a :class:`Config` (flattened via :meth:`Config.to_env_dict`), a plain
    dict keyed by env var names (used as-is, unvalidated), or ``None`` (no-op).
    """
    if config is None:
        yield
        return
    values = config.to_env_dict() if isinstance(config, Config) else dict(config)
    token = _context_config.set(values)
    try:
        yield
    finally:
        _context_config.reset(token)


class Config(BaseSettings):
    """All defined config options, one typed field per ``DATACONTRACT_*`` env var.

    Field names map to env var names by upper-casing and prefixing with
    ``DATACONTRACT_`` (``snowflake_username`` ↔ ``DATACONTRACT_SNOWFLAKE_USERNAME``),
    except where a ``validation_alias`` says otherwise. Instantiation reads the
    environment, so ``Config()`` is a snapshot of the current env and constructor
    keyword arguments override it. Unknown keyword arguments raise immediately;
    unrelated environment variables are ignored.
    """

    model_config = SettingsConfigDict(env_prefix=_ENV_PREFIX, extra="ignore")

    # Entropy Data / Data Mesh Manager / Data Contract Manager (publishing, contract URLs)
    entropy_data_api_key: SecretStr | None = Field(None, validation_alias="ENTROPY_DATA_API_KEY")
    entropy_data_host: str | None = Field(None, validation_alias="ENTROPY_DATA_HOST")
    datamesh_manager_api_key: SecretStr | None = Field(None, validation_alias="DATAMESH_MANAGER_API_KEY")
    datamesh_manager_host: str | None = Field(None, validation_alias="DATAMESH_MANAGER_HOST")
    datacontract_manager_api_key: SecretStr | None = Field(None, validation_alias="DATACONTRACT_MANAGER_API_KEY")
    datacontract_manager_host: str | None = Field(None, validation_alias="DATACONTRACT_MANAGER_HOST")

    # general
    api_header_authorization: SecretStr | None = None
    max_errors: int | None = None

    # azure
    azure_connection_string: SecretStr | None = None
    azure_storage_account_key: SecretStr | None = None
    azure_tenant_id: str | None = None
    azure_client_id: str | None = None
    azure_client_secret: SecretStr | None = None

    # bigquery
    bigquery_account_info_json_path: str | None = None
    bigquery_billing_project: str | None = None
    bigquery_impersonation_account: str | None = None

    # databricks
    databricks_server_hostname: str | None = None
    databricks_http_path: str | None = None
    databricks_token: SecretStr | None = None
    databricks_client_id: str | None = None
    databricks_client_secret: SecretStr | None = None
    databricks_profile: str | None = None
    databricks_auth_type: str | None = None

    # gcs
    gcs_key_id: str | None = None
    gcs_secret: SecretStr | None = None

    # impala
    impala_username: str | None = None
    impala_password: SecretStr | None = None
    impala_auth_mechanism: str | None = None
    impala_http_path: str | None = None
    impala_use_ssl: bool | None = None
    impala_use_http_transport: bool | None = None

    # kafka
    kafka_sasl_username: str | None = None
    kafka_sasl_password: SecretStr | None = None
    kafka_sasl_mechanism: str | None = None
    kafka_schema_registry_url: str | None = None
    kafka_schema_registry_username: str | None = None
    kafka_schema_registry_password: SecretStr | None = None

    # mysql
    mysql_username: str | None = None
    mysql_password: SecretStr | None = None

    # oracle
    oracle_username: str | None = None
    oracle_password: SecretStr | None = None
    oracle_client_dir: str | None = None

    # postgres
    postgres_username: str | None = None
    postgres_password: SecretStr | None = None

    # redshift
    redshift_authentication: str | None = None
    redshift_username: str | None = None
    redshift_password: SecretStr | None = None
    redshift_sslmode: str | None = None
    redshift_db_user: str | None = None
    redshift_db_groups: str | None = None
    redshift_auto_create: bool | None = None
    redshift_workgroup: str | None = None
    redshift_cluster_identifier: str | None = None
    redshift_region: str | None = None
    redshift_duration_seconds: int | None = None

    # s3 (also used for Athena and Redshift IAM as the AWS credential set)
    s3_access_key_id: str | None = None
    s3_secret_access_key: SecretStr | None = None
    s3_session_token: SecretStr | None = None
    s3_region: str | None = None

    # snowflake
    snowflake_username: str | None = None
    snowflake_password: SecretStr | None = None
    snowflake_authenticator: str | None = None
    snowflake_role: str | None = None
    snowflake_token: SecretStr | None = None
    snowflake_passcode: SecretStr | None = None
    snowflake_private_key: SecretStr | None = None
    snowflake_private_key_file: str | None = None
    snowflake_private_key_file_pwd: SecretStr | None = None
    snowflake_warehouse: str | None = None
    snowflake_create_object_udfs: bool | None = None
    snowflake_login_timeout: int | None = None
    snowflake_network_timeout: int | None = None
    snowflake_socket_timeout: int | None = None
    snowflake_host: str | None = None
    snowflake_port: int | None = None
    snowflake_home: str | None = None
    snowflake_connections_file: str | None = None
    snowflake_default_connection_name: str | None = None
    # deprecated synonyms, mapped (with a warning) where they are consumed
    snowflake_private_key_path: str | None = None
    snowflake_private_key_passphrase: SecretStr | None = None
    snowflake_connection_timeout: int | None = None

    # sqlserver
    sqlserver_authentication: str | None = None
    sqlserver_username: str | None = None
    sqlserver_password: SecretStr | None = None
    sqlserver_client_id: str | None = None
    sqlserver_client_secret: SecretStr | None = None
    sqlserver_driver: str | None = None
    sqlserver_encrypted_connection: bool | None = None
    sqlserver_trust_server_certificate: bool | None = None
    sqlserver_trusted_connection: bool | None = None

    # trino
    trino_authentication: str | None = None
    trino_username: str | None = None
    trino_password: SecretStr | None = None
    trino_jwt_token: SecretStr | None = None

    def __init__(self, **data):
        # extra="ignore" keeps unrelated env vars from breaking instantiation, but
        # programmatic typos must not be silently dropped with them.
        unknown = set(data) - set(type(self).model_fields)
        if unknown:
            raise ValueError(f"Unknown config option(s): {', '.join(sorted(unknown))}. See datacontract.Config.")
        super().__init__(**data)

    def to_env_dict(self) -> dict[str, str]:
        """Flatten to a dict keyed by the env var names, for the resolution context."""
        values: dict[str, str] = {}
        for name, field in type(self).model_fields.items():
            value = getattr(self, name)
            if value is None:
                continue
            values[env_name(name, field)] = _as_env_value(value)
        return values


def env_name(field_name: str, field) -> str:
    alias = field.validation_alias
    if isinstance(alias, str):
        return alias
    return _ENV_PREFIX + field_name.upper()


def _as_env_value(value) -> str:
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def known_env_names() -> set[str]:
    """All env var names that map to a Config field."""
    return {env_name(name, field) for name, field in Config.model_fields.items()}


def unknown_snowflake_env_names() -> list[str]:
    """``DATACONTRACT_SNOWFLAKE_*`` names in the active config or environment
    that no Config field declares.

    Until v1.0.16 every such variable was forwarded verbatim to the Snowflake
    connector; now only declared options are. Callers use this to warn instead
    of silently ignoring them.
    """
    known = known_env_names()
    candidates = set(os.environ) | set(_context_config.get())
    return sorted(name for name in candidates if name.startswith("DATACONTRACT_SNOWFLAKE_") and name not in known)
