from open_data_contract_standard.model import SchemaProperty

from datacontract.engines.hana.hana_type_mapping import convert_type_to_hana, types_match


def test_convert_type_to_hana_string():
    field = SchemaProperty(name="col", logicalType="string")

    assert convert_type_to_hana(field) == "NVARCHAR(5000)"


def test_convert_type_to_hana_integer():
    field = SchemaProperty(name="col", logicalType="integer")

    assert convert_type_to_hana(field) == "INTEGER"


def test_convert_type_to_hana_decimal_with_params():
    field = SchemaProperty(name="col", logicalType="decimal", logicalTypeOptions={"precision": 15, "scale": 2})

    assert convert_type_to_hana(field) == "DECIMAL(15,2)"


def test_convert_type_to_hana_custom_config():
    field = SchemaProperty(
        name="col",
        logicalType="string",
        customProperties=[{"property": "hanaType", "value": "ST_GEOMETRY"}],
    )

    assert convert_type_to_hana(field) == "ST_GEOMETRY"


def test_convert_type_to_hana_all_mappings():
    expected = {
        "varchar": "NVARCHAR(5000)",
        "text": "NVARCHAR(5000)",
        "int": "INTEGER",
        "long": "BIGINT",
        "bigint": "BIGINT",
        "smallint": "SMALLINT",
        "tinyint": "TINYINT",
        "float": "REAL",
        "double": "DOUBLE",
        "numeric": "DECIMAL",
        "number": "DECIMAL",
        "boolean": "BOOLEAN",
        "date": "DATE",
        "time": "TIME",
        "timestamp": "TIMESTAMP",
        "timestamp_tz": "TIMESTAMP",
        "timestamp_ntz": "SECONDDATE",
        "binary": "VARBINARY",
        "bytes": "VARBINARY",
        "object": "NCLOB",
        "record": "NCLOB",
        "struct": "NCLOB",
        "array": "NCLOB",
    }

    for logical_type, hana_type in expected.items():
        assert convert_type_to_hana(SchemaProperty(name="col", logicalType=logical_type)) == hana_type


def test_types_match_strips_precision_and_uses_physical_type():
    assert types_match("NVARCHAR(255)", "NVARCHAR")
    assert types_match("DECIMAL(15,2)", "DECIMAL")
    assert not types_match("NVARCHAR(255)", "VARCHAR")


def test_types_match_logical_mapping():
    assert types_match("NVARCHAR(255)", "string")
    assert types_match("INTEGER", "int")
    assert types_match("SECONDDATE", "timestamp_ntz")
    assert not types_match("DATE", "timestamp")
