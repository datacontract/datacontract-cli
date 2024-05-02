import boto3
from typing import List

from datacontract.model.data_contract_specification import (
    DataContractSpecification,
    Model,
    Field,
    Server,
)


def get_glue_database(datebase_name: str):
    """Get the details Glue database.

    Args:
        database_name (str): glue database to request.

    Returns:
        set: catalogid and locationUri
    """

    glue = boto3.client("glue")
    try:
        response = glue.get_database(Name=datebase_name)
    except glue.exceptions.EntityNotFoundException:
        print(f"Database not found {datebase_name}.")
        return (None, None)
    except Exception as e:
        # todo catch all
        print(f"Error: {e}")
        return (None, None)

    return (response["Database"]["CatalogId"], response["Database"].get("LocationUri", "None"))


def get_glue_tables(database_name: str) -> List[str]:
    """Get the list of tables in a Glue database.

    Args:
        database_name (str): glue database to request.

    Returns:
        List[string]: List of table names
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


def import_glue(data_contract_specification: DataContractSpecification, source: str):
    """Import the schema of a Glue database."""

    catalogid, location_uri = get_glue_database(source)

    # something went wrong
    if catalogid is None:
        return data_contract_specification

    tables = get_glue_tables(source)

    data_contract_specification.servers = {
        "production": Server(type="glue", account=catalogid, database=source, location=location_uri),
    }

    for table_name in tables:
        if data_contract_specification.models is None:
            data_contract_specification.models = {}

        table_schema = get_glue_table_schema(source, table_name)

        fields = {}
        for column in table_schema:
            field = Field()
            field.type = map_type_from_sql(column["Type"])

            # hive partitons are required, but are not primary keys
            if column.get("Hive"):
                field.required = True

            field.description = column.get("Comment")

            fields[column["Name"]] = field

        data_contract_specification.models[table_name] = Model(
            type="table",
            fields=fields,
        )

    return data_contract_specification


def map_type_from_sql(sql_type: str):
    if sql_type is None:
        return None

    if sql_type.lower().startswith("varchar"):
        return "varchar"
    if sql_type.lower().startswith("string"):
        return "string"
    if sql_type.lower().startswith("text"):
        return "text"
    elif sql_type.lower().startswith("byte"):
        return "byte"
    elif sql_type.lower().startswith("short"):
        return "short"
    elif sql_type.lower().startswith("integer"):
        return "integer"
    elif sql_type.lower().startswith("long"):
        return "long"
    elif sql_type.lower().startswith("bigint"):
        return "long"
    elif sql_type.lower().startswith("float"):
        return "float"
    elif sql_type.lower().startswith("double"):
        return "double"
    elif sql_type.lower().startswith("boolean"):
        return "boolean"
    elif sql_type.lower().startswith("timestamp"):
        return "timestamp"
    elif sql_type.lower().startswith("date"):
        return "date"
    else:
        return "variant"
