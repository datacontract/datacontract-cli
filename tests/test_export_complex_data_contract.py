from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.INFO, force=True)


def test_export_complex_data_contract():
    """
    Use a complex data contract, and smoke test that it can be exported to various formats without exception.
    """
    data_contract = DataContract(
        data_contract_str="""
dataContractSpecification: 0.9.3
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
      status:
        type: string
        required: true
        description: order status
        enum:
            - PLACED
            - SHIPPED
            - DELIVERED
            - CANCELLED
        config:
          avroType: enum
        title: Status
      metadata:
        type: map
        required: true
        description: Additional metadata about the order
        values:
          type: object
          fields:
            value:
              type: string
              required: true
            type:
              type: string
              required: true
              enum:
              - STRING
              - LONG
              - DOUBLE
              config:
                avroType: enum
              title: MetadataType
            timestamp:
              type: long
              required: true
            source:
              type: string
              required: true
          default: {}
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
    data_contract.export(export_format="avro", model="orders")
    data_contract.export(export_format="odcs")
    data_contract.export(export_format="dbt")
    data_contract.export(export_format="dbt-sources")
    data_contract.export(export_format="dbt-staging-sql", model="orders")
    data_contract.export(export_format="jsonschema", model="orders")
