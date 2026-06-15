import os

import pytest
from dotenv import load_dotenv
from open_data_contract_standard.model import Server

from datacontract.data_contract import DataContract
from datacontract.engines.checks.check_spec import MetricType
from datacontract.engines.checks.create_checks import create_checks

# logging.basicConfig(level=logging.DEBUG, force=True)

datacontract = "fixtures/databricks-sql/datacontract.yaml"

load_dotenv(override=True)


def test_nested_struct_sql_quality_is_enabled_for_databricks_only():
    contract = """
apiVersion: v3.0.2
kind: DataContract
id: databricks-nested
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
            quality:
              - type: sql
                query: SELECT COUNT(*) FROM {model} WHERE {field} IS NULL
                mustBe: 0
      - name: discounts
        logicalType: array
        items:
          logicalType: object
          properties:
            - name: discount_code
              logicalType: string
              required: true
"""
    odcs = DataContract(data_contract_str=contract).get_data_contract()

    checks = create_checks(odcs, Server(type="databricks"))

    nested_sql = next(c for c in checks if c.type == "field_quality_sql")
    assert nested_sql.field == "customer.email"
    assert nested_sql.metric == MetricType.CUSTOM_SQL
    assert nested_sql.model == "orders"
    assert "customer.email" in (nested_sql.query or "")
    assert not any(c.model == "orders__discounts" for c in checks)


@pytest.mark.skipif(
    os.environ.get("DATACONTRACT_DATABRICKS_TOKEN") is None, reason="Requires DATACONTRACT_DATABRICKS_TOKEN to be set"
)
def _test_test_databricks_sql():
    # os.environ['DATACONTRACT_DATABRICKS_TOKEN'] = "xxx"
    # os.environ['DATACONTRACT_DATABRICKS_HTTP_PATH'] = "/sql/1.0/warehouses/b053a326fa014fb3"
    data_contract = DataContract(data_contract_file=datacontract)

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)
