import datacontract.model.data_contract_specification as spec
import datacontract.export.pydantic_converter as conv
from textwrap import dedent
import ast


# These tests would be easier if AST nodes were comparable.
# Current string comparisons are very brittle.
def test_simple_model_export():
    m = spec.Model(
        fields={
            "f": spec.Field(
                type="string")})
    ast_class = conv.generate_model_class("Test", m)
    print(ast.dump(ast_class))
    assert ast.unparse(ast_class) == dedent(
    """
    class Test(pydantic.BaseModel):
        f: typing.Optional[str]
    """).strip()

def test_array_model_export():
    m = spec.Model(
        fields={
            "f": spec.Field(
                type="array",
                items=spec.Field(
                    type="string",
                    required=True))})
    ast_class = conv.generate_model_class("Test", m)
    assert ast.unparse(ast_class) == dedent(
        """
        class Test(pydantic.BaseModel):
            f: typing.Optional[list[str]]
        """).strip()

def test_object_model_export():
    m = spec.Model(
        fields={
            "f": spec.Field(
                type="object",
                fields={
                    "f1": spec.Field(
                        type="string",
                        required=True)})})
    ast_class = conv.generate_model_class("Test", m)
    assert ast.unparse(ast_class) == dedent(
        """
        class Test(pydantic.BaseModel):

            class F(pydantic.BaseModel):
                f1: str
            f: typing.Optional[F]
        """).strip()
