from enum import Enum


class OutputFormat(str, Enum):
    json = "json"
    junit = "junit"

    @classmethod
    def get_supported_formats(cls):
        return list(map(lambda c: c.value, cls))
