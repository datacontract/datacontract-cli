from textwrap import dedent

from typer.testing import CliRunner

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty
from datacontract.cli import app
from datacontract.export.avro_idl_converter import (
    AvroIDLProtocol,
    AvroModelType,
    AvroPrimitiveField,
    AvroPrimitiveType,
    _contract_to_avro_idl_ir,
    to_avro_idl,
)
from datacontract.lint.resolve import resolve_data_contract_from_location


def test_ir():
    contract = resolve_data_contract_from_location("fixtures/lint/valid_datacontract_ref.yaml", inline_definitions=True)
    expected = AvroIDLProtocol(
        name="OrdersLatest",
        description="Successful customer orders in the webshop.\n"
        "All orders since 2020-01-01.\n"
        "Orders with their line items are in their current state (no history included).\n",
        model_types=[
            AvroModelType(
                "orders",
                "One record per order. Includes cancelled and deleted orders.",
                [
                    AvroPrimitiveField(
                        "order_id",
                        True,
                        "An internal ID that identifies an order in the online shop.",
                        type=AvroPrimitiveType.string,
                    )
                ],
            ),
        ],
    )
    assert _contract_to_avro_idl_ir(contract) == expected


def test_avro_idl_str():
    contract = resolve_data_contract_from_location("fixtures/lint/valid_datacontract_ref.yaml", inline_definitions=True)
    expected = dedent(
        """
          /** Successful customer orders in the webshop.
          All orders since 2020-01-01.
          Orders with their line items are in their current state (no history included).
           */
          protocol OrdersLatest {
              /** One record per order. Includes cancelled and deleted orders. */
              record orders {
                  /** An internal ID that identifies an order in the online shop. */
                  string order_id;
              }
          }
        """
    ).strip()
    assert to_avro_idl(contract).strip() == expected


def test_avro_idl_cli_export():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/lint/valid_datacontract_ref.yaml", "--format", "avro-idl"])
    if result.exit_code:
        print(result.output)
    assert result.exit_code == 0


def test_avro_idl_complex_type():
    contract = OpenDataContractStandard(
        apiVersion="v3.1.0",
        kind="DataContract",
        schema_=[
            SchemaObject(
                name="test_model",
                description="Test model",
                properties=[
                    SchemaProperty(
                        name="test_field",
                        logicalType="object",
                        required=True,
                        description="Complex field",
                        properties=[
                            SchemaProperty(
                                name="nested_field_1",
                                description="Primitive field",
                                logicalType="string",
                            )
                        ],
                    )
                ],
            )
        ],
    )
    expected = dedent("""
    protocol Unnamed {
        /** Test model */
        record test_model {
            /** Complex field */
            record test_field_type {
                /** Primitive field */
                string? nested_field_1;
            }
            /** Complex field */
            test_field_type test_field;
        }
    }
    """).strip()
    assert to_avro_idl(contract).strip() == expected


def test_avro_idl_array_type():
    contract = OpenDataContractStandard(
        apiVersion="v3.1.0",
        kind="DataContract",
        schema_=[
            SchemaObject(
                name="test_model",
                description="Test model",
                properties=[
                    SchemaProperty(
                        name="test_field",
                        logicalType="array",
                        description="Array field",
                        items=SchemaProperty(
                            name="item",
                            logicalType="object",
                            description="Record field",
                            properties=[
                                SchemaProperty(
                                    name="nested_field_1",
                                    logicalType="string",
                                    description="Primitive field",
                                )
                            ],
                        ),
                    )
                ],
            )
        ],
    )
    expected = dedent("""
    protocol Unnamed {
        /** Test model */
        record test_model {
            /** Record field */
            record test_field_type {
                /** Primitive field */
                string? nested_field_1;
            }
            /** Array field */
            array<test_field_type?>? test_field;
        }
    }
    """).strip()
    assert to_avro_idl(contract).strip() == expected
