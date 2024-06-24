import boto3
from typing import List

from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import (
    DataContractSpecification,
    Model,
    Field,
    Server,
)


class GlueImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> dict:
        return import_glue(data_contract_specification, source, import_args.get("glue_tables"))


def get_glue_database(database_name: str):
    """Get the details Glue database.

    Args:
        database_name (str): glue database to request.

    Returns:
        set: catalogid and locationUri
    """
    glue = boto3.client("glue")
    try:
        response = glue.get_database(Name=database_name)
    except glue.exceptions.EntityNotFoundException:
        print(f"Database not found {database_name}.")
        return (None, None)
    except Exception as e:
        # todo catch all
        print(f"Error: {e}")
        return (None, None)

    return (
        response["Database"]["CatalogId"],
        response["Database"].get("LocationUri", "None"),
    )


def get_glue_tables(database_name: str) -> List[str]:
    """Get the list of tables in a Glue database.

    Args:
        database_name (str): Glue database to request.

    Returns:
        List[str]: List of table names
    """
    glue = boto3.client("glue")

    # Set the paginator
    paginator = glue.get_paginator("get_tables")

    # Initialize an empty list to store the table names
    table_names = []
    try:
        # Paginate through the tables
        for page in paginator.paginate(DatabaseName=database_name, PaginationConfig={"PageSize": 100}):
            # Add the tables from the current page to the list
            table_names.extend([table["Name"] for table in page["TableList"] if "Name" in table])
    except glue.exceptions.EntityNotFoundException:
        print(f"Database {database_name} not found.")
        return []
    except Exception as e:
        # todo catch all
        print(f"Error: {e}")
        return []

    return table_names


def get_glue_table_schema(database_name: str, table_name: str):
    """Get the schema of a Glue table.

    Args:
        database_name (str): Glue database name.
        table_name (str): Glue table name.

    Returns:
        dict: Table schema
    """

    glue = boto3.client("glue")

    # Get the table schema
    try:
        response = glue.get_table(DatabaseName=database_name, Name=table_name)
    except glue.exceptions.EntityNotFoundException:
        print(f"Table {table_name} not found in database {database_name}.")
        return {}
    except Exception as e:
        # todo catch all
        print(f"Error: {e}")
        return {}

    table_schema = response["Table"]["StorageDescriptor"]["Columns"]

    # when using hive partition keys, the schema is stored in the PartitionKeys field
    if response["Table"].get("PartitionKeys") is not None:
        for pk in response["Table"]["PartitionKeys"]:
            table_schema.append(
                {
                    "Name": pk["Name"],
                    "Type": pk["Type"],
                    "Hive": True,
                    "Comment": "Partition Key",
                }
            )

    return table_schema


def import_glue(
    data_contract_specification: DataContractSpecification,
    source: str,
    table_names: List[str],
):
    """Import the schema of a Glue database.

    Args:
        data_contract_specification (DataContractSpecification): The data contract specification to update.
        source (str): The name of the Glue database.
        table_names (List[str]): List of table names to import. If None, all tables in the database are imported.

    Returns:
        DataContractSpecification: The updated data contract specification.
    """
    catalogid, location_uri = get_glue_database(source)

    # something went wrong
    if catalogid is None:
        return data_contract_specification

    if table_names is None:
        table_names = get_glue_tables(source)

    data_contract_specification.servers = {
        "production": Server(type="glue", account=catalogid, database=source, location=location_uri),
    }

    for table_name in table_names:
        if data_contract_specification.models is None:
            data_contract_specification.models = {}

        table_schema = get_glue_table_schema(source, table_name)

        fields = {}
        for column in table_schema:
            field = create_typed_field(column["Type"])

            # hive partitons are required, but are not primary keys
            if column.get("Hive"):
                field.required = True

            field.description = column.get("Comment")
            fields[column["Name"]] = field

            if "decimal" in column["Type"]:
                # Extract precision and scale from the string
                perc_scale = column["Type"][8:-1].split(",")
                field.precision = int(perc_scale[0])
                field.scale = int(perc_scale[1])

        data_contract_specification.models[table_name] = Model(
            type="table",
            fields=fields,
        )

    return data_contract_specification


def create_typed_field(dtype: str) -> Field:
    """Create a typed field based on the given data type.

    Args:
        dtype (str): The data type of the field.

    Returns:
        Field: The created field with the appropriate type.
    """
    field = Field()
    dtype = dtype.strip().lower().replace(" ", "")
    if dtype.startswith(("array", "struct")):
        orig_dtype: str = dtype
        if dtype.startswith("array"):
            field.type = "array"
            field.items = create_typed_field(orig_dtype[6:-1])
        elif dtype.startswith("struct"):
            field.type = "struct"
            for f in split_struct(orig_dtype[7:-1]):
                field.fields[f.split(":", 1)[0].strip()] = create_typed_field(f.split(":", 1)[1])
    else:
        field.type = map_type_from_sql(dtype)
    return field


def split_fields(s: str):
    """Split a string of fields considering nested structures.

    Args:
        s (str): The string to split.

    Yields:
        str: The next field in the string.
    """
    counter: int = 0
    last: int = 0
    for i, x in enumerate(s):
        if x in ("<", "("):
            counter += 1
        elif x in (">", ")"):
            counter -= 1
        elif x == "," and counter == 0:
            yield s[last:i]
            last = i + 1
    yield s[last:]


def split_struct(s: str) -> List[str]:
    """Split a struct string into individual fields.

    Args:
        s (str): The struct string to split.

    Returns:
        List[str]: List of individual fields in the struct.
    """
    return list(split_fields(s=s))


def map_type_from_sql(sql_type: str) -> str:
    """Map an SQL type to a corresponding field type.

    Args:
        sql_type (str): The SQL type to map.

    Returns:
        str: The corresponding field type.
    """
    if sql_type is None:
        return None

    sql_type = sql_type.lower()
    if sql_type.startswith("varchar"):
        return "varchar"
    if sql_type.startswith("string"):
        return "string"
    if sql_type.startswith("text"):
        return "text"
    if sql_type.startswith("byte"):
        return "byte"
    if sql_type.startswith("short"):
        return "short"
    if sql_type.startswith("integer") or sql_type.startswith("int"):
        return "integer"
    if sql_type.startswith("long") or sql_type.startswith("bigint"):
        return "long"
    if sql_type.startswith("float"):
        return "float"
    if sql_type.startswith("double"):
        return "double"
    if sql_type.startswith("boolean"):
        return "boolean"
    if sql_type.startswith("timestamp"):
        return "timestamp"
    if sql_type.startswith("date"):
        return "date"
    if sql_type.startswith("decimal"):
        return "decimal"
    return "variant"
