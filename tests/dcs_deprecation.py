from datacontract.model.run import Check, ResultEnum, Run

DCS_DEPRECATION = "Check that data contract is an ODCS contract"


def without_dcs_deprecation(run: Run) -> list[Check]:
    """Assert that the run warns about the DCS deprecation exactly once, and return its other checks."""
    deprecations = [check for check in run.checks if check.name == DCS_DEPRECATION]
    assert [check.result for check in deprecations] == [ResultEnum.warning]
    return [check for check in run.checks if check.name != DCS_DEPRECATION]


def assert_dcs_deprecation_is_the_only_warning(run: Run):
    assert run.result == ResultEnum.warning
    assert not any(check.result == ResultEnum.warning for check in without_dcs_deprecation(run))
