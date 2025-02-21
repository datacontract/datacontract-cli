from enum import Enum


class OutputFormat(str, Enum):
    # json = "json" # coming soon
    junit = "junit"

    @classmethod
    def get_supported_formats(cls):
        return list(map(lambda c: c.value, cls))
