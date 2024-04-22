import ast
from textwrap import dedent

import datacontract.export.pydantic_converter as conv
import datacontract.model.data_contract_specification as spec


# These tests would be easier if AST nodes were comparable.
# Current string comparisons are very brittle.
def test_simple_model_export():
    m = spec.Model(fields={"f": spec.Field(type="string")})
    ast_class = conv.generate_model_class("Test", m)
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
    m = spec.Model(fields={"f": spec.Field(type="array", items=spec.Field(type="string", required=True))})
    ast_class = conv.generate_model_class("Test", m)
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
    m = spec.Model(fields={"f": spec.Field(type="object", fields={"f1": spec.Field(type="string", required=True)})})
    ast_class = conv.generate_model_class("Test", m)
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
    m = spec.Model(
        description="A test model",
        fields={
            "f": spec.Field(
                type="object", description="A test field", fields={"f1": spec.Field(type="string", required=True)}
            )
        },
    )
    ast_class = conv.generate_model_class("Test", m)
    assert (
        ast.unparse(ast_class)
        == dedent(
            """
        class Test(pydantic.BaseModel):
            \"""A test model\"""

            class F(pydantic.BaseModel):
                \"""A test field\"""
                f1: str
            f: typing.Optional[F]
        """
        ).strip()
    )


def test_model_field_description_export():
    m = spec.Model(
        fields={
            "f": spec.Field(
                type="object", fields={"f1": spec.Field(type="string", description="A test field", required=True)}
            )
        }
    )
    ast_class = conv.generate_model_class("Test", m)
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
    m = spec.DataContractSpecification(
        info=spec.Info(description="Contract description"),
        models={"test_model": spec.Model(fields={"f": spec.Field(type="string")})},
    )
    result = conv.to_pydantic_model_str(m)
    assert (
        result
        == dedent(
            """
        import datetime, typing, pydantic
        'Contract description'

        class Test_model(pydantic.BaseModel):
            f: typing.Optional[str]
        """
        ).strip()
    )
