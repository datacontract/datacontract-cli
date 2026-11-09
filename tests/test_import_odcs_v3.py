from datacontract.data_contract import DataContract


def test_import_odcs():
    """Test that ODCS import is a pass-through returning OpenDataContractStandard."""
    result = DataContract.import_from_source("odcs", "./fixtures/odcs_v3/full-example.odcs.yaml")
    assert result.id == "53581432-6c55-4ba2-a65f-72344a91553a"
    assert result.kind == "DataContract"
    assert result.apiVersion == "v3.0.0"
    assert len(result.schema_) == 1
    assert result.schema_[0].name == "tbl"


def test_import_odcs_owner_keeps_the_members_of_a_member_list_team(tmp_path):
    source = tmp_path / "datacontract.odcs.yaml"
    source.write_text(
        """
apiVersion: v3.2.0
kind: DataContract
id: orders
version: 1.0.0
status: active
team:
  - username: alice
    role: owner
"""
    )
    result = DataContract.import_from_source("odcs", str(source), owner="sales")
    assert result.team.name == "sales"
    assert [member.username for member in result.team.members] == ["alice"]
