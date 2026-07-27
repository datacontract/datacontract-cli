"""Unit tests for the BigQuery type-string parser and SchemaProperty builder.

These tests cover the compound BigQuery type grammar (``ARRAY<...>``,
``STRUCT<...>``, ``NUMERIC(p, s)``, arbitrary nesting) that ``dbt`` emits in
model YAML ``data_type`` fields and that BigQuery's
``INFORMATION_SCHEMA.COLUMNS`` returns.
"""

import pytest

from datacontract.imports.bigquery_importer import (
    build_schema_property_from_bigquery_type,
    map_type_from_bigquery,
    parse_bigquery_type,
)
from datacontract.model.exceptions import DataContractException

# ---------------------------------------------------------------------------
# parse_bigquery_type
# ---------------------------------------------------------------------------


class TestParseBigQueryType:
    def test_parses_simple_scalar_type(self):
        parsed = parse_bigquery_type("STRING")
        assert parsed.base_type == "STRING"
        assert parsed.params == []
        assert parsed.element_type is None
        assert parsed.fields == []

    def test_lowercases_type_is_normalized_to_upper_case(self):
        parsed = parse_bigquery_type("string")
        assert parsed.base_type == "STRING"

    def test_parses_string_with_length(self):
        parsed = parse_bigquery_type("STRING(100)")
        assert parsed.base_type == "STRING"
        assert parsed.params == ["100"]

    def test_parses_numeric_with_precision_and_scale(self):
        parsed = parse_bigquery_type("NUMERIC(10, 2)")
        assert parsed.base_type == "NUMERIC"
        assert parsed.params == ["10", "2"]

    def test_parses_array_of_scalar(self):
        parsed = parse_bigquery_type("ARRAY<INT64>")
        assert parsed.base_type == "ARRAY"
        assert parsed.element_type is not None
        assert parsed.element_type.base_type == "INT64"

    def test_parses_empty_struct(self):
        parsed = parse_bigquery_type("STRUCT<>")
        assert parsed.base_type == "STRUCT"
        assert parsed.fields == []

    def test_parses_array_of_empty_struct(self):
        """The exact case that used to crash the dbt importer."""
        parsed = parse_bigquery_type("ARRAY<STRUCT<>>")
        assert parsed.base_type == "ARRAY"
        assert parsed.element_type is not None
        assert parsed.element_type.base_type == "STRUCT"
        assert parsed.element_type.fields == []

    def test_parses_struct_with_named_fields(self):
        parsed = parse_bigquery_type("STRUCT<name STRING, age INT64>")
        assert parsed.base_type == "STRUCT"
        assert [name for name, _ in parsed.fields] == ["name", "age"]
        assert [ft.base_type for _, ft in parsed.fields] == ["STRING", "INT64"]

    def test_parses_nested_array_of_struct_with_fields(self):
        parsed = parse_bigquery_type("ARRAY<STRUCT<name STRING, age INT64>>")
        assert parsed.base_type == "ARRAY"
        struct = parsed.element_type
        assert struct is not None
        assert struct.base_type == "STRUCT"
        assert [name for name, _ in struct.fields] == ["name", "age"]

    def test_parses_deeply_nested_types(self):
        parsed = parse_bigquery_type("ARRAY<STRUCT<items ARRAY<STRING>>>")
        assert parsed.base_type == "ARRAY"
        struct = parsed.element_type
        assert struct.base_type == "STRUCT"
        assert len(struct.fields) == 1
        name, field_type = struct.fields[0]
        assert name == "items"
        assert field_type.base_type == "ARRAY"
        assert field_type.element_type.base_type == "STRING"

    def test_parses_struct_with_parameterized_field_types(self):
        parsed = parse_bigquery_type("STRUCT<code STRING(10), amount NUMERIC(10, 2)>")
        code_name, code_type = parsed.fields[0]
        amount_name, amount_type = parsed.fields[1]
        assert code_name == "code"
        assert code_type.base_type == "STRING"
        assert code_type.params == ["10"]
        assert amount_name == "amount"
        assert amount_type.base_type == "NUMERIC"
        assert amount_type.params == ["10", "2"]

    def test_ignores_surrounding_whitespace(self):
        parsed = parse_bigquery_type("  ARRAY < INT64 > ")
        assert parsed.base_type == "ARRAY"
        assert parsed.element_type.base_type == "INT64"

    def test_parses_range_of_date(self):
        parsed = parse_bigquery_type("RANGE<DATE>")
        assert parsed.base_type == "RANGE"
        assert parsed.element_type.base_type == "DATE"

    @pytest.mark.parametrize("bad_input", [None, "", "   "])
    def test_rejects_empty_or_none_input(self, bad_input):
        with pytest.raises(DataContractException):
            parse_bigquery_type(bad_input)

    def test_rejects_unbalanced_angle_brackets(self):
        with pytest.raises(DataContractException):
            parse_bigquery_type("ARRAY<INT64")

    def test_rejects_unbalanced_parentheses(self):
        with pytest.raises(DataContractException):
            parse_bigquery_type("STRING(100")

    def test_rejects_trailing_garbage(self):
        with pytest.raises(DataContractException):
            parse_bigquery_type("STRING garbage")


# ---------------------------------------------------------------------------
# map_type_from_bigquery
# ---------------------------------------------------------------------------


class TestMapTypeFromBigQuery:
    @pytest.mark.parametrize(
        "bigquery_type, expected_logical",
        [
            ("STRING", "string"),
            ("INT64", "integer"),
            ("INTEGER", "integer"),
            ("FLOAT64", "number"),
            ("NUMERIC", "number"),
            ("BOOL", "boolean"),
            ("DATE", "date"),
            ("TIMESTAMP", "timestamp"),
            ("JSON", "object"),
        ],
    )
    def test_maps_simple_types(self, bigquery_type, expected_logical):
        assert map_type_from_bigquery(bigquery_type) == expected_logical

    @pytest.mark.parametrize(
        "bigquery_type, expected_logical",
        [
            ("STRING(100)", "string"),
            ("NUMERIC(10, 2)", "number"),
            ("BIGNUMERIC(38, 9)", "number"),
        ],
    )
    def test_maps_parameterized_scalar_types(self, bigquery_type, expected_logical):
        assert map_type_from_bigquery(bigquery_type) == expected_logical

    @pytest.mark.parametrize(
        "bigquery_type",
        [
            "ARRAY<INT64>",
            "ARRAY<STRUCT<>>",
            "ARRAY<STRUCT<name STRING, age INT64>>",
        ],
    )
    def test_array_types_map_to_array_logical_type(self, bigquery_type):
        assert map_type_from_bigquery(bigquery_type) == "array"

    @pytest.mark.parametrize(
        "bigquery_type",
        [
            "STRUCT<>",
            "STRUCT<name STRING>",
            "RECORD<name STRING>",
        ],
    )
    def test_struct_types_map_to_object_logical_type(self, bigquery_type):
        assert map_type_from_bigquery(bigquery_type) == "object"

    def test_rejects_unsupported_base_type(self):
        with pytest.raises(DataContractException) as exc_info:
            map_type_from_bigquery("MYSTERY_TYPE")
        assert "MYSTERY_TYPE" in str(exc_info.value.reason)

    def test_rejects_none(self):
        with pytest.raises(DataContractException):
            map_type_from_bigquery(None)


# ---------------------------------------------------------------------------
# build_schema_property_from_bigquery_type
# ---------------------------------------------------------------------------


class TestBuildSchemaPropertyFromBigQueryType:
    def test_builds_scalar_property(self):
        prop = build_schema_property_from_bigquery_type("id", "STRING")
        assert prop.name == "id"
        assert prop.logicalType == "string"
        assert prop.physicalType == "STRING"
        assert prop.items is None
        assert prop.properties is None

    def test_builds_string_property_with_max_length(self):
        prop = build_schema_property_from_bigquery_type("code", "STRING(10)")
        assert prop.logicalType == "string"
        assert prop.physicalType == "STRING"
        assert prop.logicalTypeOptions == {"maxLength": 10}

    def test_builds_numeric_property_with_precision_and_scale(self):
        prop = build_schema_property_from_bigquery_type("amount", "NUMERIC(10, 2)")
        assert prop.logicalType == "number"
        assert prop.physicalType == "NUMERIC"
        # ODCS v3.1.0 forbids precision/scale in logicalTypeOptions, so the helper
        # carries them as customProperties.
        custom_props = {cp.property: cp.value for cp in (prop.customProperties or [])}
        assert custom_props == {"precision": 10, "scale": 2}

    def test_builds_array_of_scalar_with_items(self):
        prop = build_schema_property_from_bigquery_type("tags", "ARRAY<STRING>")
        assert prop.logicalType == "array"
        assert prop.items is not None
        assert prop.items.name == "items"
        assert prop.items.logicalType == "string"
        assert prop.items.physicalType == "STRING"

    def test_builds_struct_with_named_field_properties(self):
        prop = build_schema_property_from_bigquery_type(
            "address",
            "STRUCT<street STRING, zip INT64>",
        )
        assert prop.logicalType == "object"
        assert prop.physicalType == "STRUCT"
        assert prop.properties is not None
        assert [p.name for p in prop.properties] == ["street", "zip"]
        assert [p.logicalType for p in prop.properties] == ["string", "integer"]

    def test_builds_empty_struct_as_object_without_properties(self):
        prop = build_schema_property_from_bigquery_type("payload", "STRUCT<>")
        assert prop.logicalType == "object"
        assert prop.physicalType == "STRUCT"
        assert prop.properties is None

    def test_builds_array_of_empty_struct(self):
        """The originally reported case: ``ARRAY<STRUCT<>>``."""
        prop = build_schema_property_from_bigquery_type(
            "incomeDetails",
            "ARRAY<STRUCT<>>",
            description="Income details of the customer.",
        )
        assert prop.name == "incomeDetails"
        assert prop.logicalType == "array"
        assert prop.description == "Income details of the customer."
        assert prop.items is not None
        assert prop.items.name == "items"
        assert prop.items.logicalType == "object"
        assert prop.items.physicalType == "STRUCT"
        assert prop.items.properties is None

    def test_builds_array_of_struct_with_named_fields(self):
        prop = build_schema_property_from_bigquery_type(
            "incomeDetails",
            "ARRAY<STRUCT<source STRING, amount NUMERIC(10, 2)>>",
        )
        assert prop.logicalType == "array"
        items = prop.items
        assert items is not None
        assert items.logicalType == "object"
        assert items.physicalType == "STRUCT"
        assert items.properties is not None
        assert [p.name for p in items.properties] == ["source", "amount"]
        # The nested NUMERIC(10, 2) should carry its precision/scale.
        amount = next(p for p in items.properties if p.name == "amount")
        amount_custom = {cp.property: cp.value for cp in (amount.customProperties or [])}
        assert amount_custom == {"precision": 10, "scale": 2}

    def test_builds_deeply_nested_array_struct_array(self):
        prop = build_schema_property_from_bigquery_type(
            "records",
            "ARRAY<STRUCT<name STRING, tags ARRAY<STRING>>>",
        )
        assert prop.logicalType == "array"
        struct_items = prop.items
        assert struct_items.logicalType == "object"
        assert [p.name for p in struct_items.properties] == ["name", "tags"]
        tags = next(p for p in struct_items.properties if p.name == "tags")
        assert tags.logicalType == "array"
        assert tags.items.logicalType == "string"

    def test_preserves_required_and_description(self):
        prop = build_schema_property_from_bigquery_type(
            "customer_id",
            "STRING",
            description="Primary customer identifier.",
            required=True,
        )
        assert prop.required is True
        assert prop.description == "Primary customer identifier."

    def test_builds_struct_with_anonymous_fields_as_field_n(self):
        """Anonymous struct fields become ``field_1``, ``field_2``, ... in the property."""
        prop = build_schema_property_from_bigquery_type("payload", "STRUCT<STRING, INT64>")
        assert prop.logicalType == "object"
        assert prop.properties is not None
        assert [p.name for p in prop.properties] == ["field_1", "field_2"]
        assert [p.logicalType for p in prop.properties] == ["string", "integer"]
