import yaml

from datacontract.export.sodacl_converter import SodaExporter
from datacontract.model.data_contract_specification import DataContractSpecification


def test_export_sodacl():
    data_contract_specification_str = """
dataContractSpecification: 1.1.0
models:
  orders:
    description: test
    fields:
      order_id:
        type: string
        required: true
      order_timestamp:
        type: timestamp
        required: true
      processed_timestamp:
        type: timestamp
        required: true
      order_total:
        type: integer
        quality:
          - type: sql
            query: |
              SELECT quantile_cont({field}, 0.95) AS percentile_95
              FROM {model}
            mustBeBetween: [ 1000, 49900 ]
servicelevels:
  retention:
    period: P1Y
    timestampField: orders.processed_timestamp
  latency:
    threshold: 1m
    sourceTimestampField: orders.order_timestamp
    processedTimestampField: orders.processed_timestamp
  freshness:
    threshold: 24h
    timestampField: orders.order_timestamp
quality:
    type: SodaCL
    specification:
      checks for orders:
         - row_count > 10
      checks for line_items:
         - row_count > 10:
             name: Have at lease 10 line items
    """

    expected = """
checks for orders:
  - schema:
      name: orders__order_id__field_is_present
      fail:
        when required column missing:
          - order_id
  - schema:
      name: orders__order_id__field_type
      fail:
        when wrong column type:
          order_id: string
  - missing_count(order_id) = 0:
      name: orders__order_id__field_required
  - schema:
      name: orders__order_timestamp__field_is_present
      fail:
        when required column missing:
          - order_timestamp
  - schema:
      name: orders__order_timestamp__field_type
      fail:
        when wrong column type:
          order_timestamp: timestamp
  - missing_count(order_timestamp) = 0:
      name: orders__order_timestamp__field_required
  - schema:
      name: orders__processed_timestamp__field_is_present
      fail:
        when required column missing:
          - processed_timestamp
  - schema:
      name: orders__processed_timestamp__field_type
      fail:
        when wrong column type:
          processed_timestamp: timestamp
  - missing_count(processed_timestamp) = 0:
      name: orders__processed_timestamp__field_required
  - schema:
      name: orders__order_total__field_is_present
      fail:
        when required column missing:
          - order_total
  - schema:
      name: orders__order_total__field_type
      fail:
        when wrong column type:
          order_total: integer
  - orders__order_total__quality_sql_0 between 1000 and 49900:
      name: orders__order_total__quality_sql_0
      orders__order_total__quality_sql_0 query: |
        SELECT quantile_cont(order_total, 0.95) AS percentile_95
        FROM orders
  - freshness(order_timestamp) < 24h:
      name: servicelevel_freshness
  - orders_servicelevel_retention < 31536000:
      name: servicelevel_retention
      orders_servicelevel_retention expression: TIMESTAMPDIFF(SECOND, MIN(processed_timestamp), CURRENT_TIMESTAMP)
  - row_count > 10
checks for line_items:
  - row_count > 10:
      name: Have at lease 10 line items
"""

    data = yaml.safe_load(data_contract_specification_str)
    data_contract_specification = DataContractSpecification(**data)

    exporter = SodaExporter(export_format="sodacl")
    result = exporter.export(data_contract_specification, "all", None, "auto", None)

    assert yaml.safe_load(expected) == yaml.safe_load(result)
