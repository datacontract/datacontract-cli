from datacontract.data_contract import DataContract


def test_csv_optional_field_missing_from_old_data():
    """Optional field not present in historical CSV data is correctly detected as missing"""
    data_contract = DataContract(
        data_contract_file="fixtures/schema-evolution/odcs-datacontract-cities-version-2.yaml", server="historical-csv"
    )

    run = data_contract.test()

    # field_is_present should detect that 'population' is missing from historical CSV
    assert run.result == "failed"
    missing_field_checks = [c for c in run.checks if c.type == "field_is_present" and c.field == "population"]
    assert len(missing_field_checks) == 1
    assert missing_field_checks[0].result == "failed"
    # Other field_is_present checks should still pass
    present_field_checks = [c for c in run.checks if c.type == "field_is_present" and c.field != "population"]
    assert all(c.result == "passed" for c in present_field_checks)


def test_csv_optional_field_present_in_new_data():
    """Optional field present in new CSV data should pass validation"""
    data_contract = DataContract(
        data_contract_file="fixtures/schema-evolution/odcs-datacontract-cities-version-2.yaml", server="current-csv"
    )

    run = data_contract.test()

    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)


def test_data_from_historical_and_current_schema_csv_mixed():
    """Combining CSV data written with historical and current schema passes validation"""
    data_contract = DataContract(
        data_contract_file="fixtures/schema-evolution/odcs-datacontract-cities-version-2.yaml",
        server="mixed-schema-csv",
    )

    run = data_contract.test()

    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)


def test_csv_optional_field_with_invalid_values():
    """Optional field in CSV with invalid values should fail validation"""
    data_contract = DataContract(
        data_contract_file="fixtures/schema-evolution/odcs-datacontract-cities-version-2.yaml",
        server="current-csv-invalid",
    )

    run = data_contract.test()

    assert run.result == "failed"
    # Should have at least one failed check for constraint violation
    assert any(check.result == "failed" for check in run.checks)


def test_csv_required_field_missing_fails():
    """Required field missing from CSV data should fail validation"""
    data_contract = DataContract(
        data_contract_file="fixtures/schema-evolution/odcs-datacontract-cities-version-3.yaml", server="historical-csv"
    )

    run = data_contract.test()

    assert run.result == "failed"


# Parquet Tests


def test_parquet_optional_field_missing_from_old_data():
    """Optional field not present in historical Parquet data is correctly detected as missing"""
    data_contract = DataContract(
        data_contract_file="fixtures/schema-evolution/odcs-datacontract-cities-version-2.yaml",
        server="historical-parquet",
    )

    run = data_contract.test()

    # field_is_present should detect that 'population' is missing from historical Parquet
    assert run.result == "failed"
    missing_field_checks = [c for c in run.checks if c.type == "field_is_present" and c.field == "population"]
    assert len(missing_field_checks) == 1
    assert missing_field_checks[0].result == "failed"
    # Other field_is_present checks should still pass
    present_field_checks = [c for c in run.checks if c.type == "field_is_present" and c.field != "population"]
    assert all(c.result == "passed" for c in present_field_checks)


def test_parquet_optional_field_present_in_new_data():
    """Optional field present in new Parquet data should pass validation"""
    data_contract = DataContract(
        data_contract_file="fixtures/schema-evolution/odcs-datacontract-cities-version-2.yaml", server="current-parquet"
    )

    run = data_contract.test()

    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)


def test_data_from_historical_and_current_schema_parquet_mixed():
    """Combining Parquet data written with historical and current schema passes validation"""
    data_contract = DataContract(
        data_contract_file="fixtures/schema-evolution/odcs-datacontract-cities-version-2.yaml",
        server="mixed-schema-parquet",
    )

    run = data_contract.test()

    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)


def test_parquet_optional_field_with_invalid_values():
    """Optional field in Parquet with invalid values should fail validation"""
    data_contract = DataContract(
        data_contract_file="fixtures/schema-evolution/odcs-datacontract-cities-version-2.yaml",
        server="current-parquet-invalid",
    )

    run = data_contract.test()

    assert run.result == "failed"
    # Should have at least one failed check for constraint violation
    assert any(check.result == "failed" for check in run.checks)


def test_parquet_required_field_missing_fails():
    """Required field missing from Parquet data should fail validation"""
    data_contract = DataContract(
        data_contract_file="fixtures/schema-evolution/odcs-datacontract-cities-version-3.yaml",
        server="historical-parquet",
    )

    run = data_contract.test()

    assert run.result == "failed"
