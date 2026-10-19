import ast
from textwrap import dedent

import pydantic
import pytest
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
        f: typing.Optional[str] = None
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
            f: typing.Optional[list[str]] = None
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
            f: typing.Optional[F] = None
        """
        ).strip()
    )


def test_object_without_properties_model_export():
    """An empty class body is not valid Python, so the class needs a `pass`."""
    schema = SchemaObject(
        name="Test",
        properties=[SchemaProperty(name="f", logicalType="object")],
    )
    ast_class = conv.generate_model_class("Test", schema)
    assert (
        ast.unparse(ast_class)
        == dedent(
            """
        class Test(pydantic.BaseModel):

            class F(pydantic.BaseModel):
                pass
            f: typing.Optional[F] = None
        """
        ).strip()
    )
    ast.parse(ast.unparse(ast_class))


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
            f: typing.Optional[F] = None
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
            f: typing.Optional[F] = None
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
            f: typing.Optional[str] = None
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
        f: typing.Optional[decimal.Decimal] = None
    """
        ).strip()
    )


def test_string_constraints_export():
    schema = SchemaObject(
        name="Test",
        properties=[
            SchemaProperty(
                name="f",
                logicalType="string",
                required=True,
                logicalTypeOptions={"pattern": "^[^,]+(,\\s*[^,]+)*$", "minLength": 1, "maxLength": 64},
            )
        ],
    )
    ast_class = conv.generate_model_class("Test", schema)
    assert (
        ast.unparse(ast_class)
        == dedent(
            r"""
    class Test(pydantic.BaseModel):
        f: str = pydantic.Field(pattern='^[^,]+(,\\s*[^,]+)*$', min_length=1, max_length=64)
    """
        ).strip()
    )


def test_optional_constrained_field_defaults_to_none():
    schema = SchemaObject(
        name="Test",
        properties=[
            SchemaProperty(
                name="f",
                logicalType="string",
                description="A labelled field",
                logicalTypeOptions={"pattern": "^a$"},
            )
        ],
    )
    ast_class = conv.generate_model_class("Test", schema)
    assert (
        ast.unparse(ast_class)
        == dedent(
            """
    class Test(pydantic.BaseModel):
        f: typing.Optional[str] = pydantic.Field(default=None, pattern='^a$')
        'A labelled field'
    """
        ).strip()
    )


def test_numeric_bounds_export():
    schema = SchemaObject(
        name="Test",
        properties=[
            SchemaProperty(
                name="f",
                logicalType="integer",
                required=True,
                logicalTypeOptions={"minimum": 0, "maximum": 100, "exclusiveMinimum": -1, "exclusiveMaximum": 101.5},
            )
        ],
    )
    ast_class = conv.generate_model_class("Test", schema)
    assert (
        ast.unparse(ast_class)
        == dedent(
            """
    class Test(pydantic.BaseModel):
        f: int = pydantic.Field(ge=0, le=100, gt=-1, lt=101.5)
    """
        ).strip()
    )


def test_date_bounds_export_as_strings():
    schema = SchemaObject(
        name="Test",
        properties=[
            SchemaProperty(name="f", logicalType="date", required=True, logicalTypeOptions={"minimum": "2020-01-01"})
        ],
    )
    ast_class = conv.generate_model_class("Test", schema)
    assert (
        ast.unparse(ast_class)
        == dedent(
            """
    class Test(pydantic.BaseModel):
        f: datetime.date = pydantic.Field(ge='2020-01-01')
    """
        ).strip()
    )


def test_options_outside_the_logical_type_are_ignored():
    """`maxLength` on an integer, a boolean bound, and an empty pattern have no Pydantic counterpart."""
    schema = SchemaObject(
        name="Test",
        properties=[
            SchemaProperty(name="f", logicalType="integer", required=True, logicalTypeOptions={"maxLength": 10}),
            SchemaProperty(
                name="g", logicalType="string", required=True, logicalTypeOptions={"pattern": "", "maxLength": True}
            ),
        ],
    )
    ast_class = conv.generate_model_class("Test", schema)
    assert (
        ast.unparse(ast_class)
        == dedent(
            """
    class Test(pydantic.BaseModel):
        f: int
        g: str
    """
        ).strip()
    )


def test_enum_field_keeps_its_constraints():
    schema = SchemaObject(
        name="Test",
        properties=[
            SchemaProperty(
                name="f",
                logicalType="string",
                required=True,
                logicalTypeOptions={"enum": ["ab", "cd"], "maxLength": 2},
            )
        ],
    )
    ast_class = conv.generate_model_class("Test", schema)
    assert (
        ast.unparse(ast_class)
        == dedent(
            """
    class Test(pydantic.BaseModel):
        f: typing.Literal['ab', 'cd'] = pydantic.Field(max_length=2)
    """
        ).strip()
    )


def test_generated_model_enforces_the_constraints():
    """What the contract constrains, the model rejects: the string tests cannot prove Pydantic accepts the output."""
    contract = OpenDataContractStandard(
        apiVersion="v3.1.0",
        kind="DataContract",
        schema=[
            SchemaObject(
                name="orders",
                properties=[
                    SchemaProperty(
                        name="label", logicalType="string", logicalTypeOptions={"pattern": "^[^,]+(,\\s*[^,]+)*$"}
                    ),
                    SchemaProperty(
                        name="total", logicalType="integer", required=True, logicalTypeOptions={"minimum": 0}
                    ),
                ],
            )
        ],
    )
    namespace = {}
    exec(conv.to_pydantic_model_str(contract), namespace)
    orders = namespace["Orders"]

    assert orders(total=1, label="a, b").label == "a, b"
    assert orders(total=0).label is None
    with pytest.raises(pydantic.ValidationError):
        orders(total=1, label="a,,b")
    with pytest.raises(pydantic.ValidationError):
        orders(total=-1)
