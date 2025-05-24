import json
from typing import Dict, Any, List, Union
from pyspark.sql import DataFrame, SparkSession, types
from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import (
    DataContractSpecification,
    Server
)


class SparkDataframeImporter(Importer):
    def import_source(
        self,
        data_contract_specification: DataContractSpecification,
        source: str,
        import_args: dict,
    ) -> DataContractSpecification:
        """
        Imports data from a Spark Dataframe into the data contract specification.

        Args:
            data_contract_specification: The data contract specification object.
            source: The table name to be used for the Spark dataframe input in the Data Contract.
            import_args: Additional arguments for the import process.

        Returns:
            dict: The updated data contract specification.
        """
        return import_spark_dataframe(
            data_contract_specification, 
            source, 
            import_args.get("df", None),
            import_args.get("source_desc", None)
        )


def import_spark_dataframe(data_contract: DataContractSpecification, source: str, 
                           df: DataFrame, source_desc: str = None) -> DataContractSpecification:
    """
    Take a Spark dataframe input, converts the spark schema to a jsonschema
    and then creates the data contract using the jsonschema as the input source

    Args:
        data_contract_specification: The data contract specification to update.
        source: table name
        df: Spark dataframe of data
        source_desc: table name description

    Returns:
        DataContractSpecification: The updated data contract specification.
    """
    spark = SparkSession.builder.getOrCreate()
    data_contract.servers["local"] = Server(type="dataframe")
    spark_schema = df.schema.json()
    sparkschema_to_jsonschema = convert_spark_schema_to_jsonschema(spark_schema, title=source, table_desc=table_desc)
    
    # Save to a temporary file Databricks can read (must be a local file, not DBFS)
    temp_json_path = f"./json_data/{table}.json"
    with open(temp_json_path, "w") as f:
        json.dump(sparkschema_to_jsonschema, f, indent=2)
    
    return data_contract.import_from_source("jsonschema", temp_json_path)
    

def convert_spark_schema_to_jsonschema(spark_schema_json: str, title: str, title_desc: str, col_desc: Union[Dict[str, str], None] = None,
                                       col_tags: Union[Dict[str, List[str]], None] = None) -> Dict[str, Any]:
    """
    Converts a Spark schema JSON string to an ODCS-compatible JSON Schema.

    Input:
        spark_schema_json (str): A JSON string representing the output of `df.schema.json()`.
        title (str): A title for the schema (usually the table name).
        title_desc (str): A human-readable description of the table for the schema.
        col_desc (Dict[str, str] or None): A dictionary of column names to descriptions.
        col_tags (Dict[str, List[str]] or None): A dictionary of column names to a list of tags.

    Output:
        Dict[str, Any]: A JSON Schema dictionary representing the full table schema.
    """
    spark_schema = json.loads(spark_schema_json)
    fields = spark_schema["fields"]

    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "title": title,
        "description": title_desc if title_desc is not None else "",
        "properties": {},
        "required": []  # Could be populated using Spark's `nullable` field if needed
    }

    for field in fields:
        col_name = field["name"]
        schema["properties"][col_name] = {
            **spark_type_to_jsonschema(field["type"]),
            "description": col_desc.get(col_name) if col_desc and col_name in col_desc else "",
            "tags": col_tags.get(col_name) if col_tags and col_name in col_tags else []
        }
    return schema


def spark_type_to_jsonschema(spark_type: types.DataType) -> Dict[str, Any]:
    """
    Converts a Spark SQL DataType into a corresponding JSON Schema fragment.

    Input:
        spark_type (types.DataType): A Spark SQL data type instance (e.g., StructType, StringType, etc.).

    Output:
        Dict[str, Any]: A JSON Schema dictionary representing the Spark type with appropriate structure,
                        nullable handling, and JSON Schema format where applicable.
    """
    base_type = _data_type_from_dataframe_schema(spark_type)

    if base_type == "struct":
        return {
            "type": ["object", "null"],
            "properties": extract_struct_properties(spark_type.fields)
        }
    elif base_type == "array":
        return {
            "type": ["array", "null"],
            "items": spark_type_to_jsonschema(spark_type.elementType)
        }
    elif base_type == "map":
        return {
            "type": ["object", "null"],
            "additionalProperties": spark_type_to_jsonschema(spark_type.valueType)
        }
    elif base_type == "timestamp":
        return {
            "type": ["string", "null"],
            "format": "date-time"
        }
    elif base_type == "timestamp_ntz":
        return {
            "type": ["string", "null"]
        }
    elif base_type == "date":
        return {
            "type": ["string", "null"],
            "format": "date"
        }
    elif base_type == "bytes":
        return {
            "type": ["string", "null"],
            "contentEncoding": "base64"
        }
    elif base_type == "decimal":
        return {
            "type": ["number", "null"]
        }
    else:
        return {
            "type": [base_type, "null"]
        }


def extract_struct_properties(fields: List[Dict[str, Any]], col_desc: Union[Dict[str, str], None] = None,
                              col_tags: Union[Dict[str, List[str]], None] = None) -> Dict[str, Any]:
    """
    Converts a list of struct fields into JSON Schema object properties.

    Input:
        fields (List[Dict[str, Any]]): A list of dicts, each representing a field within a struct.
                                       Each field has 'name' and 'type' keys.
        col_desc (dict or None): A dictionary mapping column names to descriptions. 
                                 If not provided or a column is missing, defaults to empty string.
        col_tags (dict or None): A dictionary mapping column names to a list of tags.
                                 If not provided or a column is missing, defaults to empty list.

    Output:
        Dict[str, Any]: A JSON Schema-compatible dictionary mapping field names to type definitions,
                        with the specified column-level description and tags applied.
    """
    props = {}
    for field in fields:
        col_name = field["name"]
        props[col_name] = {
            **spark_type_to_jsonschema(field["type"]),
            "description": (col_desc.get(col_name) if col_desc and col_name in col_desc else ""),
            "tags": (col_tags.get(col_name) if col_tags and col_name in col_tags else [])
        }
    return props


def _data_type_from_dataframe_schema(spark_type: types.DataType) -> str:
    """
    Maps a Spark SQL DataType to a string-based type used in the Data Contract type system.

    Input:
        spark_type (types.DataType): A Spark SQL data type instance (e.g., StringType, StructType, etc.).

    Output:
        str: A string representation of the data type used by the data contract system (e.g., "string", "struct").

    Raises:
        ValueError: If the Spark type is not recognized or supported.
    """
    if isinstance(spark_type, types.StringType):
        return "string"
    elif isinstance(spark_type, (types.IntegerType, types.ShortType)):
        return "integer"
    elif isinstance(spark_type, types.LongType):
        return "long"
    elif isinstance(spark_type, types.FloatType):
        return "float"
    elif isinstance(spark_type, types.DoubleType):
        return "double"
    elif isinstance(spark_type, types.StructType):
        return "struct"
    elif isinstance(spark_type, types.ArrayType):
        return "array"
    elif isinstance(spark_type, types.MapType):
        return "map"
    elif isinstance(spark_type, types.TimestampType):
        return "timestamp"
    elif isinstance(spark_type, types.TimestampNTZType):
        return "timestamp_ntz"
    elif isinstance(spark_type, types.DateType):
        return "date"
    elif isinstance(spark_type, types.BooleanType):
        return "boolean"
    elif isinstance(spark_type, types.BinaryType):
        return "bytes"
    elif isinstance(spark_type, types.DecimalType):
        return "decimal"
    elif isinstance(spark_type, types.NullType):
        return "null"
    elif hasattr(types, "VarcharType") and isinstance(spark_type, types.VarcharType):
        return "varchar"
    elif hasattr(types, "VariantType") and isinstance(spark_type, types.VariantType):
        return "variant"
    else:
        raise ValueError(f"Unsupported Spark type: {spark_type}")


# def spark_type_to_jsonschema(spark_type: Any) -> Dict[str, Any]:
#     """
#     Converts a Spark data type to a valid JSON Schema field block.
    
#     Input:
#         spark_type (Any): A Spark data type, typically parsed from JSON. 
#                           Can be a string (primitive) or a dict (complex types like struct or array).
                          
#     Output:
#         Dict[str, Any]: A partial JSON Schema block representing this field's type.
#     """
#     if isinstance(spark_type, str):
#         # Primitive type (e.g., "string", "integer") → lowercased with nullable option
#         return {"type": [spark_type.lower(), "null"]}

#     elif isinstance(spark_type, dict):
#         t = spark_type.get("type")

#         if t == "array":
#             # Recursive conversion for array element type
#             return {
#                 "type": ["array", "null"],
#                 "items": spark_type_to_jsonschema(spark_type["elementType"])
#             }

#         elif t == "struct":
#             # Recursive conversion for struct field list
#             return {
#                 "type": ["object", "null"],
#                 "properties": extract_struct_properties(spark_type["fields"])
#             }

#     # Fallback case if type isn't recognized
#     return {"type": ["string", "null"]}










