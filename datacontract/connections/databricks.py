"""Databricks SQL and SDK connections without an Ibis dependency.

Configuration is resolved once so SQL and Unity Catalog use the same destination
and credential selection. Creating settings does not authenticate or open a session.
Callers own returned connections and must close SQL connections when finished.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from datacontract.config import Config


@dataclass(frozen=True)
class DatabricksConnectionSettings:
    """Resolved connection settings; secrets are excluded from representations."""

    host: str | None = None
    http_path: str | None = None
    token: str | None = field(default=None, repr=False)
    catalog: str | None = None
    schema: str | None = None
    client_id: str | None = None
    client_secret: str | None = field(default=None, repr=False)
    profile: str | None = None
    auth_type: str | None = None

    @classmethod
    def from_config(
        cls,
        config: Config | dict[str, str] | None = None,
        *,
        host: str | None = None,
        catalog: str | None = None,
        schema: str | None = None,
    ) -> "DatabricksConnectionSettings":
        """Resolve upstream configuration, using server fields as fallbacks."""
        config = Config.resolve(config)
        return cls(
            host=config.get_databricks_server_hostname() or host,
            http_path=config.get_databricks_http_path(),
            token=config.get_databricks_token(),
            catalog=config.get_databricks_catalog() or catalog,
            schema=config.get_databricks_schema() or schema,
            client_id=config.get_databricks_client_id(),
            client_secret=config.get_databricks_client_secret(),
            profile=config.get_databricks_profile(),
            auth_type=config.get_databricks_auth_type(),
        )

    def _auth(self) -> str:
        if self.token:
            return "pat"
        if self.client_id or self.client_secret:
            if not (self.client_id and self.client_secret):
                raise ValueError("Databricks OAuth requires both client ID and client secret.")
            return "oauth-m2m"
        if self.profile:
            return "profile"
        if self.auth_type:
            return self.auth_type
        raise ValueError(
            "Databricks credentials are missing. Set DATACONTRACT_DATABRICKS_TOKEN, "
            "OAuth credentials, a profile or an auth type."
        )

    def _host(self) -> str:
        if not self.host:
            raise ValueError("Databricks host is missing.")
        host = self.host.removeprefix("https://").removeprefix("http://").rstrip("/")
        if not host or "/" in host or "@" in host:
            raise ValueError("Databricks host must be a workspace hostname.")
        return host

    def _sdk_options(self) -> dict[str, Any]:
        auth = self._auth()
        options: dict[str, Any] = {"host": f"https://{self._host()}"}
        if auth == "pat":
            if not self.token:
                raise ValueError("Databricks PAT authentication requires a token.")
            options.update(auth_type="pat", token=self.token)
        elif auth == "oauth-m2m":
            if not (self.client_id and self.client_secret):
                raise ValueError("Databricks OAuth requires both client ID and client secret.")
            options.update(auth_type=auth, client_id=self.client_id, client_secret=self.client_secret)
        elif auth == "profile":
            options["profile"] = self.profile
        else:
            options["auth_type"] = "oauth-u2m" if auth == "databricks-oauth" else auth
            options["token"] = None
        return options

    def _provider(self) -> Callable[[], Callable[[], dict[str, str]]]:
        options = self._sdk_options()

        def provider() -> Callable[[], dict[str, str]]:
            from databricks.sdk.core import Config as SdkConfig

            try:
                config = SdkConfig(**options)
                if options.get("auth_type") == "oauth-m2m":
                    from databricks.sdk.core import oauth_service_principal

                    authenticate = oauth_service_principal(config) or config.authenticate
                else:
                    authenticate = config.authenticate
            except Exception:
                raise RuntimeError("Databricks authentication failed; check credentials or az login.") from None

            def headers() -> dict[str, str]:
                try:
                    return authenticate()
                except Exception:
                    raise RuntimeError("Databricks credential refresh failed; check credentials or az login.") from None

            return headers

        return provider

    def sql_options(self) -> dict[str, Any]:
        """Build SQL connector arguments without connecting or creating volumes."""
        host = self._host()
        if not self.http_path:
            raise ValueError("Databricks HTTP path is missing.")
        options: dict[str, Any] = {
            "server_hostname": host,
            "http_path": self.http_path,
            "catalog": self.catalog,
            "schema": self.schema,
        }
        auth = self._auth()
        if auth == "pat":
            if not self.token:
                raise ValueError("Databricks PAT authentication requires a token.")
            options["access_token"] = self.token
        elif auth == "databricks-oauth":
            options["auth_type"] = auth
        else:
            options["credentials_provider"] = self._provider()
        return options

    def connect_sql(self) -> Any:
        """Open a raw Databricks SQL connection. Requires databricks-sql-connector."""
        options = self.sql_options()
        import databricks.sql as sql

        return sql.connect(**options)

    def workspace_client(self) -> Any:
        """Open an SDK client using the same resolved host and authentication."""
        options = self._sdk_options()
        from databricks.sdk import WorkspaceClient

        return WorkspaceClient(**options)
