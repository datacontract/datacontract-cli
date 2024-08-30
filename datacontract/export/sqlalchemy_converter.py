import ast
import typing

import datacontract.model.data_contract_specification as spec
from datacontract.export.exporter import Exporter
from datacontract.export.exporter import _determine_sql_server_type

class SQLAlchemyExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        sql_server_type = _determine_sql_server_type(data_contract, sql_server_type, server)
        return to_sqlalchemy_model_str(data_contract, sql_server_type)
    

DECLARATIVE_BASE = "Base"

def to_sqlalchemy_model_str(contract: spec.DataContractSpecification, sql_server_type: str) -> str:
    classdefs = [generate_model_class(model_name, model) for (model_name, model) in contract.models.items()]
    documentation = (
        [ast.Expr(ast.Constant(contract.info.description))] if (contract.info and contract.info.description) else []
    )

    declarative_base = ast.ClassDef(
        name=DECLARATIVE_BASE,
        bases=[ast.Name(id="DeclarativeBase", ctx=ast.Load())],
        body=[ast.Pass()],
        keywords=[],
        decorator_list=[],
    )
    
    databricks_timestamp = ast.ImportFrom(module="databricks.sqlalchemy", names=[ast.alias(name="TIMESTAMP")])
    timestamp = ast.ImportFrom(module="sqlalchemy", names=[ast.alias(name="TIMESTAMP")])
    result = ast.Module(
        body=[
            ast.ImportFrom(module='sqlalchemy.orm', names=[ast.alias(name='DeclarativeBase')]),
            ast.ImportFrom(module='sqlalchemy', names=[
                ast.alias(name='Column'),
                ast.alias(name='Date'),
                ast.alias(name='Integer'),
                ast.alias(name='Numeric'),
                ]),
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
        args=[
            v
            for v in args
        ],
        keywords=[
            ast.keyword(arg=f'{k}', value=ast.Constant(v)) 
            for (k, v) in kwargs.items()
        ]
    )


def Column(predicate, **kwargs) -> ast.Call:
    return Call("Column", predicate, **kwargs)


def constant_field_value(
    field_name: str, field: spec.Field
) -> tuple[ast.Call, typing.Optional[ast.ClassDef]]:
    sqlalchemy_name = {
        "string": ast.Name("String", ctx=ast.Load()),
        "text": ast.Name("Text", ctx=ast.Load()),
        "varchar": ast.Name("VARCHAR", ctx=ast.Load()),
        "number": Call("Numeric", ast.Constant(field.precision), ast.Constant(field.scale)),
        "decimal": Call("Numeric", ast.Constant(field.precision), ast.Constant(field.scale)),
        "numeric": Call("Numeric", ast.Constant(field.precision), ast.Constant(field.scale)),
        "int": ast.Name("Integer", ctx=ast.Load()),
        "integer": ast.Name("Integer", ctx=ast.Load()),
        "long": ast.Name("BigInteger", ctx=ast.Load()),
        "bigint": ast.Name("BigInteger", ctx=ast.Load()),
        "float": ast.Name("Float", ctx=ast.Load()),
        "double": ast.Name("Double", ctx=ast.Load()),
        "boolean": ast.Name("Boolean", ctx=ast.Load()),
        "timestamp": ast.Name("TIMESTAMP", ctx=ast.Load()),
        "timestamp_tz": ast.Name("TIMESTAMP", ctx=ast.Load()),
        "timestamp_ntz": ast.Name("TIMESTAMP", ctx=ast.Load()),
        "date": ast.Name("Date", ctx=ast.Load()),
        "bytes": ast.Name("LargeBinary", ctx=ast.Load()),
    }
    new_type = sqlalchemy_name.get(field.type, None)
    if new_type is None:
        raise RuntimeError(f"Unsupported field type {field.type}.")

    return Column(new_type, nullable=not field.required, comment=field.description, primary_key=field.primary), None


def column_assignment(field_name: str, field: spec.Field) -> tuple[ast.Call, typing.Optional[ast.ClassDef]]:
    return constant_field_value(field_name, field)

def is_simple_field(field: spec.Field) -> bool:
    return field.type not in set(["object", "record", "struct"])


def field_definitions(fields: dict[str, spec.Field]) -> tuple[list[ast.Expr], list[ast.ClassDef]]:
    annotations: list[ast.Expr] = []
    classes: list[typing.Any] = []
    for field_name, field in fields.items():
        (ann, new_class) = column_assignment(field_name, field)
        annotations.append(ast.Assign(targets=[ast.Name(id=field_name, ctx=ast.Store())], value=ann, lineno=0))
    return (annotations, classes)

def generate_field_class(field_name: str, field: spec.Field) -> ast.ClassDef:
    pass

def generate_model_class(name: str, model_definition: spec.Model) -> ast.ClassDef:
    (field_assignments, nested_classes) = field_definitions(model_definition.fields)
    documentation = [ast.Expr(ast.Constant(model_definition.description))] if model_definition.description else []
    result = ast.ClassDef(
        name=name.capitalize(),
        bases=[ast.Name(id=DECLARATIVE_BASE, ctx=ast.Load())],
        body=[
            *documentation,
            ast.Assign(targets=[ast.Name("__tablename__")], value=ast.Constant(name), lineno=0),
            ast.Assign(targets=[ast.Name("__table_args__")], value=ast.Constant({
                "comment": model_definition.description,
            }), lineno=0),

            *nested_classes,
            *field_assignments
        ],
        keywords=[],
        decorator_list=[],
    )
    return result
