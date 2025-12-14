import re
from typing import Dict, Generator, List

import boto3
from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
    create_server,
)


class GlueImporter(Importer):
    def import_source(
        self, source: str, import_args: dict
    ) -> OpenDataContractStandard:
        return import_glue(source, import_args.get("glue_table"))


def get_glue_database(database_name: str):
    """Get the details Glue database."""
    glue = boto3.client("glue")
    try:
        response = glue.get_database(Name=database_name)
    except glue.exceptions.EntityNotFoundException:
        print(f"Database not found {database_name}.")
        return (None, None)
    except Exception as e:
        print(f"Error: {e}")
        return (None, None)

    return (
        response["Database"]["CatalogId"],
        response["Database"].get("LocationUri"),
    )


def get_glue_tables(database_name: str) -> List[str]:
    """Get the list of tables in a Glue database."""
    glue = boto3.client("glue")
    paginator = glue.get_paginator("get_tables")
    table_names = []

    try:
        for page in paginator.paginate(DatabaseName=database_name, PaginationConfig={"PageSize": 100}):
            table_names.extend([table["Name"] for table in page["TableList"] if "Name" in table])
    except glue.exceptions.EntityNotFoundException:
        print(f"Database {database_name} not found.")
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []

    return table_names


def get_glue_table_schema(database_name: str, table_name: str) -> List[Dict]:
    """Get the schema of a Glue table."""
    glue = boto3.client("glue")

    try:
        response = glue.get_table(DatabaseName=database_name, Name=table_name)
    except glue.exceptions.EntityNotFoundException:
        print(f"Table {table_name} not found in database {database_name}.")
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []

    table_schema = response["Table"]["StorageDescriptor"]["Columns"]

    if response["Table"].get("PartitionKeys") is not None:
        for pk in response["Table"]["PartitionKeys"]:
            table_schema.append(
                {
                    "Name": pk["Name"],
                    "Type": pk["Type"],
                    "Hive": True,
                    "Comment": pk.get("Comment"),
                }
            )
    return table_schema


def import_glue(
    source: str,
    table_names: List[str],
) -> OpenDataContractStandard:
    """Import the schema of a Glue database."""
    catalogid, location_uri = get_glue_database(source)

    if catalogid is None:
        return create_odcs()

    if table_names is None:
        table_names = get_glue_tables(source)

    odcs = create_odcs()

    # Create server
    server = create_server(
        name="production",
        server_type="glue",
        account=catalogid,
        database=source,
        location=location_uri,
    )
    odcs.servers = [server]

    odcs.schema_ = []

    for table_name in table_names:
        table_schema = get_glue_table_schema(source, table_name)

        properties = []
        for column in table_schema:
            prop = create_typed_property(column["Name"], column["Type"])

            # Hive partitions are required
            if column.get("Hive"):
                prop.required = True

            if column.get("Comment"):
                prop.description = column.get("Comment")

            properties.append(prop)

        schema_obj = create_schema_object(
            name=table_name,
            physical_type="table",
            properties=properties,
        )

        odcs.schema_.append(schema_obj)

    return odcs


def create_typed_property(name: str, dtype: str) -> SchemaProperty:
    """Create a typed SchemaProperty based on the given data type."""
    dtype = dtype.strip().lower().replace(" ", "")

    if dtype.startswith("array"):
        inner_type = dtype[6:-1]
        items_prop = create_typed_property("items", inner_type)
        return create_property(
            name=name,
            logical_type="array",
            physical_type=dtype,
            items=items_prop,
        )
    elif dtype.startswith("struct"):
        nested_props = []
        for f in split_struct(dtype[7:-1]):
            field_name, field_type = f.split(":", 1)
            nested_props.append(create_typed_property(field_name, field_type))
        return create_property(
            name=name,
            logical_type="object",
            physical_type="struct",
            properties=nested_props,
        )
    elif dtype.startswith("map"):
        return create_property(
            name=name,
            logical_type="object",
            physical_type="map",
        )
    elif dtype.startswith("decimal"):
        precision = None
        scale = None
        decimal_match = re.match(r"decimal\((\d+),\s*(\d+)\)", dtype)
        if decimal_match:
            precision = int(decimal_match.group(1))
            scale = int(decimal_match.group(2))
        return create_property(
            name=name,
            logical_type="number",
            physical_type="decimal",
            precision=precision,
            scale=scale,
        )
    elif dtype.startswith("varchar"):
        max_length = None
        if len(dtype) > 7:
            max_length = int(dtype[8:-1])
        return create_property(
            name=name,
            logical_type="string",
            physical_type="varchar",
            max_length=max_length,
        )
    else:
        logical_type = map_glue_type_to_odcs(dtype)
        return create_property(
            name=name,
            logical_type=logical_type,
            physical_type=dtype,
        )


def split_fields(s: str) -> Generator[str, None, None]:
    """Split a string of fields considering nested structures."""
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
    """Split a struct string into individual fields."""
    return list(split_fields(s=s))


def map_glue_type_to_odcs(sql_type: str) -> str:
    """Map a Glue/SQL type to ODCS logical type."""
    if sql_type is None:
        return "string"

    sql_type = sql_type.lower()

    type_mapping = {
        "string": "string",
        "int": "integer",
        "bigint": "integer",
        "float": "number",
        "double": "number",
        "boolean": "boolean",
        "timestamp": "date",
        "date": "date",
    }

    for prefix, mapped_type in type_mapping.items():
        if sql_type.startswith(prefix):
            return mapped_type

    return "string"
