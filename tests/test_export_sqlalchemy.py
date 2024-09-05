import ast
from textwrap import dedent

import datacontract.export.sqlalchemy_converter as conv
import datacontract.model.data_contract_specification as spec

import pytest


# These tests would be easier if AST nodes were comparable.
# Current string comparisons are very brittle.
def test_simple_model_export():
    m = spec.Model(fields={"f": spec.Field(type="string")})
    ast_class = conv.generate_model_class("Test", m)
    assert (
        ast.unparse(ast_class)
        == dedent(
            """
    class Test(Base):
        __tablename__ = 'Test'
        __table_args__ = {'comment': None, 'schema': None}
        f = Column(String(None), nullable=True, comment=None, primary_key=None)
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
        class Test(Base):
            __tablename__ = 'Test'
            __table_args__ = {'comment': None, 'schema': None}
            f = Column(ARRAY(String(None)), nullable=True, comment=None, primary_key=None)
        """
        ).strip()
    )


def test_object_model_export():
    m = spec.Model(fields={"f": spec.Field(type="object", fields={"f1": spec.Field(type="string", required=True)})})
    # Currently unsupported
    with pytest.raises(Exception):
        conv.generate_model_class("Test", m)


def test_model_documentation_export():
    m = spec.Model(
        description="A test model",
        fields={"f": spec.Field(type="string", description="A test field")},
    )
    ast_class = conv.generate_model_class("Test", m)
    assert (
        ast.unparse(ast_class)
        == dedent(
            """
        class Test(Base):
            \"""A test model\"""
            __tablename__ = 'Test'
            __table_args__ = {'comment': 'A test model', 'schema': None}
            f = Column(String(None), nullable=True, comment='A test field', primary_key=None)
        """
        ).strip()
    )


def test_model_description_export():
    m = spec.DataContractSpecification(
        info=spec.Info(description="Contract description"),
        models={"test_model": spec.Model(fields={"f": spec.Field(type="string")})},
    )
    result = conv.to_sqlalchemy_model_str(m)
    assert result.strip().endswith(
        dedent(
            """
            'Contract description'

            class Base(DeclarativeBase):
                pass

            class Test_model(Base):
                __tablename__ = 'test_model'
                __table_args__ = {'comment': None, 'schema': None}
                f = Column(String(None), nullable=True, comment=None, primary_key=None)
            """
        ).strip()
    )
