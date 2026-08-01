"""Programmatic configuration for credentials and connection options.

All connection credentials and options the CLI reads from ``DATACONTRACT_*``
environment variables can also be provided programmatically through
:class:`Config` (or a plain dict keyed by the env var names) via
``DataContract(config=...)``.

The config object is passed explicitly through the call stack; every read goes
through :meth:`Config.getenv`, which falls back to the process environment for
values the config does not set.
"""

from datacontract.config.settings import Config, env_name, known_env_names, unknown_snowflake_env_names

__all__ = [
    "Config",
    "env_name",
    "known_env_names",
    "unknown_snowflake_env_names",
]
