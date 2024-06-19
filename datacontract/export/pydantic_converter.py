import ast
import typing

import datacontract.model.data_contract_specification as spec
from datacontract.export.exporter import Exporter


class PydanticExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        return to_pydantic_model_str(data_contract)


def to_pydantic_model_str(contract: spec.DataContractSpecification) -> str:
    classdefs = [generate_model_class(model_name, model) for (model_name, model) in contract.models.items()]
    documentation = (
        [ast.Expr(ast.Constant(contract.info.description))] if (contract.info and contract.info.description) else []
    )
    result = ast.Module(
        body=[
            ast.Import(
                names=[
                    ast.Name("datetime", ctx=ast.Load()),
                    ast.Name("typing", ctx=ast.Load()),
                    ast.Name("pydantic", ctx=ast.Load()),
                ]
            ),
            *documentation,
            *classdefs,
        ],
        type_ignores=[],
    )
    return ast.unparse(result)


def optional_of(node) -> ast.Subscript:
    return ast.Subscript(
        value=ast.Attribute(ast.Name(id="typing", ctx=ast.Load()), attr="Optional", ctx=ast.Load()), slice=node
    )


def list_of(node) -> ast.Subscript:
    return ast.Subscript(value=ast.Name(id="list", ctx=ast.Load()), slice=node)


def product_of(nodes: list[typing.Any]) -> ast.Subscript:
    return ast.Subscript(
        value=ast.Attribute(value=ast.Name(id="typing", ctx=ast.Load()), attr="Product", ctx=ast.Load()),
        slice=ast.Tuple(nodes, ctx=ast.Load()),
    )


type_annotation_type = typing.Union[ast.Name, ast.Attribute, ast.Constant, ast.Subscript]


def constant_field_annotation(
    field_name: str, field: spec.Field
) -> tuple[type_annotation_type, typing.Optional[ast.ClassDef]]:
    match field.type:
        case "string" | "text" | "varchar":
            return (ast.Name("str", ctx=ast.Load()), None)
        case "number", "decimal", "numeric":
            # Either integer or float in specification,
            # so we use float.
            return (ast.Name("float", ctx=ast.Load()), None)
        case "int" | "integer" | "long" | "bigint":
            return (ast.Name("int", ctx=ast.Load()), None)
        case "float" | "double":
            return (ast.Name("float", ctx=ast.Load()), None)
        case "boolean":
            return (ast.Name("bool", ctx=ast.Load()), None)
        case "timestamp" | "timestamp_tz" | "timestamp_ntz":
            return (ast.Attribute(value=ast.Name(id="datetime", ctx=ast.Load()), attr="datetime"), None)
        case "date":
            return (ast.Attribute(value=ast.Name(id="datetime", ctx=ast.Load()), attr="date"), None)
        case "bytes":
            return (ast.Name("bytes", ctx=ast.Load()), None)
        case "null":
            return (ast.Constant("None"), None)
        case "array":
            (annotated_type, new_class) = type_annotation(field_name, field.items)
            return (list_of(annotated_type), new_class)
        case "object" | "record" | "struct":
            classdef = generate_field_class(field_name.capitalize(), field)
            return (ast.Name(field_name.capitalize(), ctx=ast.Load()), classdef)
        case _:
            raise RuntimeError(f"Unsupported field type {field.type}.")


def type_annotation(field_name: str, field: spec.Field) -> tuple[type_annotation_type, typing.Optional[ast.ClassDef]]:
    if field.required:
        return constant_field_annotation(field_name, field)
    else:
        (annotated_type, new_classes) = constant_field_annotation(field_name, field)
        return (optional_of(annotated_type), new_classes)


def is_simple_field(field: spec.Field) -> bool:
    return field.type not in set(["object", "record", "struct"])


def field_definitions(fields: dict[str, spec.Field]) -> tuple[list[ast.Expr], list[ast.ClassDef]]:
    annotations = []
    classes = []
    for field_name, field in fields.items():
        (ann, new_class) = type_annotation(field_name, field)
        annotations.append(ast.AnnAssign(target=ast.Name(id=field_name, ctx=ast.Store()), annotation=ann, simple=1))
        if field.description and is_simple_field(field):
            annotations.append(ast.Expr(ast.Constant(field.description)))
        if new_class:
            classes.append(new_class)
    return (annotations, classes)


def generate_field_class(field_name: str, field: spec.Field) -> ast.ClassDef:
    assert field.type in set(["object", "record", "struct"])
    (annotated_type, new_classes) = field_definitions(field.fields)
    documentation = [ast.Expr(ast.Constant(field.description))] if field.description else []
    return ast.ClassDef(
        name=field_name,
        bases=[ast.Attribute(value=ast.Name(id="pydantic", ctx=ast.Load()), attr="BaseModel", ctx=ast.Load())],
        body=[*documentation, *new_classes, *annotated_type],
        keywords=[],
        decorator_list=[],
    )


def generate_model_class(name: str, model_definition: spec.Model) -> ast.ClassDef:
    (field_assignments, nested_classes) = field_definitions(model_definition.fields)
    documentation = [ast.Expr(ast.Constant(model_definition.description))] if model_definition.description else []
    result = ast.ClassDef(
        name=name.capitalize(),
        bases=[ast.Attribute(value=ast.Name(id="pydantic", ctx=ast.Load()), attr="BaseModel", ctx=ast.Load())],
        body=[*documentation, *nested_classes, *field_assignments],
        keywords=[],
        decorator_list=[],
    )
    return result
