import ast
import typing
from typing import List, Optional

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty, Server

from datacontract.export.exporter import Exporter, _determine_sql_server_type


class SQLAlchemyExporter(Exporter):
    def export(
        self, data_contract: OpenDataContractStandard, schema_name, server, sql_server_type, export_args
    ) -> dict:
        sql_server_type = _determine_sql_server_type(data_contract, sql_server_type, server)
        return to_sqlalchemy_model_str(data_contract, sql_server_type, server)


DECLARATIVE_BASE = "Base"


def _get_server_by_name(data_contract: OpenDataContractStandard, name: str) -> Optional[Server]:
    """Get a server by name."""
    if data_contract.servers is None:
        return None
    return next((s for s in data_contract.servers if s.server == name), None)


def _get_type(prop: SchemaProperty) -> Optional[str]:
    """Get the type from a schema property."""
    if prop.logicalType:
        return prop.logicalType
    if prop.physicalType:
        return prop.physicalType
    return None


def _get_logical_type_option(prop: SchemaProperty, key: str):
    """Get a logical type option value."""
    if prop.logicalTypeOptions is None:
        return None
    return prop.logicalTypeOptions.get(key)


def to_sqlalchemy_model_str(
    odcs: OpenDataContractStandard, sql_server_type: str = "", server=None
) -> str:
    server_obj = _get_server_by_name(odcs, server) if server else None
    classdefs = []
    if odcs.schema_:
        for schema_obj in odcs.schema_:
            classdefs.append(generate_model_class(schema_obj.name, schema_obj, server_obj, sql_server_type))

    description_str = None
    if odcs.description:
        if hasattr(odcs.description, "purpose"):
            description_str = odcs.description.purpose
    documentation = [ast.Expr(ast.Constant(description_str))] if description_str else []

    declarative_base = ast.ClassDef(
        name=DECLARATIVE_BASE,
        bases=[ast.Name(id="DeclarativeBase", ctx=ast.Load())],
        body=[ast.Pass()],
        keywords=[],
        decorator_list=[],
    )

    databricks_timestamp = ast.ImportFrom(
        module="databricks.sqlalchemy", names=[ast.alias("TIMESTAMP"), ast.alias("TIMESTAMP_NTZ")]
    )
    timestamp = ast.ImportFrom(module="sqlalchemy", names=[ast.alias(name="TIMESTAMP")])
    result = ast.Module(
        body=[
            ast.ImportFrom(module="sqlalchemy.orm", names=[ast.alias(name="DeclarativeBase")]),
            ast.ImportFrom(
                module="sqlalchemy",
                names=[
                    ast.alias("Column"),
                    ast.alias("Date"),
                    ast.alias("Integer"),
                    ast.alias("Numeric"),
                    ast.alias("String"),
                    ast.alias("Text"),
                    ast.alias("VARCHAR"),
                    ast.alias("BigInteger"),
                    ast.alias("Float"),
                    ast.alias("Double"),
                    ast.alias("Boolean"),
                    ast.alias("Date"),
                    ast.alias("ARRAY"),
                    ast.alias("LargeBinary"),
                ],
            ),
            databricks_timestamp if sql_server_type == "databricks" else timestamp,
            *documentation,
            declarative_base,
            *classdefs,
        ],
        type_ignores=[],
    )
    return ast.unparse(result)


def Call(name, *args, **kwargs) -> ast.Call:
    return ast.Call(
        ast.Name(name),
        args=[v for v in args],
        keywords=[ast.keyword(arg=f"{k}", value=ast.Constant(v)) for (k, v) in kwargs.items()],
    )


def Column(predicate, **kwargs) -> ast.Call:
    return Call("Column", predicate, **kwargs)


def sqlalchemy_primitive(prop: SchemaProperty):
    prop_type = _get_type(prop)
    max_length = _get_logical_type_option(prop, "maxLength")
    precision = _get_logical_type_option(prop, "precision")
    scale = _get_logical_type_option(prop, "scale")

    if prop_type is None:
        return None

    prop_type_lower = prop_type.lower()

    sqlalchemy_name = {
        "string": Call("String", ast.Constant(max_length)),
        "text": Call("Text", ast.Constant(max_length)),
        "varchar": Call("VARCHAR", ast.Constant(max_length)),
        "number": Call("Numeric", ast.Constant(precision), ast.Constant(scale)),
        "decimal": Call("Numeric", ast.Constant(precision), ast.Constant(scale)),
        "numeric": Call("Numeric", ast.Constant(precision), ast.Constant(scale)),
        "int": ast.Name("Integer"),
        "integer": ast.Name("Integer"),
        "long": ast.Name("BigInteger"),
        "bigint": ast.Name("BigInteger"),
        "float": ast.Name("Float"),
        "double": ast.Name("Double"),
        "boolean": ast.Name("Boolean"),
        "timestamp": ast.Name("TIMESTAMP"),
        "timestamp_tz": Call("TIMESTAMP", ast.Constant(True)),
        "timestamp_ntz": ast.Name("TIMESTAMP_NTZ"),
        "date": ast.Name("Date"),
        "bytes": Call("LargeBinary", ast.Constant(max_length)),
    }
    return sqlalchemy_name.get(prop_type_lower)


def constant_field_value(field_name: str, prop: SchemaProperty) -> tuple[ast.Call, typing.Optional[ast.ClassDef]]:
    new_type = sqlalchemy_primitive(prop)
    prop_type = _get_type(prop)

    if prop_type and prop_type.lower() == "array":
        if prop.items:
            new_type = Call("ARRAY", sqlalchemy_primitive(prop.items))
        else:
            new_type = Call("ARRAY", ast.Name("String"))

    if new_type is None:
        raise RuntimeError(f"Unsupported field type {prop_type}.")

    return Column(
        new_type, nullable=not prop.required, comment=prop.description, primary_key=prop.primaryKey if prop.primaryKey else None
    ), None


def column_assignment(field_name: str, prop: SchemaProperty) -> tuple[ast.Call, typing.Optional[ast.ClassDef]]:
    return constant_field_value(field_name, prop)


def is_simple_field(prop: SchemaProperty) -> bool:
    prop_type = _get_type(prop) or ""
    return prop_type.lower() not in {"object", "record", "struct"}


def field_definitions(properties: List[SchemaProperty]) -> tuple[list[ast.Expr], list[ast.ClassDef]]:
    annotations: list[ast.Expr] = []
    classes: list[typing.Any] = []
    for prop in properties:
        (ann, new_class) = column_assignment(prop.name, prop)
        annotations.append(ast.Assign(targets=[ast.Name(id=prop.name, ctx=ast.Store())], value=ann, lineno=0))
    return (annotations, classes)


def generate_model_class(
    name: str, schema_obj: SchemaObject, server: Optional[Server] = None, sql_server_type: str = ""
) -> ast.ClassDef:
    (field_assignments, nested_classes) = field_definitions(schema_obj.properties or [])
    documentation = [ast.Expr(ast.Constant(schema_obj.description))] if schema_obj.description else []

    schema = None if server is None else server.schema_
    table_name = ast.Constant(name)
    if sql_server_type == "databricks":
        table_name = ast.Constant(name.lower())

    result = ast.ClassDef(
        name=name.capitalize(),
        bases=[ast.Name(id=DECLARATIVE_BASE, ctx=ast.Load())],
        body=[
            *documentation,
            ast.Assign(targets=[ast.Name("__tablename__")], value=table_name, lineno=0),
            ast.Assign(
                targets=[ast.Name("__table_args__")],
                value=ast.Dict(
                    keys=[ast.Constant("comment"), ast.Constant("schema")],
                    values=[ast.Constant(schema_obj.description), ast.Constant(schema)],
                ),
                lineno=0,
            ),
            *nested_classes,
            *field_assignments,
        ],
        keywords=[],
        decorator_list=[],
    )
    return result
