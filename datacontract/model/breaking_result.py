from typing import List

from pydantic import BaseModel


class Location(BaseModel):
    path: str
    model: str


class BreakingResult(BaseModel):
    description: str
    severity: str
    check_name: str
    location: Location

    def __str__(self) -> str:
        return f"""{self.severity}	\[{self.check_name}] at {self.location.path}
        in model {self.location.model}
            {self.description}"""


class BreakingResults(BaseModel):
    breaking_results: List[BreakingResult]

    def __str__(self) -> str:
        first_line = f"{len(self.breaking_results)} breaking changes: {len(self.breaking_results)} error, 0 warning\n"
        return first_line + str.join("\n", map(lambda x: str(x), self.breaking_results))

#
# [
#     {
#         "description": "removed the field updated_at",
#         "check_name": "field-removed",
#         "severity": "error",
#         "location": {
#             "path": "./examples/breaking/datacontract-v2.yaml",
#             "model": "my_table",
#         }
#     }
# ]
