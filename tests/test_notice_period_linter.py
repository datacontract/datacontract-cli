import datacontract.model.data_contract_specification as spec
from datacontract.lint.linters.notice_period_linter import NoticePeriodLinter
from datacontract.model.run import Check


def construct_error_check(msg: str) -> Check:
    return Check(
        type="lint",
        name="Linter 'noticePeriod in ISO8601 format'",
        result="warning",
        engine="datacontract",
        reason=msg,
    )


success_check = Check(
    type="lint", name="Linter 'noticePeriod in ISO8601 format'", result="passed", engine="datacontract"
)


def test_lint_correct_period():
    specification = spec.DataContractSpecification()
    specification.terms = spec.Terms(noticePeriod="P1M")
    result = NoticePeriodLinter().lint(specification)
    assert result == [success_check]


def test_lint_empty_period():
    # This returns a warning that's currently ignored.
    # If warnings are treated differently, change this spec.
    specification = spec.DataContractSpecification(terms=spec.Terms())
    result = NoticePeriodLinter().lint(specification)
    assert result == [success_check]


def test_lint_incorrect_period():
    # This returns a warning that's currently ignored.
    # If warnings are treated differently, change this spec.
    specification = spec.DataContractSpecification(terms=spec.Terms(noticePeriod="P0"))
    result = NoticePeriodLinter().lint(specification)
    assert result == [construct_error_check("Notice period 'P0' is not a valid ISO8601 duration.")]


def test_lint_correct_datetime_period():
    specification = spec.DataContractSpecification(terms=spec.Terms(noticePeriod="P00000001T000001"))
    result = NoticePeriodLinter().lint(specification)
    assert result == [success_check]
