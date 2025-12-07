import yaml

from datacontract.export.sodacl_exporter import SodaExporter
from datacontract.lint.resolve import resolve_data_contract_from_location


def test_export_sodacl():
    expected = """
checks for line_items:
  - row_count > 10:
      name: Have at lease 10 line items
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
  - row_count > 10
  - orders_servicelevel_retention < 31536000:
      name: servicelevel_retention
      orders_servicelevel_retention expression: TIMESTAMPDIFF(SECOND, MIN(processed_timestamp), CURRENT_TIMESTAMP)
  - freshness(order_timestamp) < 24h:
      name: servicelevel_freshness
"""

    data_contract = resolve_data_contract_from_location("./fixtures/sodacl/datacontract.odcs.yaml")

    exporter = SodaExporter(export_format="sodacl")
    result = exporter.export(data_contract, "all", None, "auto", None)

    assert yaml.safe_load(expected) == yaml.safe_load(result)
