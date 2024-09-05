import ast
import typing

import datacontract.model.data_contract_specification as spec
from datacontract.export.exporter import Exporter
from datacontract.export.exporter import _determine_sql_server_type


class SQLAlchemyExporter(Exporter):
    def export(
        self, data_contract: spec.DataContractSpecification, model, server, sql_server_type, export_args
    ) -> dict:
        sql_server_type = _determine_sql_server_type(data_contract, sql_server_type, server)
        return to_sqlalchemy_model_str(data_contract, sql_server_type, server)


DECLARATIVE_BASE = "Base"


def to_sqlalchemy_model_str(contract: spec.DataContractSpecification, sql_server_type: str = "", server=None) -> str:
    server_obj = contract.servers.get(server)
    classdefs = [
        generate_model_class(model_name, model, server_obj, sql_server_type)
        for (model_name, model) in contract.models.items()
    ]
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


def sqlalchemy_primitive(field: spec.Field):
    sqlalchemy_name = {
        "string": Call("String", ast.Constant(field.maxLength)),
        "text": Call("Text", ast.Constant(field.maxLength)),
        "varchar": Call("VARCHAR", ast.Constant(field.maxLength)),
        "number": Call("Numeric", ast.Constant(field.precision), ast.Constant(field.scale)),
        "decimal": Call("Numeric", ast.Constant(field.precision), ast.Constant(field.scale)),
        "numeric": Call("Numeric", ast.Constant(field.precision), ast.Constant(field.scale)),
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
        "bytes": Call("LargeBinary", ast.Constant(field.maxLength)),
    }
    return sqlalchemy_name.get(field.type)


def constant_field_value(field_name: str, field: spec.Field) -> tuple[ast.Call, typing.Optional[ast.ClassDef]]:
    new_type = sqlalchemy_primitive(field)
    match field.type:
        case "array":
            new_type = Call("ARRAY", sqlalchemy_primitive(field.items))
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


def generate_model_class(
    name: str, model_definition: spec.Model, server=None, sql_server_type: str = ""
) -> ast.ClassDef:
    (field_assignments, nested_classes) = field_definitions(model_definition.fields)
    documentation = [ast.Expr(ast.Constant(model_definition.description))] if model_definition.description else []

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
                    values=[ast.Constant(model_definition.description), ast.Constant(schema)],
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
