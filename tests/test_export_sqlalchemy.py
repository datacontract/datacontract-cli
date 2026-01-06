import ast
from textwrap import dedent

import pytest
from open_data_contract_standard.model import Description, OpenDataContractStandard, SchemaObject, SchemaProperty

import datacontract.export.sqlalchemy_exporter as conv


# These tests would be easier if AST nodes were comparable.
# Current string comparisons are very brittle.
def test_simple_model_export():
    schema = SchemaObject(
        name="Test", properties=[SchemaProperty(name="f", logicalType="string", primaryKey=True, primaryKeyPosition=1)]
    )
    ast_class = conv.generate_model_class("Test", schema)
    assert (
        ast.unparse(ast_class)
        == dedent(
            """
    class Test(Base):
        __tablename__ = 'Test'
        __table_args__ = {'comment': None, 'schema': None}
        f = Column(String(None), nullable=True, comment=None, primary_key=True)
    """
        ).strip()
    )


def test_simple_model_export_with_primary_key():
    schema = SchemaObject(
        name="Test", properties=[SchemaProperty(name="f", logicalType="string", primaryKey=True, primaryKeyPosition=1)]
    )
    ast_class = conv.generate_model_class("Test", schema)
    assert (
        ast.unparse(ast_class)
        == dedent(
            """
    class Test(Base):
        __tablename__ = 'Test'
        __table_args__ = {'comment': None, 'schema': None}
        f = Column(String(None), nullable=True, comment=None, primary_key=True)
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
        class Test(Base):
            __tablename__ = 'Test'
            __table_args__ = {'comment': None, 'schema': None}
            f = Column(ARRAY(String(None)), nullable=True, comment=None, primary_key=None)
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
    # Currently unsupported
    with pytest.raises(Exception):
        conv.generate_model_class("Test", schema)


def test_model_documentation_export():
    schema = SchemaObject(
        name="Test",
        description="A test model",
        properties=[SchemaProperty(name="f", logicalType="string", description="A test field")],
    )
    ast_class = conv.generate_model_class("Test", schema)
    assert (
        ast.unparse(ast_class)
        == dedent(
            """
        class Test(Base):
            \"\"\"A test model\"\"\"
            __tablename__ = 'Test'
            __table_args__ = {'comment': 'A test model', 'schema': None}
            f = Column(String(None), nullable=True, comment='A test field', primary_key=None)
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
    result = conv.to_sqlalchemy_model_str(contract)
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
