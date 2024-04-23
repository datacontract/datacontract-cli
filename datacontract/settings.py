from os.path import dirname
from typing import Optional, Dict, Any
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, BaseModel

from datacontract.storage import DataContractStorageRegistry, BaseDataContractStorage


class SodaBigQueryConnectionSettings(BaseModel):
    """
    The settings for the bigquery connection.
    """

    bigquery_Account_info_json_path: Optional[str] = Field(
        default=None,
        description="The path to the json file containing the account info.",
    )


class SodaDatabricksConnectionSettings(BaseModel):
    """
    The settings for the databricks connection.
    """

    databricks_http_path: Optional[str] = Field(
        default=None,
        description="The http path for the databricks connection.",
    )
    databricks_token: Optional[str] = Field(
        default=None,
        description="The token for the databricks connection.",
    )


class SodaKafkaConnectionSettings(BaseModel):
    """
    The settings for the kafka connection.
    """

    kafka_sasl_username: Optional[str] = Field(
        default=None,
        description="The username for the kafka connection.",
    )
    kafka_sasl_password: Optional[str] = Field(
        default=None,
        description="The password for the kafka connection.",
    )


class SodaConnectionSettings(BaseModel):
    """
    The settings for the soda connection.

    This class is responsible for storing the settings for the soda connection loaded from environment variables.
    """

    bigquery: SodaBigQueryConnectionSettings = Field(
        default_factory=SodaBigQueryConnectionSettings,
        description="The settings for the bigquery connection.",
    )
    databricks: SodaDatabricksConnectionSettings = Field(
        default_factory=SodaDatabricksConnectionSettings,
        description="The settings for the databricks connection.",
    )
    kafka: SodaKafkaConnectionSettings = Field(
        default_factory=SodaKafkaConnectionSettings,
        description="The settings for the kafka connection.",
    )
    # TODO: Add the rest of the connection settings here.


class StorageSettings(BaseModel):
    """
    The settings for the data contract storage.
    """

    storage_class: Optional[str] = Field(
        default="local",
        description="The storage class to use for the data contract file.",
    )

    storage_options: Optional[Dict[str, Any]] = Field(
        default={"path": "datacontract_files"},
        description="The options to pass to the storage class. Json string format.",
    )

    def build_storage_class(self) -> BaseDataContractStorage:
        """
        Get the storage class.
        """
        return DataContractStorageRegistry.get_storage(self.storage_class)(**self.storage_options)


class CLISettings(BaseSettings):
    """
    The settings for the CLI.

    This class is responsible for storing the settings for the CLI loaded from environment variables.

    See: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
    """

    model_config = SettingsConfigDict(
        env_prefix="DATACONTRACT_",
        case_sensitive=False,
        env_nested_delimiter="__",
        env_file=Path(dirname(__file__)).parent / ".datacontract.env",
        env_file_encoding="utf-8",
    )

    default_template_url: str = Field(
        default="https://datacontract.com/datacontract.init.yaml",
        description="The default data contract template url.",
    )

    storage: StorageSettings = Field(
        default_factory=StorageSettings,
        description="The settings for the data contract storage.",
    )

    soda: SodaConnectionSettings = Field(
        default_factory=SodaConnectionSettings,
        description="The settings for the soda connection.",
    )
