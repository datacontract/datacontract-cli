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


def test_run_present_matches_uppercase_column_for_lowercase_contract_field():
    run = _run_with_stubbed_check()
    spec = CheckSpec(
        key="k",
        category="schema",
        type="field_is_present",
        name="field is present",
        model="checks_testcase",
        field="ctc_id",
        metric=MetricType.FIELD_PRESENT,
    )

    _run_present(run, _NoLookupConnection(), "checks_testcase", {"ctc_id": "CTC_ID"}, {"CTC_ID": "int64"}, spec)

    assert run.checks[0].result == ResultEnum.passed


def test_run_present_matches_uppercase_nested_field_for_lowercase_contract_path():
    import ibis

    run = _run_with_stubbed_check()
    spec = CheckSpec(
        key="k",
        category="schema",
        type="field_is_present",
        name="field is present",
        model="checks_testcase",
        field="customer.name",
        metric=MetricType.FIELD_PRESENT,
    )
    schema = ibis.memtable({"CUSTOMER": [{"NAME": "a"}]}).schema()

    _run_present(run, _NoLookupConnection(), "checks_testcase", {"customer": "CUSTOMER"}, schema, spec)

    assert run.checks[0].result == ResultEnum.passed


def _physical_type_spec(field: str) -> CheckSpec:
    from open_data_contract_standard.model import SchemaProperty

    return CheckSpec(
        key="k",
        category="schema",
        type="field_physical_type",
        name="physical type",
        model="orders",
        field=field,
        metric=MetricType.FIELD_PHYSICAL_TYPE,
        expected_category="DECIMAL(10,2)",
        expected_physical_type="DECIMAL(10,2)",
        expected_type_label="DECIMAL(10,2)",
        expected_schema_property=SchemaProperty(name=field, logicalType="number"),
    )


def test_physical_type_of_a_nested_path_is_skipped_rather_than_passed_on_the_fallback():
    # fetch_native_types only reads top-level columns, so a nested path has no
    # native type to compare against. The logicalType fallback would report a
    # mismatched physical type as passed.
    import ibis
    from open_data_contract_standard.model import Server

    from datacontract.engines.ibis.ibis_check_execute import _run_physical_type

    schema = ibis.schema({"price": "float64", "orders": "array<struct<price:float64>>"})
    native_types = {"price": "DOUBLE", "orders": "ARRAY<STRUCT<price: DOUBLE>>"}
    server = Server(server="s", type="databricks")

    run = Run.create_run()
    run.checks = [Check(type="field_physical_type", key="k")]
    _run_physical_type(run, None, server, schema, native_types, _physical_type_spec("orders[].price"))
    assert run.checks[0].result == ResultEnum.warning
    assert "skipping the physical type check" in run.checks[0].reason

    # the same mismatch on a top-level column is still a real comparison
    run = Run.create_run()
    run.checks = [Check(type="field_physical_type", key="k")]
    _run_physical_type(run, None, server, schema, native_types, _physical_type_spec("price"))
    assert run.checks[0].result == ResultEnum.failed
