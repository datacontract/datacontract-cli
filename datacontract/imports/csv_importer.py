import os

import clevercsv

from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import DataContractSpecification, Example, Field, Model, Server


class CsvImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        return import_csv(data_contract_specification, self.import_format, source)


def import_csv(data_contract_specification: DataContractSpecification, format: str, source: str):
    include_example = False

    # detect encoding and dialect
    encoding = clevercsv.encoding.get_encoding(source)
    with open(source, "r", newline="") as fp:
        dialect = clevercsv.Sniffer().sniff(fp.read(10000))

    # using auto detecting of the format and encoding
    df = clevercsv.read_dataframe(source)

    if data_contract_specification.models is None:
        data_contract_specification.models = {}

    # use the file name as table name
    table_name = os.path.splitext(os.path.basename(source))[0]

    if data_contract_specification.servers is None:
        data_contract_specification.servers = {}

    data_contract_specification.servers["production"] = Server(
        type="local", path=source, format="csv", delimiter=dialect.delimiter
    )

    fields = {}
    for column, dtype in df.dtypes.items():
        field = Field()
        field.type = map_type_from_pandas(dtype.name)
        fields[column] = field

    data_contract_specification.models[table_name] = Model(
        type="table",
        description=f"Csv file with encoding {encoding}",
        fields=fields,
    )

    # multiline data is not correctly handled by yaml dump
    if include_example:
        if data_contract_specification.examples is None:
            data_contract_specification.examples = []

        # read first 10 lines with the detected encoding
        with open(source, "r", encoding=encoding) as csvfile:
            lines = csvfile.readlines()[:10]

        data_contract_specification.examples.append(Example(type="csv", model=table_name, data="".join(lines)))

    return data_contract_specification


def map_type_from_pandas(sql_type: str):
    if sql_type is None:
        return None

    sql_type_normed = sql_type.lower().strip()

    if sql_type_normed == "object":
        return "string"
    elif sql_type_normed.startswith("str"):
        return "string"
    elif sql_type_normed.startswith("int"):
        return "integer"
    elif sql_type_normed.startswith("float"):
        return "float"
    elif sql_type_normed.startswith("bool"):
        return "boolean"
    elif sql_type_normed.startswith("timestamp"):
        return "timestamp"
    elif sql_type_normed == "datetime64":
        return "date"
    elif sql_type_normed == "timedelta[ns]":
        return "timestamp_ntz"
    else:
        return "variant"
