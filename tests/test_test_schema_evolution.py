from datacontract.data_contract import DataContract


def test_csv_optional_field_missing_from_old_data():
    """Optional field not present in historical CSV data should pass validation"""
    data_contract = DataContract(
        data_contract_file="fixtures/schema-evolution/odcs-datacontract-cities-version-2.yaml", server="historical-csv"
    )

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)


def test_csv_optional_field_present_in_new_data():
    """Optional field present in new CSV data should pass validation"""
    data_contract = DataContract(
        data_contract_file="fixtures/schema-evolution/odcs-datacontract-cities-version-2.yaml", server="current-csv")

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)

def test_data_from_historical_and_current_schema_csv_mixed():
    """Combining CSV data written with historical and current schema passes validation"""
    data_contract = DataContract(
        data_contract_file="fixtures/schema-evolution/odcs-datacontract-cities-version-2.yaml", server="mixed-schema-csv")

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)

def test_csv_optional_field_with_invalid_values():
    """Optional field in CSV with invalid values should fail validation"""
    data_contract = DataContract(
        data_contract_file="fixtures/schema-evolution/odcs-datacontract-cities-version-2.yaml", server="current-csv-invalid")

    run = data_contract.test()

    print(run)
    assert run.result == "failed"
    # Should have at least one failed check for constraint violation
    assert any(check.result == "failed" for check in run.checks)

def test_csv_required_field_missing_fails():
    """Required field missing from CSV data should fail validation"""
    data_contract = DataContract(
        data_contract_file="fixtures/schema-evolution/odcs-datacontract-cities-version-3.yaml", server="historical-csv")

    run = data_contract.test()

    print(run)
    assert run.result == "failed"


# Parquet Tests


def test_parquet_optional_field_missing_from_old_data():
    """Optional field not present in historical Parquet data should pass validation"""
    data_contract = DataContract(
        data_contract_file="fixtures/schema-evolution/odcs-datacontract-cities-version-2.yaml", server="historical-parquet"
    )

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)


def test_parquet_optional_field_present_in_new_data():
    """Optional field present in new Parquet data should pass validation"""
    data_contract = DataContract(
        data_contract_file="fixtures/schema-evolution/odcs-datacontract-cities-version-2.yaml", server="current-parquet")

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)

def test_data_from_historical_and_current_schema_parquet_mixed():
    """Combining Parquet data written with historical and current schema passes validation"""
    data_contract = DataContract(
        data_contract_file="fixtures/schema-evolution/odcs-datacontract-cities-version-2.yaml", server="mixed-schema-parquet")

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)

def test_parquet_optional_field_with_invalid_values():
    """Optional field in Parquet with invalid values should fail validation"""
    data_contract = DataContract(
        data_contract_file="fixtures/schema-evolution/odcs-datacontract-cities-version-2.yaml", server="current-parquet-invalid")

    run = data_contract.test()

    print(run)
    assert run.result == "failed"
    # Should have at least one failed check for constraint violation
    assert any(check.result == "failed" for check in run.checks)

def test_parquet_required_field_missing_fails():
    """Required field missing from Parquet data should fail validation"""
    data_contract = DataContract(
        data_contract_file="fixtures/schema-evolution/odcs-datacontract-cities-version-3.yaml", server="historical-parquet")

    run = data_contract.test()

    print(run)
    assert run.result == "failed"
