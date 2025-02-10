from datacontract.engines.data_contract_checks import period_to_seconds


def test_period_to_seconds():
    assert period_to_seconds("P1Y") == 31536000
    assert period_to_seconds("P1D") == 86400
    assert period_to_seconds("PT24H") == 86400
    assert period_to_seconds("1d") == 86400
    assert period_to_seconds("24h") == 86400
    assert period_to_seconds("60m") == 3600
