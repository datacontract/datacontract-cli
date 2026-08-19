"""Import Pydantic models into an ODCS data contract.

The module is read with :mod:`ast` and never imported, so a contract can be
derived from a service's models without installing that service's dependencies
or executing any of its code.

Module-level Pydantic models become schema objects, except those used as the
type of another model's field: those are inlined as nested objects, which is
also what makes the round trip with ``datacontract export pydantic-model`` hold.
"""

import ast
from typing import Any, Dict, List, Optional, Tuple

from open_data_contract_standard.model import (
    DataQuality,
    Description,
    OpenDataContractStandard,
    SchemaProperty,
)

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import create_odcs, create_property, create_schema_object
from datacontract.model.exceptions import DataContractException

# Python type -> (ODCS logical type, physical type). Keyed by the last segment of
# the annotation, so `datetime.datetime` and a bare `datetime` both resolve.
_SCALAR_TYPES: Dict[str, Tuple[str, str]] = {
    "str": ("string", "str"),
    "int": ("integer", "int"),
    "float": ("number", "float"),
    "bool": ("boolean", "bool"),
    "bytes": ("array", "bytes"),
    "Decimal": ("number", "decimal"),
    "datetime": ("timestamp", "datetime"),
    "date": ("date", "date"),
    "time": ("time", "time"),
    "timedelta": ("string", "timedelta"),
    "UUID": ("string", "uuid"),
}

# Pydantic's constrained string aliases carry a format the logical type cannot.
_FORMAT_TYPES: Dict[str, str] = {
    "EmailStr": "email",
    "AnyUrl": "uri",
    "AnyHttpUrl": "uri",
    "HttpUrl": "uri",
    "IPvAnyAddress": "ipv4",
}

_ARRAY_CONTAINERS = {"list", "List", "set", "Set", "frozenset", "FrozenSet", "Sequence", "tuple", "Tuple"}
_OBJECT_CONTAINERS = {"dict", "Dict", "Mapping", "MutableMapping", "DefaultDict", "OrderedDict"}

# `Field(max_length=...)` -> the ODCS logicalTypeOptions key it maps onto.
_CONSTRAINT_KEYWORDS = {
    "min_length": "min_length",
    "max_length": "max_length",
    "pattern": "pattern",
    "regex": "pattern",
    "ge": "minimum",
    "le": "maximum",
    "gt": "exclusive_minimum",
    "lt": "exclusive_maximum",
}

# Guards against a model that references itself, directly or through a cycle.
_MAX_NESTING_DEPTH = 12


def _dotted_name(node: ast.AST) -> Optional[str]:
    """Return the dotted source of a name-like annotation, e.g. ``datetime.datetime``."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        # A forward reference: `parent: "Address"`.
        return node.value
    return None


def _last_segment(node: ast.AST) -> Optional[str]:
    dotted = _dotted_name(node)
    return dotted.split(".")[-1] if dotted else None


def _subscript_args(node: ast.Subscript) -> List[ast.expr]:
    """The arguments of a subscript, whether or not it is a tuple."""
    if isinstance(node.slice, ast.Tuple):
        return list(node.slice.elts)
    return [node.slice]


def _is_none(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is None


def _unwrap_optional(node: ast.expr) -> Tuple[ast.expr, bool]:
    """Strip ``Optional[X]``, ``Union[X, None]`` and ``X | None`` down to ``X``."""
    if isinstance(node, ast.Subscript):
        container = _last_segment(node.value)
        if container == "Optional":
            return _subscript_args(node)[0], True
        if container == "Union":
            args = _subscript_args(node)
            remaining = [arg for arg in args if not _is_none(arg)]
            if len(remaining) < len(args) and remaining:
                inner = remaining[0] if len(remaining) == 1 else node
                return inner, True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        operands = _flatten_union(node)
        remaining = [operand for operand in operands if not _is_none(operand)]
        if len(remaining) < len(operands) and remaining:
            inner = remaining[0] if len(remaining) == 1 else node
            return inner, True
    return node, False


def _flatten_union(node: ast.expr) -> List[ast.expr]:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _flatten_union(node.left) + _flatten_union(node.right)
    return [node]


def _unwrap_annotated(node: ast.expr) -> Tuple[ast.expr, List[ast.expr]]:
    """Split ``Annotated[X, meta...]`` into ``X`` and its metadata."""
    if isinstance(node, ast.Subscript) and _last_segment(node.value) == "Annotated":
        args = _subscript_args(node)
        if args:
            return args[0], args[1:]
    return node, []


def _literal_value(node: ast.AST) -> Any:
    """The Python value of a literal node, or ``None`` if it is not one."""
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return None


def _valid_values_quality(values: List[Any]) -> DataQuality:
    """Express an enum as the same quality rule the JSON Schema importer emits."""
    return DataQuality(type="library", metric="invalidValues", arguments={"validValues": values}, mustBe=0)


def _scalar_from_values(values: List[Any]) -> Tuple[str, str]:
    """Infer a logical type from the members of an enum or ``Literal``."""
    if values and all(isinstance(value, bool) for value in values):
        return "boolean", "bool"
    if values and all(isinstance(value, int) and not isinstance(value, bool) for value in values):
        return "integer", "int"
    if values and all(isinstance(value, float) for value in values):
        return "number", "float"
    return "string", "str"


class _FieldInfo:
    """The parts of a field assignment that are not the annotation."""

    def __init__(self) -> None:
        self.description: Optional[str] = None
        self.has_default: bool = False
        self.examples: Optional[List[Any]] = None
        self.constraints: Dict[str, Any] = {}


def _parse_field_call(call: ast.Call, info: _FieldInfo) -> None:
    """Read description, default and constraints out of a ``Field(...)`` call."""
    # A positional `...` marks the field required; any other positional is a default.
    for arg in call.args:
        if isinstance(arg, ast.Constant) and arg.value is Ellipsis:
            continue
        info.has_default = True

    for keyword in call.keywords:
        if keyword.arg == "description":
            value = _literal_value(keyword.value)
            if isinstance(value, str):
                info.description = value
        elif keyword.arg == "examples":
            value = _literal_value(keyword.value)
            if isinstance(value, list):
                info.examples = value
        elif keyword.arg == "default":
            if not (isinstance(keyword.value, ast.Constant) and keyword.value.value is Ellipsis):
                info.has_default = True
        elif keyword.arg == "default_factory":
            info.has_default = True
        elif keyword.arg in _CONSTRAINT_KEYWORDS:
            value = _literal_value(keyword.value)
            if value is not None:
                info.constraints[_CONSTRAINT_KEYWORDS[keyword.arg]] = value


def _is_field_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and _last_segment(node.func) == "Field"


def _field_info(assign: ast.AnnAssign, metadata: List[ast.expr]) -> _FieldInfo:
    info = _FieldInfo()

    # `x: Annotated[int, Field(ge=0)]` carries the constraints in the metadata.
    for meta in metadata:
        if _is_field_call(meta):
            _parse_field_call(meta, info)

    if assign.value is not None:
        if _is_field_call(assign.value):
            _parse_field_call(assign.value, info)
        elif not (isinstance(assign.value, ast.Constant) and assign.value.value is Ellipsis):
            info.has_default = True

    return info


class _ModuleIndex:
    """The Pydantic models and enums declared in one module."""

    def __init__(self, tree: ast.Module) -> None:
        self.models: Dict[str, ast.ClassDef] = {}
        self.enums: Dict[str, List[Any]] = {}
        self.top_level: List[str] = []
        self._collect(tree)

    def _base_names(self, node: ast.ClassDef) -> List[str]:
        return [name for name in (_last_segment(base) for base in node.bases) if name]

    def _collect(self, tree: ast.Module) -> None:
        # `from pydantic import BaseModel as Base` still declares models.
        model_bases = {"BaseModel"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "pydantic":
                for alias in node.names:
                    if alias.name == "BaseModel" and alias.asname:
                        model_bases.add(alias.asname)

        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        for node in classes:
            bases = self._base_names(node)
            if "Enum" in bases or "StrEnum" in bases or "IntEnum" in bases:
                self.enums[node.name] = self._enum_values(node)

        # Subclassing a model makes a model too, so grow the set until it settles.
        changed = True
        while changed:
            changed = False
            for node in classes:
                if node.name in self.models:
                    continue
                if model_bases.intersection(self._base_names(node)):
                    self.models[node.name] = node
                    model_bases.add(node.name)
                    changed = True

        self.top_level = [
            node.name for node in tree.body if isinstance(node, ast.ClassDef) and node.name in self.models
        ]

    @staticmethod
    def _enum_values(node: ast.ClassDef) -> List[Any]:
        values = []
        for statement in node.body:
            if isinstance(statement, ast.Assign) and statement.targets:
                value = _literal_value(statement.value)
                if value is not None:
                    values.append(value)
        return values


def _field_statements(node: ast.ClassDef) -> List[Tuple[ast.AnnAssign, Optional[str]]]:
    """The annotated fields of a class, each with the docstring that follows it.

    ``datacontract export pydantic`` writes field descriptions as a bare string
    below the annotation, so reading them back keeps the round trip lossless.
    """
    statements: List[Tuple[ast.AnnAssign, Optional[str]]] = []
    body = node.body
    for index, statement in enumerate(body):
        if not isinstance(statement, ast.AnnAssign) or not isinstance(statement.target, ast.Name):
            continue
        name = statement.target.id
        if name.startswith("_") or name == "model_config":
            continue
        if _last_segment(statement.annotation) == "ClassVar":
            continue

        docstring = None
        following = body[index + 1] if index + 1 < len(body) else None
        if (
            isinstance(following, ast.Expr)
            and isinstance(following.value, ast.Constant)
            and isinstance(following.value.value, str)
        ):
            docstring = following.value.value
        statements.append((statement, docstring))
    return statements


def _referenced_models(index: _ModuleIndex) -> set:
    """Model names used as the type of some field, and so nested rather than root."""
    referenced = set()
    for node in index.models.values():
        for assign, _ in _field_statements(node):
            for annotation in ast.walk(assign.annotation):
                name = _last_segment(annotation) if isinstance(annotation, (ast.Name, ast.Attribute)) else None
                if name in index.models and name != node.name:
                    referenced.add(name)
    return referenced


def _properties(node: ast.ClassDef, index: _ModuleIndex, depth: int) -> List[SchemaProperty]:
    return [
        _to_property(assign.target.id, assign, docstring, index, depth) for assign, docstring in _field_statements(node)
    ]


def _to_property(
    name: str, assign: ast.AnnAssign, docstring: Optional[str], index: _ModuleIndex, depth: int
) -> SchemaProperty:
    annotation, metadata = _unwrap_annotated(assign.annotation)
    annotation, optional = _unwrap_optional(annotation)
    annotation, inner_metadata = _unwrap_annotated(annotation)
    info = _field_info(assign, metadata + inner_metadata)

    resolved = _resolved_kwargs(annotation, index, depth)
    resolved.update(info.constraints)

    return create_property(
        name=name,
        description=info.description or docstring,
        required=not optional and not info.has_default,
        examples=info.examples,
        **resolved,
    )


def _resolved_kwargs(annotation: ast.expr, index: _ModuleIndex, depth: int) -> Dict[str, Any]:
    """The ``create_property`` keywords describing an annotation, constraints flattened."""
    resolved = _resolve_annotation(annotation, index, depth)
    resolved.update(resolved.pop("constraints", {}))
    return resolved


def _resolve_annotation(annotation: ast.expr, index: _ModuleIndex, depth: int) -> Dict[str, Any]:
    """Map a type annotation onto the ODCS fields describing it."""
    if depth > _MAX_NESTING_DEPTH:
        return {"logical_type": "object", "physical_type": "object"}

    if isinstance(annotation, ast.Subscript):
        container = _last_segment(annotation.value)
        args = _subscript_args(annotation)

        if container == "Literal":
            values = [_literal_value(arg) for arg in args]
            values = [value for value in values if value is not None]
            logical_type, physical_type = _scalar_from_values(values)
            return {
                "logical_type": logical_type,
                "physical_type": physical_type,
                "quality": [_valid_values_quality(values)] if values else None,
            }

        if container in _ARRAY_CONTAINERS:
            element, _ = _unwrap_annotated(args[0]) if args else (None, [])
            items = None
            if element is not None and not (isinstance(element, ast.Constant) and element.value is Ellipsis):
                element, _ = _unwrap_optional(element)
                items = create_property(name="items", **_resolved_kwargs(element, index, depth + 1))
            return {"logical_type": "array", "physical_type": container.lower(), "items": items}

        if container in _OBJECT_CONTAINERS:
            return {"logical_type": "object", "physical_type": "map"}

    dotted = _dotted_name(annotation)
    segment = dotted.split(".")[-1] if dotted else None

    if segment in index.models:
        nested = index.models[segment]
        return {
            "logical_type": "object",
            "physical_type": "object",
            "properties": _properties(nested, index, depth + 1) or None,
        }

    if segment in index.enums:
        values = index.enums[segment]
        logical_type, physical_type = _scalar_from_values(values)
        return {
            "logical_type": logical_type,
            "physical_type": physical_type,
            "quality": [_valid_values_quality(values)] if values else None,
        }

    if segment in _FORMAT_TYPES:
        return {"logical_type": "string", "physical_type": "str", "constraints": {"format": _FORMAT_TYPES[segment]}}

    if segment in _SCALAR_TYPES:
        logical_type, physical_type = _SCALAR_TYPES[segment]
        return {"logical_type": logical_type, "physical_type": physical_type}

    # An unknown annotation is still a column; describe it as a string rather
    # than dropping the field.
    return {"logical_type": "string", "physical_type": segment or "str"}


def _module_description(tree: ast.Module) -> Optional[str]:
    """The contract description, from the module docstring or a bare string.

    ``datacontract export pydantic-model`` writes it below the imports rather
    than as a docstring, so both spellings are read back.
    """
    docstring = ast.get_docstring(tree)
    if docstring:
        return docstring
    for statement in tree.body:
        if isinstance(statement, ast.ClassDef):
            break
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant):
            if isinstance(statement.value.value, str):
                return statement.value.value
    return None


def import_pydantic(source: str) -> OpenDataContractStandard:
    """Read a Python module of Pydantic models into an ODCS data contract."""
    try:
        with open(source, "r", encoding="utf-8") as file:
            tree = ast.parse(file.read(), filename=source)
    except OSError as exception:
        raise DataContractException(
            type="file",
            name="Read Pydantic models",
            reason=f"Failed to read Python file: {source}",
            engine="datacontract-cli",
            original_exception=exception,
        )
    except SyntaxError as exception:
        raise DataContractException(
            type="schema",
            name="Parse Pydantic models",
            reason=f"Failed to parse Python file: {source}",
            engine="datacontract-cli",
            original_exception=exception,
        )

    index = _ModuleIndex(tree)
    if not index.models:
        raise DataContractException(
            type="schema",
            name="Parse Pydantic models",
            reason=f"No Pydantic models found in {source}",
            engine="datacontract-cli",
            result="failed",
        )

    nested = _referenced_models(index)
    roots = [name for name in index.top_level if name not in nested] or index.top_level

    odcs = create_odcs()
    purpose = _module_description(tree)
    if purpose:
        odcs.description = Description(purpose=purpose)
    odcs.schema_ = [
        create_schema_object(
            name=name,
            physical_type="object",
            description=ast.get_docstring(index.models[name]),
            properties=_properties(index.models[name], index, depth=0),
        )
        for name in roots
    ]
    return odcs


class PydanticImporter(Importer):
    def import_source(self, source: str, import_args: dict = None) -> OpenDataContractStandard:
        return import_pydantic(source)
