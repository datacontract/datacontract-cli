"""Export a data contract as Spark schemas.

`datacontract export spark` emits the schema as Python source — `StructType([...])`
— so building real ``pyspark.sql.types`` objects just to print them back out would
make pyspark a hard requirement of a command that only produces text. The mapping
therefore produces the small ``SparkDataType`` tree below, which carries the same
type names and parameters, and ``to_pyspark`` turns that into the real objects for
the callers that want them (``to_spark_dict``, ``to_pyspark_schema``). pyspark is
imported there and nowhere else in this module.
"""

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty

from datacontract.export.exporter import Exporter
from datacontract.model.map_type import get_map_key, get_map_value, is_map

if TYPE_CHECKING:
    from pyspark.sql import types

# Spark's own DecimalType defaults, for a contract that asks for a decimal without
# saying how wide.
_DEFAULT_DECIMAL_PRECISION = 10
_DEFAULT_DECIMAL_SCALE = 0


@dataclass(frozen=True)
class SparkDataType:
    """A Spark type, named exactly as the ``pyspark.sql.types`` class it stands for."""

    name: str


@dataclass(frozen=True)
class SparkDecimalType(SparkDataType):
    name: str = "DecimalType"
    precision: int = _DEFAULT_DECIMAL_PRECISION
    scale: int = _DEFAULT_DECIMAL_SCALE


@dataclass(frozen=True)
class SparkStructType(SparkDataType):
    name: str = "StructType"
    fields: Tuple["SparkField", ...] = ()


@dataclass(frozen=True)
class SparkArrayType(SparkDataType):
    name: str = "ArrayType"
    element_type: SparkDataType = SparkDataType("StringType")


@dataclass(frozen=True)
class SparkMapType(SparkDataType):
    name: str = "MapType"
    key_type: SparkDataType = SparkDataType("StringType")
    value_type: SparkDataType = SparkDataType("StringType")


@dataclass(frozen=True)
class SparkField:
    """One field of a struct: a ``pyspark.sql.types.StructField`` without pyspark."""

    name: str
    data_type: SparkDataType
    nullable: bool = True
    metadata: Dict[str, str] = field(default_factory=dict)


class SparkExporter(Exporter):
    """
    Exporter class for exporting data contracts to Spark schemas.
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
        Export the given data contract to Spark schemas.

        Args:
            data_contract (OpenDataContractStandard): The data contract specification.
            schema_name: The name of the schema to export, or 'all' for all schemas.
            server: Not used in this implementation.
            sql_server_type: Not used in this implementation.
            export_args: Additional arguments for export.

        Returns:
            str: A string representation of the Spark schema for each model.
        """
        return to_spark(data_contract)


def to_spark(contract: OpenDataContractStandard) -> str:
    """
    Converts an OpenDataContractStandard into a Spark schema string.

    Args:
        contract (OpenDataContractStandard): The data contract specification.

    Returns:
        str: A string representation of the Spark schema for each model in the contract.
    """
    result = []
    if contract.schema_:
        for schema_obj in contract.schema_:
            result.append(f"{schema_obj.name} = {print_schema(to_spark_schema(schema_obj))}")
    return "\n\n".join(result)


def to_spark_dict(contract: OpenDataContractStandard) -> "dict[str, types.StructType]":
    """
    Convert a data contract specification to Spark schemas.

    Args:
        contract (OpenDataContractStandard): The data contract specification.

    Returns:
        dict[str, types.StructType]: A dictionary mapping model names to their corresponding Spark schemas.
    """
    result = {}
    if contract.schema_:
        for schema_obj in contract.schema_:
            result[schema_obj.name] = to_pyspark_schema(schema_obj)
    return result


def to_pyspark_schema(schema_obj: SchemaObject) -> "types.StructType":
    """
    Convert a schema object to a `pyspark.sql.types.StructType`. Requires pyspark.

    Args:
        schema_obj (SchemaObject): The schema object to convert.

    Returns:
        types.StructType: The corresponding Spark schema.
    """
    return to_pyspark(to_spark_schema(schema_obj))


def to_spark_schema(schema_obj: SchemaObject) -> SparkStructType:
    """
    Convert a schema object to a Spark schema.

    Args:
        schema_obj (SchemaObject): The schema object to convert.

    Returns:
        SparkStructType: The corresponding Spark schema.
    """
    return to_struct_type(schema_obj.properties or [])


def to_struct_type(properties: List[SchemaProperty]) -> SparkStructType:
    """
    Convert a list of properties to a Spark StructType.

    Args:
        properties (List[SchemaProperty]): The properties to convert.

    Returns:
        SparkStructType: The corresponding Spark StructType.
    """
    return SparkStructType(fields=tuple(to_struct_field(prop) for prop in properties))


def to_pyspark(data_type: SparkDataType) -> "types.DataType":
    """
    Build the real `pyspark.sql.types` object a `SparkDataType` stands for.

    Args:
        data_type (SparkDataType): The type to build.

    Returns:
        types.DataType: The corresponding pyspark type.
    """
    from pyspark.sql import types

    if isinstance(data_type, SparkStructType):
        return types.StructType(
            [
                types.StructField(
                    name=f.name, dataType=to_pyspark(f.data_type), nullable=f.nullable, metadata=f.metadata
                )
                for f in data_type.fields
            ]
        )
    if isinstance(data_type, SparkArrayType):
        return types.ArrayType(to_pyspark(data_type.element_type))
    if isinstance(data_type, SparkMapType):
        return types.MapType(to_pyspark(data_type.key_type), to_pyspark(data_type.value_type))
    if isinstance(data_type, SparkDecimalType):
        return types.DecimalType(precision=data_type.precision, scale=data_type.scale)

    # Not every Spark type exists in every PySpark line — VariantType arrived in 4.0 —
    # and a bare AttributeError on `types` says nothing about which column caused it or
    # what to do. `datacontract export spark` renders the same type as text on any
    # version; only building the real object needs one that has it.
    spark_type = getattr(types, data_type.name, None)
    if spark_type is None:
        import pyspark

        raise RuntimeError(
            f"PySpark {pyspark.__version__} has no {data_type.name}. Upgrade PySpark to build this "
            f"schema as objects, or use `datacontract export spark`, which renders it as code "
            f"without needing the type to exist."
        )
    return spark_type()


def _get_type(prop: SchemaProperty) -> Optional[str]:
    """Get the logical type from a schema property."""
    return prop.logicalType


def _get_logical_type_option(prop: SchemaProperty, key: str):
    """Get a logical type option value."""
    if prop.logicalTypeOptions is None:
        return None
    return prop.logicalTypeOptions.get(key)


def _get_custom_property_value(prop: SchemaProperty, key: str) -> Optional[str]:
    """Get a custom property value."""
    if prop.customProperties is None:
        return None
    for cp in prop.customProperties:
        if cp.property == key:
            return cp.value
    return None


def _parse_decimal_precision_scale(physical_type: str) -> tuple[Optional[int], Optional[int]]:
    """Parse precision and scale from physicalType like 'decimal(10,2)' or 'numeric(18,4)'."""
    match = re.match(r"(?:decimal|numeric)\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)", physical_type, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


def _get_decimal_type(prop: SchemaProperty) -> SparkDecimalType:
    """Get DecimalType: first from customProperties, then parse from physicalType, else Spark defaults."""
    # First check customProperties
    precision_str = _get_custom_property_value(prop, "precision")
    scale_str = _get_custom_property_value(prop, "scale")
    if precision_str is not None or scale_str is not None:
        precision = int(precision_str) if precision_str else _DEFAULT_DECIMAL_PRECISION
        scale = int(scale_str) if scale_str else _DEFAULT_DECIMAL_SCALE
        return SparkDecimalType(precision=precision, scale=scale)

    # Fallback: parse from physicalType
    if prop.physicalType:
        precision, scale = _parse_decimal_precision_scale(prop.physicalType)
        if precision is not None:
            return SparkDecimalType(precision=precision, scale=scale if scale is not None else 0)

    # Use Spark defaults
    return SparkDecimalType()


def _logical_type_to_spark_type(logical_type: str) -> SparkDataType:
    """Convert a logical type string to a Spark DataType."""
    if logical_type is None:
        return SparkDataType("StringType")
    lt = logical_type.lower()
    if lt == "string":
        return SparkDataType("StringType")
    if lt == "integer":
        return SparkDataType("LongType")
    if lt == "number":
        return SparkDataType("DoubleType")
    if lt == "boolean":
        return SparkDataType("BooleanType")
    if lt == "date":
        return SparkDataType("DateType")
    if lt == "timestamp":
        return SparkDataType("TimestampType")
    if lt == "object":
        return SparkStructType()
    return SparkDataType("StringType")


def to_struct_field(prop: SchemaProperty) -> SparkField:
    """
    Convert a property to a Spark StructField.

    Args:
        prop (SchemaProperty): The property to convert.

    Returns:
        SparkField: The corresponding Spark StructField.
    """
    data_type = to_spark_data_type(prop)
    metadata = to_spark_metadata(prop)
    return SparkField(name=prop.name, data_type=data_type, nullable=not prop.required, metadata=metadata)


def to_spark_data_type(prop: SchemaProperty) -> SparkDataType:
    """
    Convert a property to a Spark DataType.

    Args:
        prop (SchemaProperty): The property to convert.

    Returns:
        SparkDataType: The corresponding Spark DataType.
    """
    logical_type = _get_type(prop)
    physical_type = prop.physicalType.lower() if prop.physicalType else None

    # Check for null type
    if logical_type is None and physical_type is None:
        return SparkDataType("NullType")
    if physical_type == "null":
        return SparkDataType("NullType")

    # Handle array type
    if logical_type == "array":
        if prop.items:
            return SparkArrayType(element_type=to_spark_data_type(prop.items))
        return SparkArrayType(element_type=SparkDataType("StringType"))

    # Handle map type - MUST be before object/struct check
    if is_map(prop):
        key = get_map_key(prop)
        value = get_map_value(prop)
        return SparkMapType(
            key_type=to_spark_data_type(key) if key is not None else SparkDataType("StringType"),
            value_type=to_spark_data_type(value) if value is not None else SparkDataType("StringType"),
        )

    # Handle object/struct type
    if logical_type == "object" or physical_type in ["object", "record", "struct"]:
        if prop.properties:
            return to_struct_type(prop.properties)
        return SparkStructType()

    # Handle variant type
    if physical_type == "variant":
        return SparkDataType("VariantType")

    # Check physical type first for specific SQL types
    if physical_type:
        if physical_type in ["string", "varchar", "text", "char", "nvarchar"]:
            return SparkDataType("StringType")
        if physical_type in ["decimal", "numeric"] or physical_type.startswith(("decimal(", "numeric(")):
            return _get_decimal_type(prop)
        if physical_type in ["integer", "int", "int32"]:
            return SparkDataType("IntegerType")
        if physical_type in ["long", "bigint", "int64"]:
            return SparkDataType("LongType")
        if physical_type in ["float", "real", "float32"]:
            return SparkDataType("FloatType")
        if physical_type in ["double", "float64"]:
            return SparkDataType("DoubleType")
        if physical_type in ["boolean", "bool"]:
            return SparkDataType("BooleanType")
        if physical_type in ["timestamp", "timestamp_tz"]:
            return SparkDataType("TimestampType")
        if physical_type == "timestamp_ntz":
            return SparkDataType("TimestampNTZType")
        if physical_type == "date":
            return SparkDataType("DateType")
        if physical_type in ["bytes", "binary", "bytea"]:
            return SparkDataType("BinaryType")

    # Fall back to logical type
    match logical_type:
        case "string":
            return SparkDataType("StringType")
        case "number":
            return _get_decimal_type(prop)
        case "integer":
            return SparkDataType("LongType")
        case "boolean":
            return SparkDataType("BooleanType")
        case "date":
            return SparkDataType("DateType")
        case "timestamp":
            return SparkDataType("TimestampType")
        case _:
            return SparkDataType("StringType")  # default if no condition is met


def to_spark_metadata(prop: SchemaProperty) -> dict[str, str]:
    """
    Convert a property to a Spark metadata dictionary.

    Args:
        prop (SchemaProperty): The property to convert.

    Returns:
        dict: dictionary that can be supplied to Spark as metadata for a StructField
    """
    metadata = {}
    if prop.description:
        metadata["comment"] = prop.description

    return metadata


def print_schema(dtype: SparkDataType) -> str:
    """
    Converts a Spark schema to its equivalent PySpark code representation.

    Args:
        dtype (SparkDataType): The schema to be converted.

    Returns:
        str: The code representation of the PySpark DataType schema.
    """

    def indent(text: str, level: int) -> str:
        """
        Indents each line of the given text by a specified number of levels.

        Args:
            text (str): The text to be indented.
            level (int): The number of indentation levels.

        Returns:
            str: The indented text.
        """
        return "\n".join([f"{'    ' * level}{line}" if line else "" for line in text.split("\n")])

    def repr_column(column: SparkField) -> str:
        """
        Converts a Spark field to its StructField code representation.

        Args:
            column (SparkField): The field to be converted.

        Returns:
            str: The code representation of the StructField.
        """
        name = f'"{column.name}"'
        data_type = indent(print_schema(column.data_type), 1)
        nullable = indent(f"{column.nullable}", 1)
        if column.metadata:
            metadata = indent(f"{json.dumps(column.metadata)}", 1)
            return f"StructField({name},\n{data_type},\n{nullable},\n{metadata}\n)"
        else:
            return f"StructField({name},\n{data_type},\n{nullable}\n)"

    def format_struct_type(struct_type: SparkStructType) -> str:
        """
        Converts a Spark struct to its StructType code representation.

        Args:
            struct_type (SparkStructType): The struct to be converted.

        Returns:
            str: The code representation of the StructType.
        """
        if not struct_type.fields:
            return "StructType([\n\n])"
        fields = ",\n".join([indent(repr_column(f), 1) for f in struct_type.fields])
        return f"StructType([\n{fields}\n])"

    if isinstance(dtype, SparkStructType):
        return format_struct_type(dtype)
    elif isinstance(dtype, SparkArrayType):
        return f"ArrayType({print_schema(dtype.element_type)})"
    elif isinstance(dtype, SparkMapType):
        return f"MapType(\n{indent(print_schema(dtype.key_type), 1)}, {print_schema(dtype.value_type)})"
    elif isinstance(dtype, SparkDecimalType):
        return f"DecimalType({dtype.precision}, {dtype.scale})"
    else:
        return f"{dtype.name}()"
