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

from datacontract.config.resolution import config_context, getenv
from datacontract.config.settings import Config, env_name, known_env_names, unknown_snowflake_env_names

__all__ = [
    "Config",
    "config_context",
    "env_name",
    "getenv",
    "known_env_names",
    "unknown_snowflake_env_names",
]
