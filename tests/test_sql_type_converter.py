from datacontract.data_contract import DataContract


def test_to_sql_ddl_postgres_string_types():
    actual = DataContract(data_contract_file="fixtures/postgres-export-string-types/datacontract.yaml").export("sql")
    expected = """
-- Data Contract: string-types-postgres-test
-- SQL Dialect: postgres
CREATE TABLE my_table (
  field_physical_type VARCHAR(255),
  field_max_length varchar(100),
  field_plain_string text,
  field_integer integer
);
""".strip()
    assert actual == expected
