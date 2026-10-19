import pytest

from datacontract.data_contract import DataContract


@pytest.mark.parametrize(
    "dialect, ddl",
    [
        ("databricks", "CREATE TABLE orders (order_id INT, shipping STRUCT<city: STRING, zip: STRING>);"),
        ("spark", "CREATE TABLE orders (order_id INT, shipping STRUCT<city: STRING, zip: STRING>);"),
        ("bigquery", "CREATE TABLE orders (order_id INT64, shipping STRUCT<city STRING, zip STRING>);"),
    ],
)
def test_the_fields_of_a_struct_are_not_columns_of_the_table(tmp_path, dialect, ddl):
    source = tmp_path / "orders.sql"
    source.write_text(ddl)

    result = DataContract.import_from_source("sql", str(source), dialect=dialect)

    assert [prop.name for prop in result.schema_[0].properties] == ["order_id", "shipping"]
