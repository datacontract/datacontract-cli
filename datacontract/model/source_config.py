"""Typed credentials for a source family, passable programmatically.

Each class mirrors one ``DATACONTRACT_<FAMILY>_*`` variable group. Fields passed
explicitly win per field; anything left unset falls back to the environment, so
environment-only setups keep working unchanged.
"""

from __future__ import annotations

import os
import typing

from pydantic import AliasChoices, Field, SecretStr, ValidationError, field_serializer
from pydantic_settings import BaseSettings, EnvSettingsSource, SettingsConfigDict


class BaseSourceConfig(BaseSettings):
    # populate_by_name is load-bearing: a field with a validation_alias is otherwise
    # settable only by its environment variable name, which breaks the Python API.
    model_config = SettingsConfigDict(extra="forbid", env_ignore_empty=True, populate_by_name=True)

    def __init__(__pydantic_self__, **values):
        # A rejected value is often a secret under a mistyped field name, and pydantic echoes
        # the input into the error. Re-raise with locations and messages only.
        try:
            super().__init__(**values)
        except ValidationError as e:
            details = "; ".join(
                f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
                for error in e.errors(include_url=False)
            )
        else:
            return
        # raised outside the handler so the pydantic error, which still holds the rejected
        # value, is not attached as this exception's __context__
        raise ValueError(f"invalid {type(__pydantic_self__).__name__}: {details}")


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
        prefix = self.env_prefix
        # A field's environment variable is its validation_alias if it has one (already a full
        # name, the prefix is not applied on top), otherwise the prefix plus the field name.
        declared = set()
        for name, field in self.settings_cls.model_fields.items():
            alias = field.validation_alias
            if alias is None:
                declared.add(f"{prefix}{name}".lower())
            elif isinstance(alias, str):
                declared.add(alias.lower())
            else:
                declared.update(choice.lower() for choice in alias.choices if isinstance(choice, str))
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

    # Connector parameters we do not declare, forwarded verbatim to the driver. Values can be
    # secrets the driver accepts without a field here (passcode, oauth_client_secret, ...), so
    # they are masked wherever SecretStr is: repr, str, and JSON dumps. Like SecretStr, a
    # python-mode model_dump() keeps the real values, so a config survives a dump round-trip.
    connection_parameters: dict[str, typing.Any] = Field(default_factory=dict)

    @field_serializer("connection_parameters", when_used="json")
    def _mask_connection_parameters(self, value: dict[str, typing.Any]) -> dict[str, str]:
        return dict.fromkeys(value, "**********")

    def __repr_args__(self):
        for name, value in super().__repr_args__():
            yield name, self._mask_connection_parameters(value) if name == "connection_parameters" else value

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
