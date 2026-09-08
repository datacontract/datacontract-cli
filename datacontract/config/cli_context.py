"""Holds the Config loaded from the CLI's --config-file option.

The Typer callback loads the file once per process; command implementations pass
the result explicitly into DataContract. Library users never touch this: they
pass ``config=`` directly.
"""

from datacontract.config.settings import Config

_cli_config: Config | None = None


def set_cli_config(config: Config | None) -> None:
    global _cli_config
    _cli_config = config


def cli_config() -> Config | None:
    return _cli_config
