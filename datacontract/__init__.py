# Configuration so that yaml.safe_dump dumps strings with line breaks with yaml literal |
import yaml

yaml.SafeDumper.org_represent_str = yaml.SafeDumper.represent_str


def repr_str(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.org_represent_str(data)


yaml.add_representer(str, repr_str, Dumper=yaml.SafeDumper)
