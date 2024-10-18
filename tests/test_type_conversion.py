from datacontract.export.sql_type_converter import convert_to_duckdb


class TestDuckDbConversion:
    def test_convert_to_duckdb_handles_none(self):
        assert convert_to_duckdb(None) is None
