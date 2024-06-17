import logging

from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.INFO, force=True)


def test_schema():
    """
    A schema in a data contract would not do anything, but should also raise no errors.
    """
    data_contract = DataContract(
        data_contract_str="""
dataContractSpecification: 0.9.2
id: urn:datacontract:checkout:orders-latest
info:
  title: Orders Latest
  version: 1.0.0
models:
  orders:
    description: One record per order. Includes cancelled and deleted orders.
    type: object
    fields:
      order_id:
        type: string
        description: Primary key of the orders table
      order_timestamp:
        type: string
        format: date-time
        description: The business timestamp in UTC when the order was successfully registered in the source system and the payment was successful.
      order_total:
        type: integer
        description: Total amount of the order in the smallest monetary unit (e.g., cents).
  line_items:
    type: object
    fields:
      lines_item_id:
        type: string
        description: Primary key of the lines_item_id table
      order_id:
        type: string
        description: Foreign key to the orders table
      sku:
        type: string
        description: The purchased article number"""
    )

    data_contract.lint()
    data_contract.test()
    data_contract.export(export_format="odcs")
    data_contract.export(export_format="dbt")
    data_contract.export(export_format="dbt-sources")
    data_contract.export(export_format="dbt-staging-sql", model="orders")
    data_contract.export(export_format="jsonschema", model="orders")
