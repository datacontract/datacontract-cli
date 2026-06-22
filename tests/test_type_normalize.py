from datacontract.engines.checks.type_normalize import category_matches, normalize_type_name


def test_normalize_strips_length_parameters():
    assert normalize_type_name("VARCHAR2(4000)") == "string"
    assert normalize_type_name("VARCHAR2(40)") == "string"
    assert normalize_type_name("NUMBER(4,0)") == "number"
    assert normalize_type_name("CHAR(10)") == "string"


def test_normalize_oracle_string_types():
    # Oracle VARCHAR2/NVARCHAR2 (with or without length) are strings, not "other".
    assert normalize_type_name("VARCHAR2") == "string"
    assert normalize_type_name("NVARCHAR2") == "string"
    assert normalize_type_name("nvarchar2(100)") == "string"


def test_parameterized_type_matches_unparameterized():
    # A contract declaring VARCHAR2(4000) must match a column reported as VARCHAR2.
    expected = normalize_type_name("VARCHAR2(4000)")
    actual = normalize_type_name("VARCHAR2")
    assert category_matches(expected, actual)

    expected = normalize_type_name("NUMBER(4,0)")
    assert category_matches(expected, "decimal")
