import tempfile

from pyiceberg import types
from pyiceberg.schema import Schema, assign_fresh_schema_ids
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.iceberg_converter import IcebergExporter
from datacontract.lint.resolve import resolve_data_contract


def test_cli():
    with tempfile.NamedTemporaryFile(delete=True) as tmp_input_file:
        # create temp file with content
        tmp_input_file.write(b"""
        dataContractSpecification: 0.9.3
        id: my-id
        info:
          title: My Title
          version: 1.0.0
        models:
          orders:
            fields:
              order_id:
                type: int
                required: true
                primaryKey: true
        """)
        tmp_input_file.flush()

        with tempfile.NamedTemporaryFile(delete=True) as tmp_output_file:
            runner = CliRunner()
            result = runner.invoke(
                app, ["export", tmp_input_file.name, "--format", "iceberg", "--output", tmp_output_file.name]
            )
            assert result.exit_code == 0

            with open(tmp_output_file.name, "r") as f:
                schema = Schema.model_validate_json(f.read())

    assert len(schema.fields) == 1
    _assert_field(schema, "order_id", types.IntegerType(), True)
    assert schema.identifier_field_ids == [1]


def test_type_conversion():
    datacontract = resolve_data_contract(
        data_contract_str="""
            dataContractSpecification: 0.9.3
            id: my-id
            info:
              title: My Title
              version: 1.0.0
            models:
              datatypes:
                fields:
                  string_type:
                    type: string
                  text_type:
                    type: text
                  varchar_type:
                    type: varchar
                  number_type:
                    type: number
                  decimal_type:
                    type: decimal
                    precision: 4
                    scale: 2
                  numeric_type:
                    type: numeric
                  int_type:
                    type: int
                  integer_type:
                    type: integer
                  long_type:
                    type: long
                  bigint_type:
                    type: bigint
                  float_type:
                    type: float
                  double_type:
                    type: double
                  boolean_type:
                    type: boolean
                  timestamp_type:
                    type: timestamp
                  timestamp_tz_type:
                    type: timestamp_tz
                  timestamp_ntz_type:
                    type: timestamp_ntz
                  date_type:
                    type: date
                  array_type:
                    type: array
                    items:
                      type: string
                  map_type:
                    type: map
                    keys:
                      type: string
                    values:
                      type: int
                  object_type:
                    type: object
                    fields:
                      object_field1:
                        type: string
                  record_type:
                    type: record
                    fields:
                      record_field1:
                        type: int
                  struct_type:
                    type: struct
                    fields:
                      struct_field1:
                        type: float
            """,
        inline_definitions=True,
    )
    datacontract.model_dump()
    schema = Schema.model_validate_json(_export(datacontract))

    assert len(schema.fields) == 22
    _assert_field(schema, "string_type", types.StringType(), False)
    _assert_field(schema, "text_type", types.StringType(), False)
    _assert_field(schema, "varchar_type", types.StringType(), False)
    _assert_field(schema, "number_type", types.DecimalType(precision=38, scale=0), False)
    _assert_field(schema, "decimal_type", types.DecimalType(precision=4, scale=2), False)
    _assert_field(schema, "numeric_type", types.DecimalType(precision=38, scale=0), False)
    _assert_field(schema, "int_type", types.IntegerType(), False)
    _assert_field(schema, "integer_type", types.IntegerType(), False)
    _assert_field(schema, "long_type", types.LongType(), False)
    _assert_field(schema, "bigint_type", types.LongType(), False)
    _assert_field(schema, "float_type", types.FloatType(), False)
    _assert_field(schema, "double_type", types.DoubleType(), False)
    _assert_field(schema, "boolean_type", types.BooleanType(), False)
    _assert_field(schema, "timestamp_type", types.TimestamptzType(), False)
    _assert_field(schema, "timestamp_tz_type", types.TimestamptzType(), False)
    _assert_field(schema, "timestamp_ntz_type", types.TimestampType(), False)
    _assert_field(schema, "date_type", types.DateType(), False)
    _assert_field(
        schema,
        "array_type",
        types.ListType(element_id=0, element_type=types.StringType(), element_required=False),
        False,
    )
    _assert_field(
        schema,
        "map_type",
        types.MapType(
            key_id=0, key_type=types.StringType(), value_id=0, value_type=types.IntegerType(), value_required=False
        ),
        False,
    )
    _assert_field(
        schema,
        "object_type",
        types.StructType(
            types.NestedField(field_id=0, name="object_field1", field_type=types.StringType(), required=False)
        ),
        False,
    )
    _assert_field(
        schema,
        "record_type",
        types.StructType(
            types.NestedField(field_id=0, name="record_field1", field_type=types.IntegerType(), required=False)
        ),
        False,
    )
    _assert_field(
        schema,
        "struct_type",
        types.StructType(
            types.NestedField(field_id=0, name="struct_field1", field_type=types.FloatType(), required=False)
        ),
        False,
    )


def test_round_trip():
    with open("fixtures/iceberg/nested_schema.json", "r") as f:
        starting_schema = Schema.model_validate_json(f.read())

    import_runner = CliRunner()
    import_result = import_runner.invoke(
        app,
        [
            "import",
            "--format",
            "iceberg",
            "--source",
            "fixtures/iceberg/nested_schema.json",
            "--iceberg-table",
            "test-table",
        ],
    )

    assert import_result.exit_code == 0
    output = import_result.stdout.strip()

    with tempfile.NamedTemporaryFile(delete=True) as tmp_input_file:
        # create temp file with content
        tmp_input_file.write(output.encode())
        tmp_input_file.flush()

        with tempfile.NamedTemporaryFile(delete=True) as tmp_output_file:
            runner = CliRunner()
            result = runner.invoke(
                app, ["export", tmp_input_file.name, "--format", "iceberg", "--output", tmp_output_file.name]
            )
            assert result.exit_code == 0

            with open(tmp_output_file.name, "r") as f:
                ending_schema = Schema.model_validate_json(f.read())

    # don't use IDs in equality check since SDK resets them anyway
    starting_schema = assign_fresh_schema_ids(starting_schema)
    ending_schema = assign_fresh_schema_ids(ending_schema)
    assert starting_schema == ending_schema


def _assert_field(schema, field_name, field_type, required):
    field = None
    for f in schema.fields:
        if f.name == field_name:
            field = f
            break

    assert field is not None
    assert field.name == field_name
    assert field.required == required

    found_type = field.field_type
    if found_type.is_primitive:
        assert found_type == field_type
    elif isinstance(found_type, types.ListType):
        assert found_type.element_type == field_type.element_type
        assert found_type.element_required == field_type.element_required
    elif isinstance(found_type, types.MapType):
        assert found_type.key_type == field_type.key_type
        assert found_type.value_type == field_type.value_type
        assert found_type.value_required == field_type.value_required
    elif isinstance(found_type, types.StructType):
        assert len(found_type.fields) == len(field_type.fields)
        for nested_field in field_type.fields:
            _assert_field(found_type, nested_field.name, nested_field.field_type, nested_field.required)
    else:
        raise ValueError(f"Unexpected field type: {found_type}")


def _export(datacontract, model=None):
    return IcebergExporter("iceberg").export(datacontract, model, None, None, None)
