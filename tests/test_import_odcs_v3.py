from datacontract.data_contract import DataContract


def test_import_odcs():
    """Test that ODCS import is a pass-through returning OpenDataContractStandard."""
    result = DataContract.import_from_source("odcs", "./fixtures/odcs_v3/full-example.odcs.yaml")
    assert result.id == "53581432-6c55-4ba2-a65f-72344a91553a"
    assert result.kind == "DataContract"
    assert result.apiVersion == "v3.0.0"
    assert len(result.schema_) == 1
    assert result.schema_[0].name == "tbl"
