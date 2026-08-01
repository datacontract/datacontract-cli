"""Resolution of config values: active programmatic config first, then the environment.

The active config is held in a :class:`~contextvars.ContextVar` keyed by the
env var names. ContextVars propagate per thread and per asyncio task, so
concurrent operations with different credentials do not interfere.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar

_context_config: ContextVar[dict[str, str]] = ContextVar("datacontract_config", default={})


def getenv(key: str, default: str | None = None) -> str | None:
    """Return a config value: active programmatic config first, then the environment."""
    value = _context_config.get().get(key)
    if value is not None:
        return value
    return os.environ.get(key, default)


@contextmanager
def config_context(config):
    """Activate ``config`` for the duration of the block.

    Accepts a :class:`~datacontract.config.Config` (flattened via its
    ``to_env_dict()``), a plain dict keyed by env var names (used as-is,
    unvalidated), or ``None`` (no-op).
    """
    if config is None:
        yield
        return
    values = config.to_env_dict() if hasattr(config, "to_env_dict") else dict(config)
    token = _context_config.set(values)
    try:
        yield
    finally:
        _context_config.reset(token)
