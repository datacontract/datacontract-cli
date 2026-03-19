import ast
from textwrap import dedent

from open_data_contract_standard.model import Description, OpenDataContractStandard, SchemaObject, SchemaProperty

import datacontract.export.pydantic_exporter as conv


# These tests would be easier if AST nodes were comparable.
# Current string comparisons are very brittle.
def test_simple_model_export():
    schema = SchemaObject(name="Test", properties=[SchemaProperty(name="f", logicalType="string")])
    ast_class = conv.generate_model_class("Test", schema)
    assert (
        ast.unparse(ast_class)
        == dedent(
            """
    class Test(pydantic.BaseModel):
        f: typing.Optional[str]
    """
        ).strip()
    )


def test_array_model_export():
    schema = SchemaObject(
        name="Test",
        properties=[
            SchemaProperty(
                name="f",
                logicalType="array",
                items=SchemaProperty(name="item", logicalType="string", required=True),
            )
        ],
    )
    ast_class = conv.generate_model_class("Test", schema)
    assert (
        ast.unparse(ast_class)
        == dedent(
            """
        class Test(pydantic.BaseModel):
            f: typing.Optional[list[str]]
        """
        ).strip()
    )


def test_object_model_export():
    schema = SchemaObject(
        name="Test",
        properties=[
            SchemaProperty(
                name="f",
                logicalType="object",
                properties=[SchemaProperty(name="f1", logicalType="string", required=True)],
            )
        ],
    )
    ast_class = conv.generate_model_class("Test", schema)
    assert (
        ast.unparse(ast_class)
        == dedent(
            """
        class Test(pydantic.BaseModel):

            class F(pydantic.BaseModel):
                f1: str
            f: typing.Optional[F]
        """
        ).strip()
    )


def test_model_documentation_export():
    schema = SchemaObject(
        name="Test",
        description="A test model",
        properties=[
            SchemaProperty(
                name="f",
                logicalType="object",
                description="A test field",
                properties=[SchemaProperty(name="f1", logicalType="string", required=True)],
            )
        ],
    )
    ast_class = conv.generate_model_class("Test", schema)
    assert (
        ast.unparse(ast_class)
        == dedent(
            """
        class Test(pydantic.BaseModel):
            \"\"\"A test model\"\"\"

            class F(pydantic.BaseModel):
                \"\"\"A test field\"\"\"
                f1: str
            f: typing.Optional[F]
        """
        ).strip()
    )


def test_model_field_description_export():
    schema = SchemaObject(
        name="Test",
        properties=[
            SchemaProperty(
                name="f",
                logicalType="object",
                properties=[SchemaProperty(name="f1", logicalType="string", description="A test field", required=True)],
            )
        ],
    )
    ast_class = conv.generate_model_class("Test", schema)
    assert (
        ast.unparse(ast_class)
        == dedent(
            """
        class Test(pydantic.BaseModel):

            class F(pydantic.BaseModel):
                f1: str
                'A test field'
            f: typing.Optional[F]
        """
        ).strip()
    )


def test_model_description_export():
    contract = OpenDataContractStandard(
        apiVersion="v3.1.0",
        kind="DataContract",
        description=Description(purpose="Contract description"),
        schema=[SchemaObject(name="test_model", properties=[SchemaProperty(name="f", logicalType="string")])],
    )
    result = conv.to_pydantic_model_str(contract)
    assert (
        result
        == dedent(
            """
        import datetime, typing, pydantic, decimal
        'Contract description'

        class Test_model(pydantic.BaseModel):
            f: typing.Optional[str]
        """
        ).strip()
    )


def test_decimal_model_export():
    schema = SchemaObject(
        name="test_model", properties=[SchemaProperty(name="f", logicalType="number", physicalType="decimal")]
    )
    ast_class = conv.generate_model_class("Test", schema)
    assert (
        ast.unparse(ast_class)
        == dedent(
            """
    class Test(pydantic.BaseModel):
        f: typing.Optional[decimal.Decimal]
    """
        ).strip()
    )
