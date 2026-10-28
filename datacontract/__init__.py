# Configuration so that yaml.safe_dump dumps strings with line breaks with yaml literal |
import warnings

import yaml

yaml.SafeDumper.org_represent_str = yaml.SafeDumper.represent_str


def repr_str(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.org_represent_str(data)


yaml.add_representer(str, repr_str, Dumper=yaml.SafeDumper)

# snowflake-connector-python 5.x warns on every connection about a changing logout default, and about the 4.x
# parameter names we keep passing because Python 3.10 installs still get 4.x.
warnings.filterwarnings(
    "ignore", message="enable_server_session_keep_alive_auto_detection was not set", category=FutureWarning
)
warnings.filterwarnings(
    "ignore",
    message="'(private_key_file_pwd|network_timeout|socket_timeout)' is deprecated",
    category=DeprecationWarning,
)

from datacontract.config import Config  # noqa: E402

__all__ = ["Config"]
