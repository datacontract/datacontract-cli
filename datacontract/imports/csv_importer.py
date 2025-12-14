import os
from typing import Dict, List

import duckdb
from open_data_contract_standard.model import OpenDataContractStandard

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
    create_server,
)


class CsvImporter(Importer):
    def import_source(
        self, source: str, import_args: dict
    ) -> OpenDataContractStandard:
        return import_csv(source)


def import_csv(
    source: str, include_examples: bool = False
) -> OpenDataContractStandard:
    """Import a CSV file and create an ODCS data contract."""
    # use the file name as table name
    table_name = os.path.splitext(os.path.basename(source))[0]

    # use duckdb to auto detect format, columns, etc.
    con = duckdb.connect(database=":memory:")
    con.sql(
        f"""CREATE VIEW "{table_name}" AS SELECT * FROM read_csv_auto('{source}', hive_partitioning=1, auto_type_candidates = ['BOOLEAN', 'INTEGER', 'BIGINT', 'DOUBLE', 'VARCHAR']);"""
    )
    dialect = con.sql(f"SELECT * FROM sniff_csv('{source}', sample_size = 1000);").fetchnumpy()
    tbl = con.table(table_name)

    odcs = create_odcs()

    delimiter = None if dialect is None else dialect["Delimiter"][0]

    if dialect is not None:
        dc_types = [map_type_from_duckdb(x["type"]) for x in dialect["Columns"][0]]
    else:
        dc_types = [map_type_from_duckdb(str(x)) for x in tbl.dtypes]

    # Add server
    odcs.servers = [
        create_server(
            name="production",
            server_type="local",
            path=source,
            format="csv",
        )
    ]
    # Set delimiter as custom property on server if needed
    if delimiter:
        from open_data_contract_standard.model import CustomProperty
        odcs.servers[0].customProperties = [CustomProperty(property="delimiter", value=delimiter)]

    rowcount = tbl.shape[0]

    tallies = dict()
    for row in tbl.describe().fetchall():
        if row[0] not in ["count", "max", "min"]:
            continue
        for i in range(tbl.shape[1]):
            tallies[(row[0], tbl.columns[i])] = row[i + 1] if row[0] != "count" else int(row[i + 1])

    samples: Dict[str, List] = dict()
    for i in range(tbl.shape[1]):
        field_name = tbl.columns[i]
        if tallies[("count", field_name)] > 0 and tbl.dtypes[i] not in ["BOOLEAN", "BLOB"]:
            sql = f"""SELECT DISTINCT "{field_name}" FROM "{table_name}" WHERE "{field_name}" IS NOT NULL USING SAMPLE 5 ROWS;"""
            samples[field_name] = [x[0] for x in con.sql(sql).fetchall()]

    formats: Dict[str, str] = dict()
    for i in range(tbl.shape[1]):
        field_name = tbl.columns[i]
        if tallies[("count", field_name)] > 0 and tbl.dtypes[i] == "VARCHAR":
            sql = f"""SELECT
              count_if("{field_name}" IS NOT NULL) as count,
              count_if(regexp_matches("{field_name}", '^[\\w-\\.]+@([\\w-]+\\.)+[\\w-]{{2,4}}$')) as email,
              count_if(regexp_matches("{field_name}", '^[[a-z0-9]{{8}}-?[a-z0-9]{{4}}-?[a-z0-9]{{4}}-?[a-z0-9]{{4}}-?[a-z0-9]{{12}}]')) as uuid
              FROM "{table_name}";
              """
            res = con.sql(sql).fetchone()
            if res[1] == res[0]:
                formats[field_name] = "email"
            elif res[2] == res[0]:
                formats[field_name] = "uuid"

    properties = []
    for i in range(tbl.shape[1]):
        field_name = tbl.columns[i]
        dc_type = dc_types[i]

        # specifying "integer" rather than "bigint" looks nicer
        if (
            dc_type == "integer"
            and tallies[("max", field_name)] <= 2147483647
            and tallies[("min", field_name)] >= -2147483648
        ):
            dc_type = "integer"

        format_val = formats.get(field_name, None)
        required = tallies[("count", field_name)] == rowcount

        unique = None
        if dc_type not in ["boolean", "array"]:
            distinct_values = tbl.count(f'DISTINCT "{field_name}"').fetchone()[0]
            if distinct_values > 0 and distinct_values == tallies[("count", field_name)]:
                unique = True

        examples = samples.get(field_name, None)

        minimum = None
        maximum = None
        if dc_type in ["integer", "number"]:
            minimum = tallies[("min", field_name)]
            maximum = tallies[("max", field_name)]

        # Build custom properties for format if present
        custom_props = {}
        if format_val:
            custom_props["format"] = format_val

        prop = create_property(
            name=field_name,
            logical_type=dc_type,
            physical_type=str(tbl.dtypes[i]),
            required=required if required else None,
            unique=unique,
            examples=examples,
            minimum=minimum,
            maximum=maximum,
            custom_properties=custom_props if custom_props else None,
        )
        properties.append(prop)

    schema_obj = create_schema_object(
        name=table_name,
        physical_type="table",
        description="Generated model of " + source,
        properties=properties,
    )

    odcs.schema_ = [schema_obj]

    return odcs


_duck_db_types = {
    "BOOLEAN": "boolean",
    "BLOB": "array",
    "TINYINT": "integer",
    "SMALLINT": "integer",
    "INTEGER": "integer",
    "BIGINT": "integer",
    "UTINYINT": "integer",
    "USMALLINT": "integer",
    "UINTEGER": "integer",
    "UBIGINT": "integer",
    "FLOAT": "number",
    "DOUBLE": "number",
    "VARCHAR": "string",
    "TIMESTAMP": "date",
    "DATE": "date",
}


def map_type_from_duckdb(sql_type: None | str) -> str:
    """Map DuckDB type to ODCS logical type."""
    if sql_type is None:
        return "string"

    sql_type_normed = sql_type.upper().strip()
    return _duck_db_types.get(sql_type_normed, "string")
