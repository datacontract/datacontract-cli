import os

from pydantic import BaseModel


class SourceConfig(BaseModel):
    databricks: "DatabricksSourceConfig | None" = None

    def databricks_config(self) -> "DatabricksSourceConfig":
        return (self.databricks or DatabricksSourceConfig()).resolve()


class DatabricksSourceConfig(BaseModel):
    server_hostname: str | None = None
    http_path: str | None = None
    token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    profile: str | None = None
    auth_type: str | None = None

    def resolve(self) -> "DatabricksSourceConfig":
        """Fill missing values from env vars."""
        env = os.getenv
        return DatabricksSourceConfig(
            server_hostname=self.server_hostname or env("DATACONTRACT_DATABRICKS_SERVER_HOSTNAME"),
            http_path=self.http_path or env("DATACONTRACT_DATABRICKS_HTTP_PATH"),
            token=self.token or env("DATACONTRACT_DATABRICKS_TOKEN"),
            client_id=self.client_id or env("DATACONTRACT_DATABRICKS_CLIENT_ID"),
            client_secret=self.client_secret or env("DATACONTRACT_DATABRICKS_CLIENT_SECRET"),
            profile=self.profile or env("DATACONTRACT_DATABRICKS_PROFILE"),
            auth_type=self.auth_type or env("DATACONTRACT_DATABRICKS_AUTH_TYPE"),
        )
