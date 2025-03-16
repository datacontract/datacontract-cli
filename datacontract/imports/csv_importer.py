import os
from typing import Any, Dict, List

import duckdb

from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import DataContractSpecification, Model, Server


class CsvImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        return import_csv(data_contract_specification, source)


def import_csv(
    data_contract_specification: DataContractSpecification, source: str, include_examples: bool = False
) -> DataContractSpecification:
    # use the file name as table name
    table_name = os.path.splitext(os.path.basename(source))[0]

    # use duckdb to auto detect format, columns, etc.
    con = duckdb.connect(database=":memory:")
    con.sql(
        f"""CREATE VIEW "{table_name}" AS SELECT * FROM read_csv_auto('{source}', hive_partitioning=1, auto_type_candidates = ['BOOLEAN', 'INTEGER', 'BIGINT', 'DOUBLE', 'VARCHAR']);"""
    )
    dialect = con.sql(f"SELECT * FROM sniff_csv('{source}', sample_size = 1000);").fetchnumpy()
    tbl = con.table(table_name)

    if data_contract_specification.servers is None:
        data_contract_specification.servers = {}

    delimiter = None if dialect is None else dialect['Delimiter'][0]

    if dialect is not None:
        dc_types = [map_type_from_duckdb(x["type"]) for x in dialect['Columns'][0]]
    else:
        dc_types = [map_type_from_duckdb(str(x)) for x in tbl.dtypes]

    data_contract_specification.servers["production"] = Server(
        type="local", path=source, format="csv", delimiter=delimiter
    )

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

    fields = {}
    for i in range(tbl.shape[1]):
        field_name = tbl.columns[i]
        dc_type = dc_types[i]

        ## specifying "integer" rather than "bigint" looks nicer
        if (
            dc_type == "bigint"
            and tallies[("max", field_name)] <= 2147483647
            and tallies[("min", field_name)] >= -2147483648
        ):
            dc_type = "integer"

        field: Dict[str, Any] = {"type": dc_type, "format": formats.get(field_name, None)}

        if tallies[("count", field_name)] == rowcount:
            field["required"] = True
        if dc_type not in ["boolean", "bytes"]:
            distinct_values = tbl.count(f'DISTINCT "{field_name}"').fetchone()[0]  # type: ignore
            if distinct_values > 0 and distinct_values == tallies[("count", field_name)]:
                field["unique"] = True
        s = samples.get(field_name, None)
        if s is not None:
            field["examples"] = s
        if dc_type in ["integer", "bigint", "float", "double"]:
            field["minimum"] = tallies[("min", field_name)]
            field["maximum"] = tallies[("max", field_name)]

        fields[field_name] = field

    model_examples = None
    if include_examples:
        model_examples = con.sql(f"""SELECT DISTINCT * FROM "{table_name}" USING SAMPLE 5 ROWS;""").fetchall()

    data_contract_specification.models[table_name] = Model(
        type="table", description="Generated model of " + source, fields=fields, examples=model_examples
    )

    return data_contract_specification


_duck_db_types = {
    "BOOLEAN": "boolean",
    "BLOB": "bytes",
    "TINYINT": "integer",
    "SMALLINT": "integer",
    "INTEGER": "integer",
    "BIGINT": "bigint",
    "UTINYINT": "integer",
    "USMALLINT": "integer",
    "UINTEGER": "integer",
    "UBIGINT": "bigint",
    "FLOAT": "float",
    "DOUBLE": "double",
    "VARCHAR": "string",
    "TIMESTAMP": "timestamp",
    "DATE": "date",
    # TODO: Add support for NULL
}


def map_type_from_duckdb(sql_type: None | str):
    if sql_type is None:
        return None

    sql_type_normed = sql_type.upper().strip()
    return _duck_db_types.get(sql_type_normed, "string")
