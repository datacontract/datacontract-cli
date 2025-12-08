import os

import yaml


def _get_bool_env(name: str, default: bool) -> bool:
    """
    Helper to read a boolean from an environment variable.

    Accepts: 1/0, true/false, yes/no, on/off (case-insensitive).
    """
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "y", "on")


def to_impala_soda_configuration(server):
    """
    Build a Soda configuration for an Impala data source.

    Expects the datacontract `server` block to have at least:
      - type   (e.g. "impala")
      - host
      - port   (optional; defaults to 443 if not set)

    Credentials are taken from environment variables:
      - DATACONTRACT_IMPALA_USERNAME
      - DATACONTRACT_IMPALA_PASSWORD

    Connection behaviour can be overridden via:
      - DATACONTRACT_IMPALA_USE_SSL            (default: true)
      - DATACONTRACT_IMPALA_AUTH_MECHANISM     (default: "LDAP")
      - DATACONTRACT_IMPALA_USE_HTTP_TRANSPORT (default: true)
      - DATACONTRACT_IMPALA_HTTP_PATH          (default: "cliservice")
    """

    port = getattr(server, "port", None)
    if port is None:
        port = 443

    # Optional database / schema default, e.g. "edpdevs_scratch"
    database = getattr(server, "database", None)

    use_ssl = _get_bool_env("DATACONTRACT_IMPALA_USE_SSL", True)
    auth_mechanism = os.getenv("DATACONTRACT_IMPALA_AUTH_MECHANISM", "LDAP")
    use_http_transport = _get_bool_env(
        "DATACONTRACT_IMPALA_USE_HTTP_TRANSPORT", True
    )
    http_path = os.getenv("DATACONTRACT_IMPALA_HTTP_PATH", "cliservice")

    connection = {
        "host": server.host,
        "port": str(port),
        "username": os.getenv("DATACONTRACT_IMPALA_USERNAME"),
        "password": os.getenv("DATACONTRACT_IMPALA_PASSWORD"),
        "use_ssl": use_ssl,
        "auth_mechanism": auth_mechanism,
        "use_http_transport": use_http_transport,
        "http_path": http_path,
    }

    if database:
        connection["database"] = database

    soda_configuration = {
        f"data_source {server.type}": {
            "type": "impala",
            "connection": connection,
        }
    }

    soda_configuration_str = yaml.dump(soda_configuration)
    return soda_configuration_str
