"""Unit tests for Databricks CTE virtual model generation."""

from datacontract.data_contract import DataContract
from datacontract.engines.ibis.connections.databricks_nested_models import (
    build_databricks_virtual_model_queries_for_contract,
)


def test_builds_virtual_queries_for_structs_and_arrays():
    """Virtual models are generated for array items, not struct fields."""
    contract = """
apiVersion: v3.0.2
kind: DataContract
id: test-nested
version: 1.0.0
status: active
schema:
  - name: orders
    properties:
      - name: customer
        logicalType: object
        properties:
          - name: email
            logicalType: string
      - name: items
        logicalType: array
        items:
          logicalType: object
          properties:
            - name: item_id
              logicalType: string
            - name: qty
              logicalType: integer
"""
    odcs = DataContract(data_contract_str=contract).get_data_contract()

    queries = build_databricks_virtual_model_queries_for_contract(odcs)

    # Struct fields don't get virtual models; they resolve via dotted paths.
    assert "orders__customer" not in queries
    # Array items get virtual models with LATERAL VIEW OUTER explode_outer.
    assert "orders__items" in queries
    assert "LATERAL VIEW OUTER explode_outer(`items`)" in queries["orders__items"]
    assert "SELECT __dc_nested__.* FROM" in queries["orders__items"]


def test_builds_virtual_queries_for_nested_array_paths():
    contract = """
apiVersion: v3.0.2
kind: DataContract
id: test-nested
version: 1.0.0
status: active
schema:
  - name: orders
    properties:
      - name: customer
        logicalType: object
        properties:
          - name: emails
            logicalType: array
            items:
              logicalType: object
              properties:
                - name: address
                  logicalType: string
      - name: line_items
        logicalType: array
        items:
          logicalType: object
          properties:
            - name: product
              logicalType: object
              properties:
                - name: tags
                  logicalType: array
                  items:
                    logicalType: object
                    properties:
                      - name: tag_id
                        logicalType: string
"""
    odcs = DataContract(data_contract_str=contract).get_data_contract()

    queries = build_databricks_virtual_model_queries_for_contract(odcs)

    assert "orders__customer__emails" in queries
    assert "explode_outer(`customer`.`emails`)" in queries["orders__customer__emails"]

    assert "orders__line_items__product__tags" in queries
    assert "explode_outer(`product`.`tags`)" in queries["orders__line_items__product__tags"]


def test_build_virtual_queries_respects_schema_filter():
    """Only models matching the schema_name filter are included."""
    contract = """
apiVersion: v3.0.2
kind: DataContract
id: test-nested
version: 1.0.0
status: active
schema:
  - name: orders
    properties:
      - name: items
        logicalType: array
        items:
          logicalType: object
          properties:
            - name: item_id
              logicalType: string
  - name: shipments
    properties:
      - name: tracking_events
        logicalType: array
        items:
          logicalType: object
          properties:
            - name: status
              logicalType: string
"""
    odcs = DataContract(data_contract_str=contract).get_data_contract()

    # Only include "orders" schema.
    queries = build_databricks_virtual_model_queries_for_contract(odcs, schema_name="orders")

    assert "orders__items" in queries
    assert "shipments__tracking_events" not in queries
