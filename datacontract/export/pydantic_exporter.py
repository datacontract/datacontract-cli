import ast
import typing
from typing import Optional

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty

from datacontract.export.exporter import Exporter


class PydanticExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> dict:
        return to_pydantic_model_str(data_contract)


def _get_description_str(description) -> str | None:
    """Extract a string from a description, handling both string and Description object."""
    if description is None:
        return None
    if isinstance(description, str):
        return description
    # It's a Description object - get purpose or other meaningful field
    if hasattr(description, "purpose") and description.purpose:
        return description.purpose
    if hasattr(description, "usage") and description.usage:
        return description.usage
    return None


def to_pydantic_model_str(contract: OpenDataContractStandard) -> str:
    classdefs = []
    if contract.schema_:
        for schema_obj in contract.schema_:
            classdefs.append(generate_model_class(schema_obj.name, schema_obj))

    desc_str = _get_description_str(contract.description)
    documentation = [ast.Expr(ast.Constant(desc_str))] if desc_str else []
    result = ast.Module(
        body=[
            ast.Import(
                names=[
                    ast.Name("datetime", ctx=ast.Load()),
                    ast.Name("typing", ctx=ast.Load()),
                    ast.Name("pydantic", ctx=ast.Load()),
                    ast.Name("decimal", ctx=ast.Load()),
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


def _get_type(prop: SchemaProperty) -> Optional[str]:
    """Get the logical type from a schema property."""
    return prop.logicalType


def _get_physical_type(prop: SchemaProperty) -> Optional[str]:
    """Get the physical type from a schema property."""
    return prop.physicalType.lower() if prop.physicalType else None


def constant_field_annotation(
    field_name: str, prop: SchemaProperty
) -> tuple[type_annotation_type, typing.Optional[ast.ClassDef]]:
    prop_type = _get_type(prop)
    physical_type = _get_physical_type(prop)

    match prop_type:
        case "string":
            return (ast.Name("str", ctx=ast.Load()), None)
        case "number":
            if physical_type == "decimal":
                return (ast.Attribute(value=ast.Name(id="decimal", ctx=ast.Load()), attr="Decimal"), None)
            # Either integer or float in specification,
            # so we use float.
            return (ast.Name("float", ctx=ast.Load()), None)
        case "integer":
            return (ast.Name("int", ctx=ast.Load()), None)
        case "boolean":
            return (ast.Name("bool", ctx=ast.Load()), None)
        case "date":
            return (ast.Attribute(value=ast.Name(id="datetime", ctx=ast.Load()), attr="datetime"), None)
        case "array":
            if prop.items:
                (annotated_type, new_class) = type_annotation(field_name, prop.items)
                return (list_of(annotated_type), new_class)
            return (list_of(ast.Name("typing.Any", ctx=ast.Load())), None)
        case "object":
            classdef = generate_field_class(field_name.capitalize(), prop)
            return (ast.Name(field_name.capitalize(), ctx=ast.Load()), classdef)
        case _:
            # Check physical type for more specific mappings
            if physical_type:
                if physical_type in ["text", "varchar", "char", "nvarchar"]:
                    return (ast.Name("str", ctx=ast.Load()), None)
                elif physical_type in ["int", "integer", "int32"]:
                    return (ast.Name("int", ctx=ast.Load()), None)
                elif physical_type in ["long", "bigint", "int64"]:
                    return (ast.Name("int", ctx=ast.Load()), None)
                elif physical_type in ["float", "real", "float32"]:
                    return (ast.Name("float", ctx=ast.Load()), None)
                elif physical_type in ["double", "float64"]:
                    return (ast.Name("float", ctx=ast.Load()), None)
                elif physical_type in ["numeric", "number"]:
                    return (ast.Name("float", ctx=ast.Load()), None)
                elif physical_type == "decimal":
                    return (ast.Attribute(value=ast.Name(id="decimal", ctx=ast.Load()), attr="Decimal"), None)
                elif physical_type in ["timestamp", "datetime", "timestamp_tz", "timestamp_ntz"]:
                    return (ast.Attribute(value=ast.Name(id="datetime", ctx=ast.Load()), attr="datetime"), None)
                elif physical_type == "date":
                    return (ast.Attribute(value=ast.Name(id="datetime", ctx=ast.Load()), attr="date"), None)
                elif physical_type in ["bytes", "binary", "bytea"]:
                    return (ast.Name("bytes", ctx=ast.Load()), None)
                elif physical_type == "null":
                    return (ast.Constant("None"), None)
                elif physical_type in ["record", "struct"]:
                    classdef = generate_field_class(field_name.capitalize(), prop)
                    return (ast.Name(field_name.capitalize(), ctx=ast.Load()), classdef)
            # Default to string
            return (ast.Name("str", ctx=ast.Load()), None)


def type_annotation(
    field_name: str, prop: SchemaProperty
) -> tuple[type_annotation_type, typing.Optional[ast.ClassDef]]:
    if prop.required:
        return constant_field_annotation(field_name, prop)
    else:
        (annotated_type, new_classes) = constant_field_annotation(field_name, prop)
        return (optional_of(annotated_type), new_classes)


def is_simple_field(prop: SchemaProperty) -> bool:
    prop_type = _get_type(prop) or ""
    physical_type = (prop.physicalType or "").lower()
    return prop_type not in {"object"} and physical_type not in {"record", "struct"}


def field_definitions(properties: list[SchemaProperty]) -> tuple[list[ast.Expr], list[ast.ClassDef]]:
    annotations = []
    classes = []
    for prop in properties:
        (ann, new_class) = type_annotation(prop.name, prop)
        annotations.append(ast.AnnAssign(target=ast.Name(id=prop.name, ctx=ast.Store()), annotation=ann, simple=1))
        if prop.description and is_simple_field(prop):
            annotations.append(ast.Expr(ast.Constant(prop.description)))
        if new_class:
            classes.append(new_class)
    return (annotations, classes)


def generate_field_class(field_name: str, prop: SchemaProperty) -> ast.ClassDef:
    prop_type = _get_type(prop) or ""
    physical_type = (prop.physicalType or "").lower()
    assert prop_type == "object" or physical_type in {"record", "struct"}
    (annotated_type, new_classes) = field_definitions(prop.properties or [])
    documentation = [ast.Expr(ast.Constant(prop.description))] if prop.description else []
    return ast.ClassDef(
        name=field_name,
        bases=[ast.Attribute(value=ast.Name(id="pydantic", ctx=ast.Load()), attr="BaseModel", ctx=ast.Load())],
        body=[*documentation, *new_classes, *annotated_type],
        keywords=[],
        decorator_list=[],
    )


def generate_model_class(name: str, schema_obj: SchemaObject) -> ast.ClassDef:
    (field_assignments, nested_classes) = field_definitions(schema_obj.properties or [])
    documentation = [ast.Expr(ast.Constant(schema_obj.description))] if schema_obj.description else []
    result = ast.ClassDef(
        name=name.capitalize(),
        bases=[ast.Attribute(value=ast.Name(id="pydantic", ctx=ast.Load()), attr="BaseModel", ctx=ast.Load())],
        body=[*documentation, *nested_classes, *field_assignments],
        keywords=[],
        decorator_list=[],
    )
    return result
