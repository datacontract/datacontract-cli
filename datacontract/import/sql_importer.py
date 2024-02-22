from simple_ddl_parser import parse_from_file

from datacontract.model.data_contract_specification import \
    DataContractSpecification


def import_sql(format: str, sql_file:str) -> DataContractSpecification:

    ddl = parse_from_file(sql_file)

    print(ddl)

    return DataContractSpecification()
