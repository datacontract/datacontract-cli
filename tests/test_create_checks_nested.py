from open_data_contract_standard.model import Server

from datacontract.data_contract import DataContract
from datacontract.engines.checks.check_spec import MetricType
from datacontract.engines.checks.create_checks import create_checks

CONTRACT = """
apiVersion: v3.0.2
kind: DataContract
id: nested-checks
version: 1.0.0
status: active
schema:
  - name: orders
    properties:
      - name: id
        logicalType: string
        required: true
      - name: user
        logicalType: object
        properties:
          - name: email
            logicalType: string
            required: true
            logicalTypeOptions:
              pattern: ^.+@.+$
          - name: status
            logicalType: string
            quality:
              - type: sql
                query: SELECT COUNT(*) FROM {model} WHERE {field} NOT IN ('active', 'inactive')
                mustBe: 0
          - name: emails
            logicalType: array
            items:
              logicalType: object
              properties:
                - name: address
                  logicalType: string
                  required: true
      - name: line_items
        logicalType: array
        items:
          logicalType: object
          properties:
            - name: sku
              logicalType: string
              required: true
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
                        required: true
"""


def _checks(server_type: str):
    odcs = DataContract(data_contract_str=CONTRACT).get_data_contract()
    return create_checks(odcs, Server(type=server_type))


def test_create_checks_recurses_for_dataframe_nested_structs_and_arrays():
    checks = _checks("dataframe")

    assert any(c.field == "user.email" and c.type == "field_required" and c.model == "orders" for c in checks)
    assert any(c.field == "user.email" and c.type == "field_regex" and c.model == "orders" for c in checks)
    assert any(c.field == "line_items[].sku" and c.type == "field_required" and c.model == "orders" for c in checks)

    nested_sql = next(c for c in checks if c.type == "field_quality_sql")
    assert nested_sql.field == "user.status"
    assert nested_sql.model == "orders"
    assert nested_sql.metric == MetricType.CUSTOM_SQL
    assert "user.status" in (nested_sql.query or "")


def test_create_checks_skips_nested_checks_for_unverified_backends():
    checks = _checks("postgres")

    assert not any(c.field == "user.email" for c in checks)
    assert not any(c.field == "line_items[].sku" for c in checks)


def test_create_checks_marks_array_hops_in_the_field_path():
    checks = _checks("dataframe")

    assert any(
        c.model == "orders" and c.field == "user.emails[].address" and c.type == "field_required" for c in checks
    )
    assert any(
        c.model == "orders" and c.field == "line_items[].product.tags[].tag_id" and c.type == "field_required"
        for c in checks
    )


PHYSICAL_TYPE_CONTRACT = """
apiVersion: v3.0.2
kind: DataContract
id: nested-physical-types
version: 1.0.0
status: active
schema:
  - name: orders
    properties:
      - name: customer
        logicalType: object
        physicalType: STRUCT
        properties:
          - name: name
            logicalType: string
            physicalType: STRING
      - name: line_items
        logicalType: array
        physicalType: ARRAY
        items:
          logicalType: object
          physicalType: STRUCT
          properties:
            - name: sku
              logicalType: string
              physicalType: STRING
"""


def test_create_checks_keeps_array_item_checks_on_the_real_model():
    odcs = DataContract(data_contract_str=PHYSICAL_TYPE_CONTRACT).get_data_contract()
    checks = create_checks(odcs, Server(type="databricks"))

    sku = next(c for c in checks if c.type == "field_physical_type" and c.field == "line_items[].sku")
    assert sku.model == "orders"

    # A struct field keeps the parent model and is addressed by its dotted path.
    name = next(c for c in checks if c.type == "field_physical_type" and c.field == "customer.name")
    assert name.model == "orders"


ARRAY_QUALITY_CONTRACT = """
apiVersion: v3.0.2
kind: DataContract
id: array-quality
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
      - name: items
        logicalType: array
        items:
          logicalType: object
          properties:
            - name: sku
              logicalType: string
              quality:
                - type: sql
                  query: SELECT COUNT(*) FROM {model} WHERE {field} IS NULL
                  mustBe: 0
"""


def test_a_quality_query_on_an_array_item_warns_instead_of_emitting_unparseable_sql():
    odcs = DataContract(data_contract_str=ARRAY_QUALITY_CONTRACT).get_data_contract()
    checks = {c.field: c for c in create_checks(odcs, Server(type="databricks")) if c.type == "field_quality_sql"}

    # a struct path is a legal column reference, so it still becomes a real query
    assert checks["customer.email"].metric != MetricType.UNSUPPORTED
    assert "customer.email" in checks["customer.email"].query

    # an array item is not, so the rule is reported as unsupported rather than run
    item = checks["items[].sku"]
    assert item.metric == MetricType.UNSUPPORTED
    assert item.preset_result == "warning"
    assert "items[].sku" in item.preset_reason
    assert "Declare the rule on 'items'" in item.preset_reason
