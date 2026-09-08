"""The typed Config class: one field per supported ``DATACONTRACT_*`` option."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_ENV_PREFIX = "DATACONTRACT_"

# Deprecated option (field name) -> replacement (field name). Single source for
# the accessor warnings, the Snowflake connect synonyms, and the generated docs.
DEPRECATED_OPTIONS = {
    "datamesh_manager_api_key": "entropy_data_api_key",
    "datamesh_manager_host": "entropy_data_host",
    "datacontract_manager_api_key": "entropy_data_api_key",
    "datacontract_manager_host": "entropy_data_host",
    "snowflake_private_key_path": "snowflake_private_key_file",
    "snowflake_private_key_passphrase": "snowflake_private_key_file_pwd",
    "snowflake_connection_timeout": "snowflake_login_timeout",
}
_TRUTHY = ("1", "true", "yes", "y", "on")

# Config option (field name) -> the property in the contract's ``servers`` block
# it overrides when set. Single source for the generated docs notes.
SERVER_OVERRIDE_OPTIONS = {
    "athena_catalog": "catalog",
    "athena_schema": "schema",
    "athena_staging_dir": "stagingDir",
    "athena_workgroup": "workgroup",
    "bigquery_project": "project",
    "bigquery_dataset": "dataset",
    "databricks_server_hostname": "host",
    "databricks_catalog": "catalog",
    "databricks_schema": "schema",
    "duckdb_database": "database",
    "duckdb_schema": "schema",
    "iceberg_catalog_url": "catalogUrl",
    "iceberg_catalog": "catalog",
    "iceberg_namespace": "namespace",
    "iceberg_warehouse": "warehouse",
    "impala_host": "host",
    "impala_port": "port",
    "impala_database": "database",
    "mysql_host": "host",
    "mysql_port": "port",
    "mysql_database": "database",
    "oracle_host": "host",
    "oracle_port": "port",
    "oracle_service_name": "serviceName",
    "postgres_host": "host",
    "postgres_port": "port",
    "postgres_database": "database",
    "postgres_schema": "schema",
    "redshift_host": "host",
    "redshift_port": "port",
    "redshift_database": "database",
    "redshift_schema": "schema",
    "snowflake_account": "account",
    "snowflake_database": "database",
    "snowflake_schema": "schema",
    "sqlserver_host": "host",
    "sqlserver_port": "port",
    "sqlserver_database": "database",
    "trino_host": "host",
    "trino_port": "port",
    "trino_catalog": "catalog",
    "trino_schema": "schema",
}


class Config(BaseSettings):
    """All defined config options, one typed field per ``DATACONTRACT_*`` env var.

    Field names map to env var names by upper-casing and prefixing with
    ``DATACONTRACT_`` (``snowflake_username`` ↔ ``DATACONTRACT_SNOWFLAKE_USERNAME``),
    except where a ``validation_alias`` says otherwise. Instantiation reads the
    environment, so ``Config()`` is a snapshot of the current env and constructor
    keyword arguments override it. Unknown keyword arguments raise immediately;
    unrelated environment variables are ignored.
    """

    # populate_by_name lets the aliased fields (validation_alias, e.g.
    # ENTROPY_DATA_API_KEY) also be set via their field name in the constructor.
    model_config = SettingsConfigDict(env_prefix=_ENV_PREFIX, extra="ignore", populate_by_name=True)

    # Entropy Data / Data Mesh Manager / Data Contract Manager (publishing, contract URLs)
    entropy_data_api_key: SecretStr | None = Field(None, validation_alias="ENTROPY_DATA_API_KEY")
    entropy_data_host: str | None = Field(None, validation_alias="ENTROPY_DATA_HOST")
    # deprecated synonyms for the entropy_data_* options (pre-rebrand product names);
    # a warning is emitted when one of them supplies a value
    datamesh_manager_api_key: SecretStr | None = Field(None, validation_alias="DATAMESH_MANAGER_API_KEY")
    datamesh_manager_host: str | None = Field(None, validation_alias="DATAMESH_MANAGER_HOST")
    datacontract_manager_api_key: SecretStr | None = Field(None, validation_alias="DATACONTRACT_MANAGER_API_KEY")
    datacontract_manager_host: str | None = Field(None, validation_alias="DATACONTRACT_MANAGER_HOST")

    # general
    api_header_authorization: SecretStr | None = None
    max_errors: int | None = None

    # athena (credentials come from the s3_* options)
    # overrides for the contract's servers block
    athena_catalog: str | None = None
    athena_schema: str | None = None
    athena_staging_dir: str | None = None
    athena_workgroup: str | None = None

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
    # overrides for the contract's servers block
    bigquery_project: str | None = None
    bigquery_dataset: str | None = None

    # databricks
    databricks_server_hostname: str | None = None
    databricks_http_path: str | None = None
    databricks_token: SecretStr | None = None
    databricks_client_id: str | None = None
    databricks_client_secret: SecretStr | None = None
    databricks_profile: str | None = None
    databricks_auth_type: str | None = None
    # overrides for the contract's servers block
    databricks_catalog: str | None = None
    databricks_schema: str | None = None

    # duckdb
    # overrides for the contract's servers block
    duckdb_database: str | None = None
    duckdb_schema: str | None = None

    # gcs
    gcs_key_id: str | None = None
    gcs_secret: SecretStr | None = None

    # iceberg (REST catalog by default; data files use the s3_* options)
    iceberg_catalog_type: str | None = None
    iceberg_credential: SecretStr | None = None
    iceberg_token: SecretStr | None = None
    iceberg_s3_endpoint: str | None = None
    iceberg_signing_name: str | None = None
    iceberg_properties: str | None = None
    # overrides for the contract's servers block
    iceberg_catalog_url: str | None = None
    iceberg_catalog: str | None = None
    iceberg_namespace: str | None = None
    iceberg_warehouse: str | None = None

    # impala
    impala_username: str | None = None
    impala_password: SecretStr | None = None
    impala_auth_mechanism: str | None = None
    impala_http_path: str | None = None
    impala_use_ssl: bool | None = None
    impala_use_http_transport: bool | None = None
    # overrides for the contract's servers block
    impala_host: str | None = None
    impala_port: int | None = None
    impala_database: str | None = None

    # kafka
    kafka_sasl_username: str | None = None
    kafka_sasl_password: SecretStr | None = None
    kafka_sasl_mechanism: str | None = None
    kafka_schema_registry_url: str | None = None
    kafka_schema_registry_username: str | None = None
    kafka_schema_registry_password: SecretStr | None = None
    kafka_max_messages: int | None = None
    kafka_timeout: int | None = None
    kafka_group_prefix: str | None = None

    # mysql
    mysql_username: str | None = None
    mysql_password: SecretStr | None = None
    # overrides for the contract's servers block
    mysql_host: str | None = None
    mysql_port: int | None = None
    mysql_database: str | None = None

    # oracle
    oracle_username: str | None = None
    oracle_password: SecretStr | None = None
    oracle_client_dir: str | None = None
    # overrides for the contract's servers block
    oracle_host: str | None = None
    oracle_port: int | None = None
    oracle_service_name: str | None = None

    # postgres
    postgres_username: str | None = None
    postgres_password: SecretStr | None = None
    # overrides for the contract's servers block
    postgres_host: str | None = None
    postgres_port: int | None = None
    postgres_database: str | None = None
    postgres_schema: str | None = None

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
    # overrides for the contract's servers block
    redshift_host: str | None = None
    redshift_port: int | None = None
    redshift_database: str | None = None
    redshift_schema: str | None = None

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
    # overrides for the contract's servers block
    snowflake_account: str | None = None
    snowflake_database: str | None = None
    snowflake_schema: str | None = None

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
    # overrides for the contract's servers block
    sqlserver_host: str | None = None
    sqlserver_port: int | None = None
    sqlserver_database: str | None = None

    # trino
    trino_authentication: str | None = None
    trino_username: str | None = None
    trino_password: SecretStr | None = None
    trino_jwt_token: SecretStr | None = None
    # overrides for the contract's servers block
    trino_host: str | None = None
    trino_port: int | None = None
    trino_catalog: str | None = None
    trino_schema: str | None = None

    def __init__(self, **data):
        # extra="ignore" keeps unrelated env vars from breaking instantiation, but
        # programmatic typos must not be silently dropped with them.
        unknown = set(data) - set(type(self).model_fields)
        if unknown:
            raise ValueError(f"Unknown config option(s): {', '.join(sorted(unknown))}. See datacontract.Config.")
        super().__init__(**data)

    @classmethod
    def resolve(cls, config: "Config | dict[str, str] | None") -> "Config":
        """Normalize the ``config=`` argument to a Config instance.

        ``None`` becomes an empty Config (every read falls back to the
        environment); a dict is keyed by the env var names and validated
        against the declared fields.
        """
        if config is None:
            return cls.model_construct()
        if isinstance(config, cls):
            return config
        if isinstance(config, dict):
            reverse = {env_name(name, field): name for name, field in cls.model_fields.items()}
            fields = {}
            unknown = []
            for key, value in config.items():
                if key in reverse:
                    fields[reverse[key]] = value
                else:
                    unknown.append(key)
            if unknown:
                raise ValueError(f"Unknown config option(s): {', '.join(sorted(unknown))}. See datacontract.Config.")
            return _ExplicitConfig(**fields)
        raise TypeError(f"config must be a Config, dict, or None, got {type(config).__name__}")

    @classmethod
    def from_yaml(cls, path: "str | Path") -> "Config":
        """Load a Config from a YAML file with per-source sections.

        Nested keys join with ``_`` to form the field name (``snowflake.username``
        → ``snowflake_username``); top-level scalars address the general options
        (``max_errors``). ``${VAR}`` and ``${VAR:-default}`` references in string
        values are replaced with the environment variable's value at load time,
        so files can be committed without holding secrets. Unknown option names
        raise a ValueError.
        """
        import yaml

        path = Path(path)
        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError as e:
            raise ValueError(f"Config file {path} is not valid YAML: {e}")
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ValueError(f"Config file {path} must contain a YAML mapping.")

        flat: dict[str, object] = {}

        def walk(prefix: str, node: dict):
            for key, value in node.items():
                name = f"{prefix}_{key}" if prefix else str(key)
                if isinstance(value, dict):
                    walk(name, value)
                else:
                    flat[name] = _interpolate_env(value, path)

        walk("", data)
        unknown = sorted(set(flat) - set(cls.model_fields))
        if unknown:
            raise ValueError(f"Unknown config option(s) in {path}: {', '.join(unknown)}. See datacontract.Config.")
        return _ExplicitConfig(**flat)

    # ------------------------------------------------------------------
    # Value resolution: one typed accessor per option (get_<field>()).
    # An accessor returns the field value if set, falling back to the process
    # environment; SecretStr values are unwrapped. ``required=True`` raises a
    # DataContractException naming the env var when the value is missing.
    # ------------------------------------------------------------------

    def _raw_option(self, field_name: str):
        value = getattr(self, field_name)
        if value is None:
            value = os.environ.get(env_name(field_name, type(self).model_fields[field_name]))
        if isinstance(value, SecretStr):
            value = value.get_secret_value()
        return value

    def option_source(self, field_name: str) -> str | None:
        """Where ``get_<field_name>()`` takes its value from.

        ``"request"`` when the value is set on this Config (a per-request header,
        a config file, or a programmatic value), ``"env"`` when it falls back to
        the process environment, and ``None`` when it is unset everywhere. Used to
        keep a credential the server holds in its environment from being sent to a
        host chosen by an untrusted caller.
        """
        if getattr(self, field_name) is not None:
            return "request"
        if os.environ.get(env_name(field_name, type(self).model_fields[field_name])) is not None:
            return "env"
        return None

    def _str_option(self, field_name: str, required: bool = False) -> str | None:
        value = self._raw_option(field_name)
        value = str(value) if value is not None else None
        if required and not value:
            key = env_name(field_name, type(self).model_fields[field_name])
            server_type = field_name.split("_")[0]
            from datacontract.model.exceptions import DataContractException

            raise DataContractException(
                type=f"{server_type}-connection",
                name=f"missing_env_{key}",
                reason=f"Required configuration {key} is not set. Set the environment variable "
                f"or pass it via DataContract(config=...) to connect to {server_type}.",
                engine="datacontract-cli",
            )
        return value

    def _deprecated_str_option(
        self, field_name: str, replacement: str | None = None, required: bool = False
    ) -> str | None:
        """A str option kept as a deprecated synonym: warns when it supplies a value."""
        replacement = replacement or DEPRECATED_OPTIONS[field_name]
        value = self._str_option(field_name, required)
        if value:
            deprecated_env = env_name(field_name, type(self).model_fields[field_name])
            replacement_env = env_name(replacement, type(self).model_fields[replacement])
            logger.warning(
                "%s is deprecated and will be removed in a future release, use %s instead.",
                deprecated_env,
                replacement_env,
            )
        return value

    def _int_option(self, field_name: str) -> int | None:
        value = self._raw_option(field_name)
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            key = env_name(field_name, type(self).model_fields[field_name])
            from datacontract.model.exceptions import DataContractException

            raise DataContractException(
                type="configuration",
                name=f"invalid_{key}",
                reason=f"{key} must be a whole number, got {value!r}.",
                engine="datacontract-cli",
            )

    def _bool_option(self, field_name: str, default: bool) -> bool:
        value = self._raw_option(field_name)
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        # A set-but-empty variable counts as false, matching pre-Config parsing.
        return str(value).strip().lower() in _TRUTHY

    # --- entropy ---
    def get_entropy_data_api_key(self, required: bool = False) -> str | None:
        return self._str_option("entropy_data_api_key", required)

    def get_entropy_data_host(self, required: bool = False) -> str | None:
        return self._str_option("entropy_data_host", required)

    # --- datamesh ---
    def get_datamesh_manager_api_key(self, required: bool = False) -> str | None:
        return self._deprecated_str_option("datamesh_manager_api_key", "entropy_data_api_key", required)

    def get_datamesh_manager_host(self, required: bool = False) -> str | None:
        return self._deprecated_str_option("datamesh_manager_host", "entropy_data_host", required)

    # --- datacontract ---
    def get_datacontract_manager_api_key(self, required: bool = False) -> str | None:
        return self._deprecated_str_option("datacontract_manager_api_key", "entropy_data_api_key", required)

    def get_datacontract_manager_host(self, required: bool = False) -> str | None:
        return self._deprecated_str_option("datacontract_manager_host", "entropy_data_host", required)

    # --- api ---
    def get_api_header_authorization(self, required: bool = False) -> str | None:
        return self._str_option("api_header_authorization", required)

    # --- max ---
    def get_max_errors(self) -> int | None:
        return self._int_option("max_errors")

    # --- athena ---
    def get_athena_catalog(self, required: bool = False) -> str | None:
        return self._str_option("athena_catalog", required)

    def get_athena_schema(self, required: bool = False) -> str | None:
        return self._str_option("athena_schema", required)

    def get_athena_staging_dir(self, required: bool = False) -> str | None:
        return self._str_option("athena_staging_dir", required)

    def get_athena_workgroup(self, required: bool = False) -> str | None:
        return self._str_option("athena_workgroup", required)

    # --- azure ---
    def get_azure_connection_string(self, required: bool = False) -> str | None:
        return self._str_option("azure_connection_string", required)

    def get_azure_storage_account_key(self, required: bool = False) -> str | None:
        return self._str_option("azure_storage_account_key", required)

    def get_azure_tenant_id(self, required: bool = False) -> str | None:
        return self._str_option("azure_tenant_id", required)

    def get_azure_client_id(self, required: bool = False) -> str | None:
        return self._str_option("azure_client_id", required)

    def get_azure_client_secret(self, required: bool = False) -> str | None:
        return self._str_option("azure_client_secret", required)

    # --- bigquery ---
    def get_bigquery_account_info_json_path(self, required: bool = False) -> str | None:
        return self._str_option("bigquery_account_info_json_path", required)

    def get_bigquery_billing_project(self, required: bool = False) -> str | None:
        return self._str_option("bigquery_billing_project", required)

    def get_bigquery_impersonation_account(self, required: bool = False) -> str | None:
        return self._str_option("bigquery_impersonation_account", required)

    def get_bigquery_project(self, required: bool = False) -> str | None:
        return self._str_option("bigquery_project", required)

    def get_bigquery_dataset(self, required: bool = False) -> str | None:
        return self._str_option("bigquery_dataset", required)

    # --- databricks ---
    def get_databricks_server_hostname(self, required: bool = False) -> str | None:
        return self._str_option("databricks_server_hostname", required)

    def get_databricks_http_path(self, required: bool = False) -> str | None:
        return self._str_option("databricks_http_path", required)

    def get_databricks_token(self, required: bool = False) -> str | None:
        return self._str_option("databricks_token", required)

    def get_databricks_client_id(self, required: bool = False) -> str | None:
        return self._str_option("databricks_client_id", required)

    def get_databricks_client_secret(self, required: bool = False) -> str | None:
        return self._str_option("databricks_client_secret", required)

    def get_databricks_profile(self, required: bool = False) -> str | None:
        return self._str_option("databricks_profile", required)

    def get_databricks_auth_type(self, required: bool = False) -> str | None:
        return self._str_option("databricks_auth_type", required)

    def get_databricks_catalog(self, required: bool = False) -> str | None:
        return self._str_option("databricks_catalog", required)

    def get_databricks_schema(self, required: bool = False) -> str | None:
        return self._str_option("databricks_schema", required)

    # --- gcs ---
    def get_gcs_key_id(self, required: bool = False) -> str | None:
        return self._str_option("gcs_key_id", required)

    def get_gcs_secret(self, required: bool = False) -> str | None:
        return self._str_option("gcs_secret", required)

    # --- iceberg ---
    def get_iceberg_catalog_type(self, required: bool = False) -> str | None:
        return self._str_option("iceberg_catalog_type", required)

    def get_iceberg_s3_endpoint(self, required: bool = False) -> str | None:
        return self._str_option("iceberg_s3_endpoint", required)

    def get_iceberg_signing_name(self, required: bool = False) -> str | None:
        return self._str_option("iceberg_signing_name", required)

    def get_iceberg_properties(self, required: bool = False) -> str | None:
        return self._str_option("iceberg_properties", required)

    def get_iceberg_credential(self, required: bool = False) -> str | None:
        return self._str_option("iceberg_credential", required)

    def get_iceberg_token(self, required: bool = False) -> str | None:
        return self._str_option("iceberg_token", required)

    def get_iceberg_catalog_url(self, required: bool = False) -> str | None:
        return self._str_option("iceberg_catalog_url", required)

    def get_iceberg_catalog(self, required: bool = False) -> str | None:
        return self._str_option("iceberg_catalog", required)

    def get_iceberg_namespace(self, required: bool = False) -> str | None:
        return self._str_option("iceberg_namespace", required)

    def get_iceberg_warehouse(self, required: bool = False) -> str | None:
        return self._str_option("iceberg_warehouse", required)

    # --- impala ---
    def get_impala_username(self, required: bool = False) -> str | None:
        return self._str_option("impala_username", required)

    def get_impala_password(self, required: bool = False) -> str | None:
        return self._str_option("impala_password", required)

    def get_impala_auth_mechanism(self, required: bool = False) -> str | None:
        return self._str_option("impala_auth_mechanism", required)

    def get_impala_http_path(self, required: bool = False) -> str | None:
        return self._str_option("impala_http_path", required)

    def get_impala_use_ssl(self, default: bool = False) -> bool:
        return self._bool_option("impala_use_ssl", default)

    def get_impala_use_http_transport(self, default: bool = False) -> bool:
        return self._bool_option("impala_use_http_transport", default)

    def get_impala_host(self, required: bool = False) -> str | None:
        return self._str_option("impala_host", required)

    def get_impala_port(self) -> int | None:
        return self._int_option("impala_port")

    def get_impala_database(self, required: bool = False) -> str | None:
        return self._str_option("impala_database", required)

    # --- kafka ---
    def get_kafka_sasl_username(self, required: bool = False) -> str | None:
        return self._str_option("kafka_sasl_username", required)

    def get_kafka_sasl_password(self, required: bool = False) -> str | None:
        return self._str_option("kafka_sasl_password", required)

    def get_kafka_sasl_mechanism(self, required: bool = False) -> str | None:
        return self._str_option("kafka_sasl_mechanism", required)

    def get_kafka_schema_registry_url(self, required: bool = False) -> str | None:
        return self._str_option("kafka_schema_registry_url", required)

    def get_kafka_schema_registry_username(self, required: bool = False) -> str | None:
        return self._str_option("kafka_schema_registry_username", required)

    def get_kafka_schema_registry_password(self, required: bool = False) -> str | None:
        return self._str_option("kafka_schema_registry_password", required)

    def get_kafka_max_messages(self) -> int | None:
        return self._int_option("kafka_max_messages")

    def get_kafka_timeout(self) -> int | None:
        return self._int_option("kafka_timeout")

    def get_kafka_group_prefix(self, required: bool = False) -> str | None:
        return self._str_option("kafka_group_prefix", required)

    # --- mysql ---
    def get_mysql_username(self, required: bool = False) -> str | None:
        return self._str_option("mysql_username", required)

    def get_mysql_password(self, required: bool = False) -> str | None:
        return self._str_option("mysql_password", required)

    def get_mysql_host(self, required: bool = False) -> str | None:
        return self._str_option("mysql_host", required)

    def get_mysql_port(self) -> int | None:
        return self._int_option("mysql_port")

    def get_mysql_database(self, required: bool = False) -> str | None:
        return self._str_option("mysql_database", required)

    # --- oracle ---
    def get_oracle_username(self, required: bool = False) -> str | None:
        return self._str_option("oracle_username", required)

    def get_oracle_password(self, required: bool = False) -> str | None:
        return self._str_option("oracle_password", required)

    def get_oracle_client_dir(self, required: bool = False) -> str | None:
        return self._str_option("oracle_client_dir", required)

    def get_oracle_host(self, required: bool = False) -> str | None:
        return self._str_option("oracle_host", required)

    def get_oracle_port(self) -> int | None:
        return self._int_option("oracle_port")

    def get_oracle_service_name(self, required: bool = False) -> str | None:
        return self._str_option("oracle_service_name", required)

    # --- postgres ---
    def get_postgres_username(self, required: bool = False) -> str | None:
        return self._str_option("postgres_username", required)

    def get_postgres_password(self, required: bool = False) -> str | None:
        return self._str_option("postgres_password", required)

    def get_duckdb_database(self, required: bool = False) -> str | None:
        return self._str_option("duckdb_database", required)

    def get_duckdb_schema(self, required: bool = False) -> str | None:
        return self._str_option("duckdb_schema", required)

    def get_postgres_host(self, required: bool = False) -> str | None:
        return self._str_option("postgres_host", required)

    def get_postgres_port(self) -> int | None:
        return self._int_option("postgres_port")

    def get_postgres_database(self, required: bool = False) -> str | None:
        return self._str_option("postgres_database", required)

    def get_postgres_schema(self, required: bool = False) -> str | None:
        return self._str_option("postgres_schema", required)

    # --- redshift ---
    def get_redshift_authentication(self, required: bool = False) -> str | None:
        return self._str_option("redshift_authentication", required)

    def get_redshift_username(self, required: bool = False) -> str | None:
        return self._str_option("redshift_username", required)

    def get_redshift_password(self, required: bool = False) -> str | None:
        return self._str_option("redshift_password", required)

    def get_redshift_sslmode(self, required: bool = False) -> str | None:
        return self._str_option("redshift_sslmode", required)

    def get_redshift_db_user(self, required: bool = False) -> str | None:
        return self._str_option("redshift_db_user", required)

    def get_redshift_db_groups(self, required: bool = False) -> str | None:
        return self._str_option("redshift_db_groups", required)

    def get_redshift_auto_create(self, default: bool = False) -> bool:
        return self._bool_option("redshift_auto_create", default)

    def get_redshift_workgroup(self, required: bool = False) -> str | None:
        return self._str_option("redshift_workgroup", required)

    def get_redshift_cluster_identifier(self, required: bool = False) -> str | None:
        return self._str_option("redshift_cluster_identifier", required)

    def get_redshift_region(self, required: bool = False) -> str | None:
        return self._str_option("redshift_region", required)

    def get_redshift_duration_seconds(self) -> int | None:
        return self._int_option("redshift_duration_seconds")

    def get_redshift_host(self, required: bool = False) -> str | None:
        return self._str_option("redshift_host", required)

    def get_redshift_port(self) -> int | None:
        return self._int_option("redshift_port")

    def get_redshift_database(self, required: bool = False) -> str | None:
        return self._str_option("redshift_database", required)

    def get_redshift_schema(self, required: bool = False) -> str | None:
        return self._str_option("redshift_schema", required)

    # --- s3 ---
    def get_s3_access_key_id(self, required: bool = False) -> str | None:
        return self._str_option("s3_access_key_id", required)

    def get_s3_secret_access_key(self, required: bool = False) -> str | None:
        return self._str_option("s3_secret_access_key", required)

    def get_s3_session_token(self, required: bool = False) -> str | None:
        return self._str_option("s3_session_token", required)

    def get_s3_region(self, required: bool = False) -> str | None:
        return self._str_option("s3_region", required)

    # --- snowflake ---
    def get_snowflake_username(self, required: bool = False) -> str | None:
        return self._str_option("snowflake_username", required)

    def get_snowflake_password(self, required: bool = False) -> str | None:
        return self._str_option("snowflake_password", required)

    def get_snowflake_authenticator(self, required: bool = False) -> str | None:
        return self._str_option("snowflake_authenticator", required)

    def get_snowflake_role(self, required: bool = False) -> str | None:
        return self._str_option("snowflake_role", required)

    def get_snowflake_token(self, required: bool = False) -> str | None:
        return self._str_option("snowflake_token", required)

    def get_snowflake_passcode(self, required: bool = False) -> str | None:
        return self._str_option("snowflake_passcode", required)

    def get_snowflake_private_key(self, required: bool = False) -> str | None:
        return self._str_option("snowflake_private_key", required)

    def get_snowflake_private_key_file(self, required: bool = False) -> str | None:
        return self._str_option("snowflake_private_key_file", required)

    def get_snowflake_private_key_file_pwd(self, required: bool = False) -> str | None:
        return self._str_option("snowflake_private_key_file_pwd", required)

    def get_snowflake_warehouse(self, required: bool = False) -> str | None:
        return self._str_option("snowflake_warehouse", required)

    def get_snowflake_create_object_udfs(self, default: bool = False) -> bool:
        return self._bool_option("snowflake_create_object_udfs", default)

    def get_snowflake_login_timeout(self) -> int | None:
        return self._int_option("snowflake_login_timeout")

    def get_snowflake_network_timeout(self) -> int | None:
        return self._int_option("snowflake_network_timeout")

    def get_snowflake_socket_timeout(self) -> int | None:
        return self._int_option("snowflake_socket_timeout")

    def get_snowflake_host(self, required: bool = False) -> str | None:
        return self._str_option("snowflake_host", required)

    def get_snowflake_port(self) -> int | None:
        return self._int_option("snowflake_port")

    def get_snowflake_home(self, required: bool = False) -> str | None:
        return self._str_option("snowflake_home", required)

    def get_snowflake_connections_file(self, required: bool = False) -> str | None:
        return self._str_option("snowflake_connections_file", required)

    def get_snowflake_default_connection_name(self, required: bool = False) -> str | None:
        return self._str_option("snowflake_default_connection_name", required)

    def get_snowflake_private_key_path(self, required: bool = False) -> str | None:
        return self._str_option("snowflake_private_key_path", required)

    def get_snowflake_private_key_passphrase(self, required: bool = False) -> str | None:
        return self._str_option("snowflake_private_key_passphrase", required)

    def get_snowflake_connection_timeout(self) -> int | None:
        return self._int_option("snowflake_connection_timeout")

    def get_snowflake_account(self, required: bool = False) -> str | None:
        return self._str_option("snowflake_account", required)

    def get_snowflake_database(self, required: bool = False) -> str | None:
        return self._str_option("snowflake_database", required)

    def get_snowflake_schema(self, required: bool = False) -> str | None:
        return self._str_option("snowflake_schema", required)

    # --- sqlserver ---
    def get_sqlserver_authentication(self, required: bool = False) -> str | None:
        return self._str_option("sqlserver_authentication", required)

    def get_sqlserver_username(self, required: bool = False) -> str | None:
        return self._str_option("sqlserver_username", required)

    def get_sqlserver_password(self, required: bool = False) -> str | None:
        return self._str_option("sqlserver_password", required)

    def get_sqlserver_client_id(self, required: bool = False) -> str | None:
        return self._str_option("sqlserver_client_id", required)

    def get_sqlserver_client_secret(self, required: bool = False) -> str | None:
        return self._str_option("sqlserver_client_secret", required)

    def get_sqlserver_driver(self, required: bool = False) -> str | None:
        return self._str_option("sqlserver_driver", required)

    def get_sqlserver_encrypted_connection(self, default: bool = False) -> bool:
        return self._bool_option("sqlserver_encrypted_connection", default)

    def get_sqlserver_trust_server_certificate(self, default: bool = False) -> bool:
        return self._bool_option("sqlserver_trust_server_certificate", default)

    def get_sqlserver_trusted_connection(self, default: bool = False) -> bool:
        return self._bool_option("sqlserver_trusted_connection", default)

    def get_sqlserver_host(self, required: bool = False) -> str | None:
        return self._str_option("sqlserver_host", required)

    def get_sqlserver_port(self) -> int | None:
        return self._int_option("sqlserver_port")

    def get_sqlserver_database(self, required: bool = False) -> str | None:
        return self._str_option("sqlserver_database", required)

    # --- trino ---
    def get_trino_authentication(self, required: bool = False) -> str | None:
        return self._str_option("trino_authentication", required)

    def get_trino_username(self, required: bool = False) -> str | None:
        return self._str_option("trino_username", required)

    def get_trino_password(self, required: bool = False) -> str | None:
        return self._str_option("trino_password", required)

    def get_trino_jwt_token(self, required: bool = False) -> str | None:
        return self._str_option("trino_jwt_token", required)

    def get_trino_host(self, required: bool = False) -> str | None:
        return self._str_option("trino_host", required)

    def get_trino_port(self) -> int | None:
        return self._int_option("trino_port")

    def get_trino_catalog(self, required: bool = False) -> str | None:
        return self._str_option("trino_catalog", required)

    def get_trino_schema(self, required: bool = False) -> str | None:
        return self._str_option("trino_schema", required)

    def to_env_dict(self) -> dict[str, str]:
        """Flatten to a dict keyed by the env var names."""
        values: dict[str, str] = {}
        for name, field in type(self).model_fields.items():
            value = getattr(self, name)
            if value is None:
                continue
            values[env_name(name, field)] = _as_env_value(value)
        return values


class _ExplicitConfig(Config):
    """Config built only from explicitly provided values.

    Skips the environment settings source, so an unrelated malformed
    DATACONTRACT_* variable in the process cannot fail construction of a config
    file, dict, or per-request header config. Unset options still fall back to
    the environment lazily through the accessors, which parse each value at the
    point of use.
    """

    @classmethod
    def settings_customise_sources(
        cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings
    ):
        return (init_settings,)


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
    """``DATACONTRACT_SNOWFLAKE_*`` environment variables that no Config field declares.

    Until v1.0.16 every such variable was forwarded verbatim to the Snowflake
    connector; now only declared options are. Callers use this to warn instead
    of silently ignoring them. Programmatic config cannot contain unknown names
    (Config validates them), so only the environment is scanned.
    """
    known = known_env_names()
    return sorted(name for name in os.environ if name.startswith("DATACONTRACT_SNOWFLAKE_") and name not in known)


def _interpolate_env(value, path):
    """Replace ``${VAR}`` and ``${VAR:-default}`` references in string values with environment variable values."""
    from datacontract.config.variables import resolve_variables

    return resolve_variables(value, source=f"config file {path}")
