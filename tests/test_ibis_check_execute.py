from datacontract.engines.checks.check_spec import CheckSpec, MetricType
from datacontract.engines.ibis.ibis_check_execute import _run_present
from datacontract.model.run import Check, ResultEnum, Run


class _FakeTable:
    def __init__(self, schema):
        self._schema = schema

    def schema(self):
        return self._schema


class _NoLookupConnection:
    def table(self, _name):
        raise AssertionError("table() should not be called for non-raw field presence checks")


class _CaseSensitiveConnection:
    def __init__(self, tables):
        self._tables = tables

    def table(self, name):
        if name in self._tables:
            return self._tables[name]
        raise KeyError(name)

    def list_tables(self):
        return list(self._tables.keys())


def _run_with_stubbed_check(key: str = "k") -> Run:
    run = Run.create_run()
    run.checks = [Check(type="field_is_present", key=key)]
    return run


def test_run_present_uses_resolved_schema_without_extra_lookup():
    run = _run_with_stubbed_check()
    spec = CheckSpec(
        key="k",
        category="schema",
        type="field_is_present",
        name="field is present",
        model="checks_testcase",
        field="CTC_ID",
        metric=MetricType.FIELD_PRESENT,
    )

    _run_present(run, _NoLookupConnection(), "checks_testcase", {"ctc_id": "CTC_ID"}, {"CTC_ID": "int64"}, spec)

    assert run.checks[0].result == ResultEnum.passed


def test_run_present_raw_view_falls_back_to_model_with_case_insensitive_resolution():
    run = _run_with_stubbed_check()
    spec = CheckSpec(
        key="k",
        category="schema",
        type="field_is_present",
        name="field is present",
        model="checks_testcase",
        field="CTC_ID",
        metric=MetricType.FIELD_PRESENT,
        uses_raw_view=True,
    )
    con = _CaseSensitiveConnection({"CHECKS_TESTCASE": _FakeTable({"CTC_ID": "int64"})})

    _run_present(run, con, "checks_testcase", {"ctc_id": "CTC_ID"}, {"IGNORED": "int64"}, spec)

    assert run.checks[0].result == ResultEnum.passed
