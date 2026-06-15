from datacontract.data_contract import DataContract


def test_sql_quality_fallback_does_not_close_connection():
    """A query-based quality check whose SQL ibis cannot round-trip falls back to
    raw_sql. The fallback must not make the following checks fail."""
    data_contract = DataContract(data_contract_file="fixtures/quality-local-fallback/datacontract.yaml")

    run = data_contract.test()

    print(run.pretty())
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)
