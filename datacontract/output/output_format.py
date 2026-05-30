from enum import Enum
from pathlib import Path
from typing import Optional


class OutputFormat(str, Enum):
    json = "json"
    junit = "junit"

    @classmethod
    def get_supported_formats(cls):
        return list(map(lambda c: c.value, cls))

    @classmethod
    def infer_from_output_path(cls, output_path: Path) -> Optional["OutputFormat"]:
        suffix = output_path.suffix.lower()
        if suffix == ".json":
            return cls.json
        if suffix == ".xml":
            return cls.junit
        return None
