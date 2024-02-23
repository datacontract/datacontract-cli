from typing import List

from pydantic import BaseModel


class Location(BaseModel):
    path: str
    composition: List[str]


class BreakingResult(BaseModel):
    description: str
    severity: str
    check_name: str
    location: Location

    def __str__(self) -> str:
        return f"""{self.severity}\t\[{self.check_name}] at {self.location.path}
        in {str.join(" -> ", self.location.composition)}
            {self.description}"""


class BreakingResults(BaseModel):
    breaking_results: List[BreakingResult]

    def __str__(self) -> str:
        changes_amount = len(self.breaking_results)
        errors = len(list(filter(lambda x: x.severity == "error", self.breaking_results)))
        warnings = len(list(filter(lambda x: x.severity == "warning", self.breaking_results)))

        headline = f"{changes_amount} breaking changes: {errors} error, {warnings} warning\n"
        content = str.join("\n\n", map(lambda x: str(x), self.breaking_results))

        return headline + content

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
