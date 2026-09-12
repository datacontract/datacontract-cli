from datacontract.data_contract import DataContract
from datacontract.engines.ibis.ibis_check_execute import _run_scalar


class _FakeRow:
    """A result row that supports integer indexing, like a BigQuery Row."""

    def __init__(self, values):
        self._values = values

    def __getitem__(self, idx):
        return self._values[idx]


class _RowIterator:
    """Mimics BigQuery's RowIterator: iterable, but no DBAPI fetchone()."""

    def __init__(self, rows):
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)


class _FakeBigQueryConnection:
    def sql(self, query, dialect=None):
        # Force the raw_sql fallback, as happens on BigQuery for queries
        # ibis cannot round-trip.
        raise NotImplementedError("ibis cannot round-trip this query")

    def raw_sql(self, query):
        return _RowIterator([_FakeRow([42])])


def test_run_scalar_fallback_handles_iterable_result_without_fetchone():
    """The raw_sql fallback must support backends like BigQuery whose result is an
    iterable RowIterator rather than a DBAPI cursor with fetchone() (DMM-457)."""
    assert _run_scalar(_FakeBigQueryConnection(), "SELECT count(*) FROM t", None) == 42


def test_sql_quality_fallback_does_not_close_connection():
    """A query-based quality check whose SQL ibis cannot round-trip falls back to
    raw_sql. The fallback must not make the following checks fail."""
    data_contract = DataContract(data_contract_file="fixtures/quality-local-fallback/datacontract.yaml")

    run = data_contract.test()

    print(run.pretty())
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)
