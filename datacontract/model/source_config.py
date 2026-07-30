"""Typed credentials for a source family, passable programmatically.

Each class mirrors one ``DATACONTRACT_<FAMILY>_*`` variable group. Fields passed
explicitly win per field; anything left unset falls back to the environment, so
environment-only setups keep working unchanged.
"""

from __future__ import annotations

import os
import typing

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, EnvSettingsSource, SettingsConfigDict


class BaseSourceConfig(BaseSettings):
    # populate_by_name is load-bearing: a field with a validation_alias is otherwise
    # settable only by its environment variable name, which breaks the Python API.
    model_config = SettingsConfigDict(extra="forbid", env_ignore_empty=True, populate_by_name=True)


class DatabricksSourceConfig(BaseSourceConfig):
    """Credentials for the ``databricks`` server type and the Unity Catalog importer."""

    model_config = SettingsConfigDict(env_prefix="DATACONTRACT_DATABRICKS_")

    server_hostname: str | None = None
    http_path: str | None = None
    token: SecretStr | None = None
    client_id: str | None = None
    client_secret: SecretStr | None = None
    profile: str | None = None
    auth_type: str | None = None


class _SnowflakeEnvSource(EnvSettingsSource):
    """Sweep undeclared ``DATACONTRACT_SNOWFLAKE_*`` variables into ``connection_parameters``.

    Any prefixed variable is a documented connection parameter for
    snowflake-connector-python, so the set is open and cannot be fully declared.
    """

    def __call__(self) -> dict[str, typing.Any]:
        data = super().__call__()
        declared = {
            env_name.lower()
            for name, field in self.settings_cls.model_fields.items()
            for _, env_name, _ in self._extract_field_info(field, name)
        }
        prefix = self.env_prefix
        swept = {
            name[len(prefix) :].lower(): value
            for name, value in os.environ.items()
            if value and name.startswith(prefix) and name.lower() not in declared
        }
        data["connection_parameters"] = {**swept, **data.get("connection_parameters", {})}
        return data


def _snowflake_alias(name: str) -> AliasChoices:
    """The prefixed variable, then the bare ``SNOWFLAKE_*`` one the importer accepts."""
    return AliasChoices(f"DATACONTRACT_SNOWFLAKE_{name.upper()}", f"SNOWFLAKE_{name.upper()}")


class SnowflakeSourceConfig(BaseSourceConfig):
    """Credentials for the ``snowflake`` server type and the Snowflake importer."""

    model_config = SettingsConfigDict(env_prefix="DATACONTRACT_SNOWFLAKE_")

    user: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATACONTRACT_SNOWFLAKE_USER", "DATACONTRACT_SNOWFLAKE_USERNAME"),
    )
    password: SecretStr | None = None
    role: str | None = None
    warehouse: str | None = None
    authenticator: str | None = None
    connection_timeout: str | None = None
    private_key: SecretStr | None = None
    private_key_passphrase: SecretStr | None = None
    private_key_path: str | None = None
    private_key_file: str | None = Field(default=None, validation_alias=_snowflake_alias("private_key_file"))
    private_key_file_pwd: SecretStr | None = Field(
        default=None, validation_alias=_snowflake_alias("private_key_file_pwd")
    )

    # Locate connections.toml. Read by the importer only; not connection parameters.
    home: str | None = Field(default=None, validation_alias=_snowflake_alias("home"))
    connections_file: str | None = Field(default=None, validation_alias=_snowflake_alias("connections_file"))
    default_connection_name: str | None = Field(
        default=None, validation_alias=_snowflake_alias("default_connection_name")
    )

    # ibis opens the connection with helper UDF creation enabled; datacontract only reads.
    create_object_udfs: bool = False

    # Connector parameters we do not declare, forwarded verbatim to the driver.
    connection_parameters: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def settings_customise_sources(
        cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings
    ):
        return init_settings, _SnowflakeEnvSource(settings_cls), dotenv_settings, file_secret_settings

    def driver_parameters(self) -> dict[str, typing.Any]:
        """The declared fields snowflake-connector-python accepts, plus the undeclared sweep."""
        declared = {
            "user": self.user,
            "password": self.password,
            "role": self.role,
            "warehouse": self.warehouse,
            "authenticator": self.authenticator,
            "connection_timeout": self.connection_timeout,
            "private_key": self.private_key,
            "private_key_passphrase": self.private_key_passphrase,
            "private_key_path": self.private_key_path,
            "private_key_file": self.private_key_file,
            "private_key_file_pwd": self.private_key_file_pwd,
        }
        params = {**self.connection_parameters}
        for name, value in declared.items():
            if value is not None:
                params[name] = value.get_secret_value() if isinstance(value, SecretStr) else value
        return params


SourceConfigType = typing.Union[DatabricksSourceConfig, SnowflakeSourceConfig]

SourceConfigInput = typing.Union[SourceConfigType, typing.Sequence[SourceConfigType], None]


def normalize_source_configs(source_config: SourceConfigInput) -> tuple[BaseSourceConfig, ...]:
    """Accept one config or a sequence, rejecting anything ambiguous at construction time."""
    if source_config is None:
        return ()
    configs = (source_config,) if isinstance(source_config, BaseSourceConfig) else tuple(source_config)

    seen = set()
    for config in configs:
        if not isinstance(config, BaseSourceConfig):
            raise ValueError(f"source_config must be a source config object, got {type(config).__name__}")
        if type(config) in seen:
            raise ValueError(f"source_config contains more than one {type(config).__name__}")
        seen.add(type(config))
    return configs


_T = typing.TypeVar("_T", bound=BaseSourceConfig)


def select_source_config(configs: typing.Sequence[BaseSourceConfig], config_type: type[_T]) -> _T:
    """The caller's config for this family, or a bare one reading the environment."""
    for config in configs:
        if isinstance(config, config_type):
            return config
    return config_type()
