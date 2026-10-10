"""Export a data contract as Polars schemas.

`datacontract export polars` emits a Python module that builds one ``pl.Schema``
per schema of the contract. It only produces text, so polars does not need to be
installed to run it: the mapping produces the small type tree below, which is
rendered as the Polars expressions it stands for.

The physical type wins when it names a width or precision that the logical type
leaves open (``int32``, ``float32``, ``decimal(10,2)``, ``timestamp(9)``), then the
``format`` of an integer or number (``i16``, ``u32``, ``f32``), then the logical type.
"""

import json
import keyword
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty

from datacontract.export.exporter import Exporter
from datacontract.model.map_type import get_map_key, get_map_value, is_map
from datacontract.model.vector_type import is_vector, vector_dimensions, vector_element_type

# Polars decimals are 128-bit integers with a scale, so they hold at most 38 digits.
_MAX_DECIMAL_PRECISION = 38

_INTEGER_FORMATS = {
    "i8": "Int8",
    "i16": "Int16",
    "i32": "Int32",
    "i64": "Int64",
    "i128": "Int128",
    "u8": "UInt8",
    "u16": "UInt16",
    "u32": "UInt32",
    "u64": "UInt64",
    "u128": "UInt128",
}

_NUMBER_FORMATS = {
    "f32": "Float32",
    "f64": "Float64",
}

# Polars has no bfloat16; Float32 holds every bfloat16 value exactly. A binary
# vector has one bit per element.
_VECTOR_ELEMENT_TYPES = {
    "bfloat16": "Float32",
    "binary": "Boolean",
    "float16": "Float16",
    "float32": "Float32",
    "float64": "Float64",
    "int8": "Int8",
    "uint8": "UInt8",
}

# Physical type names, without their parameters, that mean the same width on every
# platform. `int8` is left out: it is a 64-bit integer in Postgres and DuckDB and an
# 8-bit one in ClickHouse.
_PHYSICAL_TYPES = {
    "string": "String",
    "varchar": "String",
    "text": "String",
    "char": "String",
    "nvarchar": "String",
    "nchar": "String",
    "character varying": "String",
    "boolean": "Boolean",
    "bool": "Boolean",
    "tinyint": "Int8",
    "int1": "Int8",
    "smallint": "Int16",
    "int2": "Int16",
    "int16": "Int16",
    "short": "Int16",
    "integer": "Int32",
    "int": "Int32",
    "int4": "Int32",
    "int32": "Int32",
    "mediumint": "Int32",
    "bigint": "Int64",
    "long": "Int64",
    "int64": "Int64",
    "int128": "Int128",
    "hugeint": "Int128",
    "uint8": "UInt8",
    "utinyint": "UInt8",
    "tinyint unsigned": "UInt8",
    "uint16": "UInt16",
    "usmallint": "UInt16",
    "smallint unsigned": "UInt16",
    "uint32": "UInt32",
    "uinteger": "UInt32",
    "mediumint unsigned": "UInt32",
    "int unsigned": "UInt32",
    "integer unsigned": "UInt32",
    "uint64": "UInt64",
    "ubigint": "UInt64",
    "bigint unsigned": "UInt64",
    "uint128": "UInt128",
    "uhugeint": "UInt128",
    "float16": "Float16",
    "float": "Float32",
    "real": "Float32",
    "float4": "Float32",
    "float32": "Float32",
    "double": "Float64",
    "double precision": "Float64",
    "float8": "Float64",
    "float64": "Float64",
    "date": "Date",
    "time": "Time",
    "binary": "Binary",
    "varbinary": "Binary",
    "bytes": "Binary",
    "bytea": "Binary",
    "blob": "Binary",
}

_ZONED_TIMESTAMPS = {
    "timestamp_tz",
    "timestamptz",
    "timestamp_ltz",
    "timestamp with time zone",
    "timestamp with local time zone",
}
_NAIVE_TIMESTAMPS = {"timestamp_ntz", "timestamp without time zone", "datetime", "datetime2"}


@dataclass(frozen=True)
class PolarsType:
    """A Polars data type, held as the expression that builds it, such as ``pl.Int32``."""

    expression: str


@dataclass(frozen=True)
class PolarsList(PolarsType):
    expression: str = "pl.List"
    inner: PolarsType = PolarsType("pl.String")


@dataclass(frozen=True)
class PolarsStruct(PolarsType):
    expression: str = "pl.Struct"
    fields: Tuple[Tuple[str, PolarsType], ...] = ()


class PolarsExporter(Exporter):
    """
    Exporter class for exporting data contracts to Polars schemas.
    """

    def export(
        self,
        data_contract: OpenDataContractStandard,
        schema_name,
        server,
        sql_server_type,
        export_args,
    ) -> str:
        """
        Export the given data contract to Polars schemas.

        Args:
            data_contract (OpenDataContractStandard): The data contract specification.
            schema_name: The name of the schema to export, or 'all' for all schemas.
            server: Not used in this implementation.
            sql_server_type: Not used in this implementation.
            export_args: Not used in this implementation.

        Returns:
            str: A Python module that defines a ``pl.Schema`` for each exported schema.
        """
        return to_polars(data_contract, schema_name)


def to_polars(contract: OpenDataContractStandard, schema_name: str = "all") -> str:
    """
    Convert a data contract to a Python module defining its Polars schemas.

    Each schema is assigned to a variable named after it, made a valid Python
    identifier that is no keyword, unique, and not `pl`.

    Args:
        contract (OpenDataContractStandard): The data contract specification.
        schema_name (str): The name of the schema to export, or 'all' for all schemas.

    Returns:
        str: The source code of the module.
    """
    schemas = contract.schema_ or []
    if schema_name != "all":
        schemas = [schema_obj for schema_obj in schemas if schema_obj.name == schema_name]
        if not schemas:
            raise RuntimeError(
                f"Schema '{schema_name}' not found in the data contract. "
                f"Available schemas: {[schema_obj.name for schema_obj in contract.schema_ or []]}"
            )

    blocks = ["import polars as pl"]
    used = {"pl"}
    for schema_obj in schemas:
        name = "".join(c if ("_" + c).isidentifier() else "_" for c in (schema_obj.name or "schema"))
        if not name.isidentifier():
            name = "_" + name
        if keyword.iskeyword(name):
            name += "_"
        variable = name
        suffix = 2
        while variable in used:
            variable = f"{name}_{suffix}"
            suffix += 1
        used.add(variable)

        fields = _to_struct(schema_obj.properties or []).fields
        if fields:
            blocks.append(f"{variable} = pl.Schema(\n    {_render_fields(fields, '    ')}\n)")
        else:
            blocks.append(f"{variable} = pl.Schema({{}})")
    return "\n\n".join(blocks)


def to_polars_type(prop: SchemaProperty) -> PolarsType:
    """
    Convert a property to a Polars data type.

    Args:
        prop (SchemaProperty): The property to convert.

    Returns:
        PolarsType: The corresponding Polars data type.
    """
    logical_type = prop.logicalType.lower() if prop.logicalType else None
    physical_type = " ".join(prop.physicalType.lower().split()) if prop.physicalType else None

    if (logical_type is None and physical_type is None) or physical_type == "null":
        return PolarsType("pl.Null")

    if logical_type == "array":
        return PolarsList(inner=to_polars_type(prop.items) if prop.items else PolarsType("pl.String"))

    if is_vector(prop):
        element = PolarsType("pl." + _VECTOR_ELEMENT_TYPES.get(vector_element_type(prop), "Float32"))
        dimensions = vector_dimensions(prop)
        if dimensions is None:
            return PolarsList(inner=element)
        return PolarsType(f"pl.Array({element.expression}, {dimensions})")

    # Polars has no map type: like an Arrow map read into Polars, a map is a list of key-value structs.
    if is_map(prop):
        key = get_map_key(prop)
        value = get_map_value(prop)
        return PolarsList(
            inner=PolarsStruct(
                fields=(
                    ("key", to_polars_type(key) if key is not None else PolarsType("pl.String")),
                    ("value", to_polars_type(value) if value is not None else PolarsType("pl.String")),
                )
            )
        )

    # The physical type without its parameters: `timestamp(6) with time zone` is `timestamp with time zone`.
    base_type = " ".join(re.sub(r"\([^)]*\)", " ", physical_type).split()) if physical_type else None
    if logical_type == "object" or base_type in ["object", "record", "struct"]:
        return _to_struct(prop.properties or [])

    if physical_type:
        parameters = []
        parenthesized = re.search(r"\(([^)]*)\)", physical_type)
        if parenthesized and all(part.strip().isdigit() for part in parenthesized.group(1).split(",")):
            parameters = [int(part) for part in parenthesized.group(1).split(",")]
        if base_type in ["decimal", "numeric"] or (base_type == "number" and parameters):
            precision, scale = _custom_precision_scale(prop)
            if precision is None and scale is None and parameters:
                precision = parameters[0]
                scale = parameters[1] if len(parameters) > 1 else 0
            return _decimal_type(prop, precision, scale)
        if base_type == "timestamp":
            return _datetime_type(prop, None, parameters)
        if base_type in _ZONED_TIMESTAMPS:
            return _datetime_type(prop, True, parameters)
        if base_type in _NAIVE_TIMESTAMPS:
            return _datetime_type(prop, False, parameters)
        if base_type in _PHYSICAL_TYPES:
            return PolarsType("pl." + _PHYSICAL_TYPES[base_type])

    format_option = _logical_type_option(prop, "format")
    format_name = str(format_option).lower() if format_option is not None else None
    if logical_type == "integer" and format_name in _INTEGER_FORMATS:
        return PolarsType("pl." + _INTEGER_FORMATS[format_name])
    if logical_type == "number" and format_name in _NUMBER_FORMATS:
        return PolarsType("pl." + _NUMBER_FORMATS[format_name])

    match logical_type:
        case "string":
            return PolarsType("pl.String")
        case "integer":
            return PolarsType("pl.Int64")
        case "number":
            precision, scale = _custom_precision_scale(prop)
            if precision is not None or scale is not None:
                return _decimal_type(prop, precision, scale)
            return PolarsType("pl.Float64")
        case "boolean":
            return PolarsType("pl.Boolean")
        case "date":
            return PolarsType("pl.Date")
        case "timestamp":
            return _datetime_type(prop, None, [])
        case "time":
            return PolarsType("pl.Time")
        case _:
            return PolarsType("pl.String")


def _to_struct(properties: List[SchemaProperty]) -> PolarsStruct:
    return PolarsStruct(fields=tuple((prop.name, to_polars_type(prop)) for prop in properties))


def _decimal_type(prop: SchemaProperty, precision: Optional[int], scale: Optional[int]) -> PolarsType:
    """A decimal; without a precision, Polars chooses it, and without a scale it is 0, as in SQL."""
    if precision is not None and precision > _MAX_DECIMAL_PRECISION:
        raise RuntimeError(
            f"Polars decimals hold at most {_MAX_DECIMAL_PRECISION} digits, "
            f"but '{prop.name}' has a precision of {precision}."
        )
    if precision is None and not scale:
        return PolarsType("pl.Decimal()")
    if precision is None:
        return PolarsType(f"pl.Decimal(scale={scale})")
    return PolarsType(f"pl.Decimal(precision={precision}, scale={scale or 0})")


def _datetime_type(prop: SchemaProperty, zoned: Optional[bool], parameters: List[int]) -> PolarsType:
    """A datetime in the time unit of the physical type's precision, microseconds without one.

    `zoned` comes from the physical type; when it does not say, the `timezone`
    option of the logical type does, and its `defaultTimezone` names the zone.
    """
    if zoned is None:
        zoned = _logical_type_option(prop, "timezone") is True
    time_unit = "us"
    if parameters:
        time_unit = "ms" if parameters[0] <= 3 else "us" if parameters[0] <= 6 else "ns"
    if not zoned:
        return PolarsType(f'pl.Datetime(time_unit="{time_unit}")')
    time_zone = _logical_type_option(prop, "defaultTimezone") or "UTC"
    return PolarsType(f'pl.Datetime(time_unit="{time_unit}", time_zone={_string_literal(str(time_zone))})')


def _logical_type_option(prop: SchemaProperty, key: str):
    if prop.logicalTypeOptions is None:
        return None
    return prop.logicalTypeOptions.get(key)


def _custom_precision_scale(prop: SchemaProperty) -> Tuple[Optional[int], Optional[int]]:
    """The `precision` and `scale` custom properties, which DCS contracts converted to ODCS carry."""
    values = {"precision": None, "scale": None}
    for custom_property in prop.customProperties or []:
        if custom_property.property in values and str(custom_property.value).strip().isdigit():
            values[custom_property.property] = int(str(custom_property.value).strip())
    return values["precision"], values["scale"]


def _string_literal(value: str) -> str:
    """A double-quoted Python string literal for `value`."""
    return json.dumps(value, ensure_ascii=False)


def _render(data_type: PolarsType, indent: str) -> str:
    """The expression building `data_type`, on a line indented by `indent`.

    A struct with fields spreads over several lines with a trailing comma after
    every field, the layout `ruff format` keeps for it.
    """
    if isinstance(data_type, PolarsStruct):
        if not data_type.fields:
            return "pl.Struct({})"
        return f"pl.Struct(\n{indent}    {_render_fields(data_type.fields, indent + '    ')}\n{indent})"
    if isinstance(data_type, PolarsList):
        inner = _render(data_type.inner, indent + "    ")
        if "\n" not in inner:
            return f"pl.List({inner})"
        return f"pl.List(\n{indent}    {inner}\n{indent})"
    return data_type.expression


def _render_fields(fields: Tuple[Tuple[str, PolarsType], ...], indent: str) -> str:
    """A dict literal from field name to type, whose opening brace sits on a line indented by `indent`."""
    lines = [
        f"{indent}    {_string_literal(name)}: {_render(data_type, indent + '    ')}," for name, data_type in fields
    ]
    return "{\n" + "\n".join(lines) + f"\n{indent}}}"
