import re

from datacontract.model.data_contract_specification import DataContractSpecification

from ..lint import Linter, LinterResult


class NoticePeriodLinter(Linter):
    @property
    def name(self) -> str:
        return "noticePeriod in ISO8601 format"

    @property
    def id(self) -> str:
        return "notice-period"

    # Regex matching the "simple" ISO8601 duration format
    simple = re.compile(
        r"""P             # Introduces period
        (:?[0-9\.,]+Y)?   # Number of years
        (:?[0-9\.,]+M)?   # Number of months
        (:?[0-9\.,]+W)?   # Number of weeks
        (:?[0-9\.,]+D)?   # Number of days
        (:?               # Time part (optional)
          T               # Always starts with T
          (:?[0-9\.,]+H)? # Number of hours
          (:?[0-9\.,]+M)? # Number of minutes
          (:?[0-9\.,]+S)? # Number of seconds
        )?
        """,
        re.VERBOSE,
    )
    datetime_basic = re.compile(r"P\d{8}T\d{6}")
    datetime_extended = re.compile(r"P\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def lint_implementation(self, contract: DataContractSpecification) -> LinterResult:
        """Check whether the notice period is specified using ISO8601 duration syntax."""
        if not contract.terms:
            return LinterResult.cautious("No terms defined.")
        period = contract.terms.noticePeriod
        if not period:
            return LinterResult.cautious("No notice period defined.")
        if not period.startswith("P"):
            return LinterResult.erroneous(f"Notice period '{period}' is not a valid" "ISO8601 duration.")
        if period == "P":
            return LinterResult.erroneous(
                "Notice period 'P' is not a valid" "ISO8601 duration, requires at least one" "duration to be specified."
            )
        if (
            not self.simple.fullmatch(period)
            and not self.datetime_basic.fullmatch(period)
            and not self.datetime_extended.fullmatch(period)
        ):
            return LinterResult.erroneous(f"Notice period '{period}' is not a valid ISO8601 duration.")
        return LinterResult()
