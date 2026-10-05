from types import SimpleNamespace

import pytest
import yaml
from open_data_contract_standard.model import OpenDataContractStandard
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.export.sifflet_exporter import (
    SkipRule,
    map_schedule,
    map_severity,
    map_threshold,
    select_schemas,
    select_server,
    to_snake_case,
)

FIXTURE = "fixtures/sifflet/datacontract.yaml"
RUNNER = CliRunner()


def _quality(**kwargs):
    fields = {
        "mustBe": None,
        "mustNotBe": None,
        "mustBeGreaterThan": None,
        "mustBeGreaterOrEqualTo": None,
        "mustBeLessThan": None,
        "mustBeLessOrEqualTo": None,
        "mustBeBetween": None,
        "mustNotBeBetween": None,
        "severity": None,
        "schedule": None,
        "scheduler": None,
        "name": None,
        "description": None,
        "metric": None,
        "rule": None,
        "type": None,
        "query": None,
        "arguments": None,
        "unit": None,
    }
    fields.update(kwargs)
    return SimpleNamespace(**fields)


def _contract(schema: str, *, version: str = "v3.2.0", props: str = "", servers: str | None = None) -> str:
    server_block = (
        servers
        or "  - server: production\n    type: snowflake\n    account: xyz12345\n    database: SALES\n    schema: PUBLIC\n"
    )
    return f"""
apiVersion: {version}
kind: DataContract
id: orders-contract
version: 1.0.0
status: active
{props}
servers:
{server_block}
schema:
{schema}
"""


def _export(text: str, server: str | None = None, schema_name: str = "all"):
    result = DataContract(data_contract_str=text, server=server).export("sifflet", schema_name=schema_name)
    documents = [document for document in yaml.safe_load_all(result) if document]
    return result, documents


def _export_model(text: str, server: str | None = None, schema_name: str = "all"):
    """Load through the ODCS model without the JSON Schema one-operator rule.

    The bundled schema rejects a quality rule with no comparator, and it requires
    ``metric``. ``rule`` on its own, and a SQL rule with no operator, still reach
    the exporter when the model is built directly.
    """
    model = OpenDataContractStandard.model_validate(yaml.safe_load(text))
    result = DataContract(data_contract=model, server=server).export("sifflet", schema_name=schema_name)
    documents = [document for document in yaml.safe_load_all(result) if document]
    return result, documents


def test_to_snake_case_normalizes_camel_case_spaces_and_unicode():
    assert to_snake_case("nullValues") == "null_values"
    assert to_snake_case("Max order age") == "max_order_age"
    assert to_snake_case("allowed statuses") == "allowed_statuses"
    assert to_snake_case("café") == "caf"
    assert to_snake_case("__Row-Count__") == "row_count"


def test_threshold_operators():
    assert map_threshold(_quality(mustBe=3)) == {
        "kind": "Static",
        "min": 3,
        "max": 3,
        "isMinInclusive": True,
        "isMaxInclusive": True,
    }
    assert map_threshold(_quality(mustBeGreaterThan=1000)) == {
        "kind": "Static",
        "min": 1000,
        "isMinInclusive": False,
    }
    assert map_threshold(_quality(mustBeGreaterOrEqualTo=5)) == {
        "kind": "Static",
        "min": 5,
        "isMinInclusive": True,
    }
    assert map_threshold(_quality(mustBeLessThan=3600)) == {
        "kind": "Static",
        "max": 3600,
        "isMaxInclusive": False,
    }
    assert map_threshold(_quality(mustBeLessOrEqualTo=10)) == {
        "kind": "Static",
        "max": 10,
        "isMaxInclusive": True,
    }
    assert map_threshold(_quality(mustBeBetween=[1, 5])) == {
        "kind": "Static",
        "min": 1,
        "max": 5,
        "isMinInclusive": True,
        "isMaxInclusive": True,
    }
    assert map_threshold(_quality()) is None


def test_threshold_combines_compatible_bounds_and_rejects_conflicts():
    combined = map_threshold(_quality(mustBeGreaterThan=1000, mustBeLessThan=5000))
    assert combined == {
        "kind": "Static",
        "min": 1000,
        "isMinInclusive": False,
        "max": 5000,
        "isMaxInclusive": False,
    }
    conflicting = _quality(mustBe=3, mustBeGreaterThan=5)
    with pytest.raises(SkipRule, match="conflict"):
        map_threshold(conflicting)
    negated = _quality(mustNotBe=1)
    with pytest.raises(SkipRule, match="mustNotBe"):
        map_threshold(negated)
    one_bound = _quality(mustBeBetween=[1])
    with pytest.raises(SkipRule, match="mustBeBetween"):
        map_threshold(one_bound)


@pytest.mark.parametrize(
    ("severity", "expected"),
    [("info", "Moderate"), ("warning", "High"), ("error", "Critical"), ("INFO", "Moderate")],
)
def test_severity_maps_odcs_values(severity, expected):
    assert map_severity(_quality(severity=severity), {}, [], "orders_library_row_count") == expected


def test_severity_precedence(caplog):
    assert map_severity(_quality(severity="info"), {"sifflet.severity": "Low"}, [], "rule") == "Low"
    assert map_severity(_quality(severity="error"), {}, [{"sifflet.severity": "Low"}], "rule") == "Critical"
    assert map_severity(_quality(), {}, [{"sifflet.severity": "High"}], "implicit") == "High"
    assert map_severity(None, {}, [], "implicit") == "Moderate"
    quality = _quality()
    with pytest.raises(RuntimeError, match="Huge"):
        map_severity(quality, {"sifflet.severity": "Huge"}, [], "rule")
    map_severity(_quality(severity="fatal"), {}, [], "orders_library_row_count")
    assert "severity 'fatal'" in caplog.text


def test_schedule_resolution(caplog):
    cron = map_schedule(_quality(schedule="0 6 * * *", scheduler="cron"), {}, [{"sifflet.schedule": "@daily"}], "rule")
    assert cron == "0 6 * * *"
    assert (
        map_schedule(_quality(schedule="0 6 * * *", scheduler="Airflow"), {"sifflet.schedule": "@hourly"}, [], "rule")
        == "@hourly"
    )
    assert (
        map_schedule(_quality(schedule="0 6 * * *", scheduler="airflow"), {}, [{"sifflet.schedule": "@daily"}], "rule")
        is None
    )
    assert "scheduler 'airflow'" in caplog.text
    assert map_schedule(_quality(), {}, [{"sifflet.schedule": "@daily"}], "rule") == "@daily"
    assert map_schedule(None, {}, [], "implicit") is None
    assert map_schedule(_quality(schedule="daily"), {}, [], "rule") == "daily"
    assert "not a 5-field cron" in caplog.text


def test_rule_and_metric_build_the_same_friendly_id():
    schema = """
  - name: orders
    properties:
      - name: order_id
        logicalType: string
    quality:
      - type: library
        rule: rowCount
        mustBeGreaterThan: 1
"""
    props = "customProperties:\n  - property: sifflet.implicitMonitors\n    value: false\n"
    _, rule_docs = _export_model(_contract(schema, version="v3.0.2", props=props))
    schema = schema.replace("rule: rowCount", "metric: rowCount")
    _, metric_docs = _export(_contract(schema, version="v3.2.0", props=props))
    assert [doc["friendlyId"] for doc in rule_docs] == ["orders_library_row_count_gt_1"]
    assert [doc["friendlyId"] for doc in metric_docs] == ["orders_library_row_count_gt_1"]


def test_unnamed_library_rules_compute_the_friendly_id_from_metric_and_operator(caplog):
    schema = """
  - name: orders
    properties:
      - name: id
        logicalType: string
    quality:
      - type: library
        metric: rowCount
        name: min volume
        mustBeGreaterThan: 1
      - type: library
        metric: rowCount
        mustBeGreaterThan: 1
      - type: library
        metric: rowCount
        mustBeLessThan: 10
      - type: library
        metric: rowCount
        mustBeBetween: [1, 2.5]
      - type: library
        metric: rowCount
        mustBeGreaterThan: 1
        severity: error
"""
    props = "customProperties:\n  - property: sifflet.implicitMonitors\n    value: false\n"
    _, documents = _export(_contract(schema, props=props))
    assert [doc["friendlyId"] for doc in documents] == [
        "min_volume",
        "orders_library_row_count_gt_1",
        "orders_library_row_count_lt_10",
        "orders_library_row_count_between_1_2_5",
    ]
    assert "duplicate friendlyId" in caplog.text


def test_friendly_id_precedence_custom_property_then_id_then_name():
    schema = """
  - name: orders
    properties:
      - name: id
        logicalType: string
    quality:
      - id: orders_ignored_id
        name: ignored name
        type: library
        metric: rowCount
        mustBeLessThan: 10
        customProperties:
          - property: sifflet.friendlyId
            value: orders_pinned
      - id: orders_volume
        name: ignored name
        type: library
        metric: rowCount
        mustBeGreaterThan: 1
      - name: Max order age
        type: sql
        query: SELECT 1
        mustBeLessThan: 3600
      - id: orders_sql_without_name
        type: sql
        query: SELECT 1
        mustBe: 1
"""
    props = "customProperties:\n  - property: sifflet.implicitMonitors\n    value: false\n"
    _, documents = _export(_contract(schema, props=props))
    assert [doc["friendlyId"] for doc in documents] == [
        "orders_pinned",
        "orders_volume",
        "max_order_age",
        "orders_sql_without_name",
    ]


def test_colliding_friendly_id_override_is_an_error():
    schema = """
  - name: orders
    properties:
      - name: id
        logicalType: string
        primaryKey: true
    quality:
      - type: library
        metric: rowCount
        mustBeGreaterThan: 1
        customProperties:
          - property: sifflet.friendlyId
            value: orders_schema_change
"""
    text = _contract(schema)
    with pytest.raises(RuntimeError, match="Colliding friendlyId"):
        _export(text)


def test_library_rules_map_to_sifflet_parameters(caplog):
    schema = """
  - name: orders
    physicalName: ORDERS
    properties:
      - name: status
        physicalName: STATUS
        logicalType: string
        quality:
          - type: library
            metric: nullValues
            unit: percent
            mustBeLessThan: 5
          - type: library
            metric: missingValues
            mustBe: 0
            arguments:
              missingValues: ["", "N/A"]
          - type: library
            metric: invalidValues
            mustBe: 0
            arguments:
              validValues: [open, closed]
          - type: library
            metric: invalidValues
            name: code pattern
            arguments:
              pattern: "^[A-Z]+$"
            mustBeLessThan: 2
          - type: library
            metric: duplicateValues
            mustBe: 0
            arguments:
              properties: [status, region]
          - type: library
            metric: rowCount
            mustBeGreaterThan: 1
      - name: region
        logicalType: string
    quality:
      - type: library
        metric: duplicateValues
        mustBe: 0
        arguments:
          properties: [status, region]
      - type: library
        metric: duplicateValues
        mustBeGreaterThan: 0
      - type: library
        metric: nullValues
        mustBe: 0
"""
    props = "customProperties:\n  - property: sifflet.implicitMonitors\n    value: false\n"
    _, documents = _export(_contract(schema, props=props))
    by_id = {doc["friendlyId"]: doc["parameters"] for doc in documents}
    assert by_id["orders_status_library_null_values_lt_5"] == {
        "kind": "FieldNulls",
        "field": "STATUS",
        "valueMode": "Percentage",
        "threshold": {"kind": "Static", "max": 5, "isMaxInclusive": False},
    }
    assert by_id["orders_status_library_missing_values_eq_0"]["valueMode"] == "Count"
    assert "threshold" not in by_id["orders_status_library_invalid_values_eq_0"]
    assert by_id["orders_status_library_invalid_values_eq_0"]["values"] == ["open", "closed"]
    assert by_id["code_pattern"]["threshold"]["max"] == 2
    assert by_id["orders_status_library_duplicate_values_eq_0"]["field"] == "STATUS"
    assert "arguments.properties is ignored" in caplog.text
    assert by_id["orders_library_duplicate_values_eq_0"]["field"] == ["status", "region"]
    assert by_id["orders_library_duplicate_values_gt_0"]["kind"] == "RowDuplicates"
    assert "only NULL values are monitored" in caplog.text
    assert "metric 'rowCount' is not supported at property level" in caplog.text
    assert "metric 'nullValues' is not supported at table level" in caplog.text


def test_row_duplicates_use_a_distinct_friendly_id():
    schema = """
  - name: orders
    properties:
      - name: id
        logicalType: string
    quality:
      - type: library
        metric: duplicateValues
        name: whole row
        mustBeGreaterThan: 0
"""
    props = "customProperties:\n  - property: sifflet.implicitMonitors\n    value: false\n"
    _, documents = _export(_contract(schema, props=props))
    assert documents[0]["friendlyId"] == "whole_row"
    assert documents[0]["parameters"] == {
        "kind": "RowDuplicates",
        "threshold": {"kind": "Static", "min": 0, "isMinInclusive": False},
    }


def test_sql_rules_substitute_placeholders_and_omit_a_missing_threshold(caplog):
    schema = """
  - name: orders
    physicalName: ORDERS
    properties:
      - name: amount
        physicalName: AMOUNT
        logicalType: integer
        quality:
          - type: sql
            name: Negatives
            query: SELECT COUNT(*) FROM ${object} WHERE ${property} < 0
            mustBeLessThan: 1
          - type: sql
            name: Open rows
            query: SELECT COUNT(*) FROM '{schema}'.${table}
"""
    props = "customProperties:\n  - property: sifflet.implicitMonitors\n    value: false\n"
    _, documents = _export_model(_contract(schema, props=props))
    bounded, dynamic = documents
    assert bounded["parameters"]["kind"] == "CustomMetrics"
    assert bounded["parameters"]["sql"] == 'SELECT COUNT(*) FROM "SALES"."PUBLIC"."ORDERS" WHERE "AMOUNT" < 0'
    assert bounded["parameters"]["threshold"]["max"] == 1
    assert dynamic["parameters"]["sql"] == 'SELECT COUNT(*) FROM "PUBLIC"."ORDERS"'
    assert "threshold" not in dynamic["parameters"]
    assert "no operator given" in caplog.text
    assert "schedule" not in dynamic


@pytest.mark.parametrize(
    ("server", "expected"),
    [
        ("type: snowflake\n    database: SALES\n    schema: PUBLIC", '"SALES"."PUBLIC"."ORDERS"'),
        ("type: bigquery\n    project: acme\n    dataset: sales", "`acme`.`sales`.`ORDERS`"),
        ("type: databricks\n    catalog: main\n    schema: sales", "`main`.`sales`.`ORDERS`"),
        ("type: postgres\n    schema: public", '"public"."ORDERS"'),
        ("type: oracle\n    schema: SALES", "SALES.ORDERS"),
        ("type: local", '"ORDERS"'),
    ],
)
def test_object_placeholder_is_the_fully_qualified_table_name(server, expected):
    schema = """
  - name: orders
    physicalName: ORDERS
    properties:
      - name: id
        logicalType: string
    quality:
      - type: sql
        name: Count
        query: SELECT COUNT(*) FROM ${object}
        mustBeGreaterThan: 0
"""
    props = "customProperties:\n  - property: sifflet.implicitMonitors\n    value: false\n"
    _, documents = _export_model(_contract(schema, props=props, servers=f"  - server: production\n    {server}\n"))
    assert documents[0]["parameters"]["sql"] == f"SELECT COUNT(*) FROM {expected}"


def test_sifflet_enabled_false_skips_the_rule_and_implicit_monitors():
    schema = """
  - name: orders
    properties:
      - name: order_id
        logicalType: string
        required: true
        primaryKey: true
        quality:
          - type: library
            metric: nullValues
            mustBe: 0
            customProperties:
              - property: sifflet.enabled
                value: false
    quality:
      - type: library
        metric: rowCount
        mustBeGreaterThan: 1
"""
    disabled = "customProperties:\n  - property: sifflet.enabled\n    value: false\n"
    _, documents = _export(_contract(schema, props=disabled))
    assert documents == []

    kept = "customProperties:\n  - property: sifflet.implicitMonitors\n    value: false\n"
    _, documents = _export(_contract(schema, props=kept))
    assert [doc["friendlyId"] for doc in documents] == ["orders_library_row_count_gt_1"]
    assert documents[0]["name"] == "orders – row count > 1"


def test_custom_rules_are_ignored(caplog):
    schema = """
  - name: orders
    properties:
      - name: id
        logicalType: string
        quality:
          - type: custom
            engine: sifflet
            implementation: "{}"
          - type: text
            description: note
"""
    props = "customProperties:\n  - property: sifflet.implicitMonitors\n    value: false\n"
    caplog.set_level("DEBUG")
    text, documents = _export(_contract(schema, props=props))
    assert documents == []
    assert "type custom is not exported" in caplog.text
    assert "type text is not exported" in caplog.text
    assert text.startswith("# Generated by datacontract-cli `export sifflet`")


def test_implicit_monitors_composite_keys_and_dedup(caplog):
    schema = """
  - name: orders
    properties:
      - name: order_id
        logicalType: string
        primaryKey: true
        required: true
      - name: line_id
        logicalType: string
        primaryKey: true
      - name: email
        logicalType: string
        required: true
        logicalTypeOptions:
          format: email
          pattern: "^.+@.+$"
        quality:
          - type: library
            metric: nullValues
            mustBeLessThan: 5
      - name: code
        logicalType: string
        unique: true
        logicalTypeOptions:
          format: date
"""
    _, documents = _export(_contract(schema))
    assert documents[0]["name"] == "orders – schema change"
    assert documents[0]["description"] == "Source: data contract orders-contract v1.0.0"
    ids = [doc["friendlyId"] for doc in documents]
    assert ids == [
        "orders_schema_change",
        "orders_primary_key",
        "orders_order_id_required",
        "orders_email_format_email",
        "orders_email_format_regex",
        "orders_email_library_null_values_lt_5",
        "orders_code_unique",
    ]
    assert "orders_email_required" not in ids
    primary_key = next(doc for doc in documents if doc["friendlyId"] == "orders_primary_key")
    assert primary_key["parameters"]["field"] == ["order_id", "line_id"]
    assert "format 'date'" in caplog.text


def test_single_primary_key_and_unique_emit_one_monitor():
    schema = """
  - name: orders
    properties:
      - name: order_id
        logicalType: string
        primaryKey: true
        unique: true
"""
    _, documents = _export(_contract(schema))
    assert [doc["friendlyId"] for doc in documents if doc["friendlyId"].endswith("_unique")] == [
        "orders_order_id_unique"
    ]


def test_custom_property_precedence_and_parameter_merge(caplog):
    schema = """
  - name: orders
    physicalName: ORDERS
    customProperties:
      - property: sifflet.datasetId
        value: dataset-1
      - property: sifflet.severity
        value: High
    properties:
      - name: amount
        logicalType: integer
        quality:
          - type: library
            metric: nullValues
            mustBeLessThan: 1
            severity: error
            customProperties:
              - property: sifflet.parameters
                value:
                  whereStatement: amount > 0
                  kind: Volume
                  timeWindow:
                    unit: day
              - property: sifflet.threshold
                value:
                  kind: Dynamic
                  sensitivity: 25
                  bounds: MinAndMax
              - property: sifflet.name
                value: "[orders-contract] orders.amount – pinned"
"""
    props = """
customProperties:
  - property: sifflet.notifications
    value:
      - kind: Slack
        name: data-orders-alerts
  - property: sifflet.datasource
    value: contract-source
  - property: sifflet.implicitMonitors
    value: false
"""
    servers = """
  - server: production
    type: snowflake
    account: xyz12345
    database: SALES
    schema: PUBLIC
    customProperties:
      - property: sifflet.datasource
        value: warehouse
      - property: sifflet.datasourceId
        value: source-1
"""
    _, documents = _export(_contract(schema, props=props, servers=servers))
    document = documents[0]
    assert document["name"] == "[orders-contract] orders.amount – pinned"
    assert document["incident"]["severity"] == "Critical"
    assert document["notifications"] == [{"kind": "Slack", "name": "data-orders-alerts"}]
    assert document["datasets"] == [
        {"name": "ORDERS", "id": "dataset-1", "datasource": {"name": "warehouse", "id": "source-1"}}
    ]
    assert document["parameters"]["kind"] == "FieldNulls"
    assert document["parameters"]["whereStatement"] == "amount > 0"
    assert document["parameters"]["timeWindow"] == {"unit": "day"}
    assert document["parameters"]["threshold"] == {"kind": "Dynamic", "sensitivity": 25, "bounds": "MinAndMax"}
    assert "cannot change kind" in caplog.text


def test_server_only_reads_datasource_properties(caplog):
    schema = """
  - name: orders
    properties:
      - name: id
        logicalType: string
"""
    servers = """
  - server: production
    type: snowflake
    account: xyz12345
    database: SALES
    schema: PUBLIC
    customProperties:
      - property: sifflet.datasource
        value: warehouse
      - property: sifflet.severity
        value: High
"""
    _, documents = _export(_contract(schema, servers=servers))
    assert documents[0]["datasets"][0]["datasource"] == {"name": "warehouse"}
    assert documents[0]["incident"]["severity"] == "Moderate"
    assert "sifflet.severity is not read on a server; ignored." in caplog.text


def test_schema_name_server_and_missing_server():
    schema = """
  - name: orders
    properties:
      - name: id
        logicalType: string
  - name: lines
    properties:
      - name: id
        logicalType: string
"""
    servers = """
  - server: production
    type: snowflake
    account: xyz12345
    database: SALES
    schema: PUBLIC
  - server: staging
    type: snowflake
    account: xyz12345
    database: SALES
    schema: PUBLIC
"""
    text = _contract(schema, servers=servers)
    _, documents = _export(text, schema_name="lines")
    assert [doc["friendlyId"] for doc in documents] == ["lines_schema_change"]
    _, staging = _export(text, server="staging")
    assert staging[0]["datasets"][0]["datasource"]["name"] == "staging"
    with pytest.raises(RuntimeError, match="Available servers"):
        _export(text, server="missing")
    with pytest.raises(RuntimeError, match="Available schemas"):
        _export(text, schema_name="missing")


def test_select_helpers_reject_an_empty_contract():
    without_schema = SimpleNamespace(schema_=None)
    with pytest.raises(RuntimeError, match="requires schema"):
        select_schemas(without_schema, "all")
    without_server = SimpleNamespace(servers=[])
    with pytest.raises(RuntimeError, match="requires a server"):
        select_server(without_server, None)


def test_fixture_exports_the_example_monitors(caplog):
    text = DataContract(data_contract_file=FIXTURE).export("sifflet")
    again = DataContract(data_contract_file=FIXTURE).export("sifflet")
    assert text == again
    assert text.startswith(
        "# Generated by datacontract-cli `export sifflet` from orders-contract v1.2.0.\n"
        "# Do not edit by hand – edit the data contract and re-export.\n"
    )
    documents = list(yaml.safe_load_all(text))
    assert [doc["friendlyId"] for doc in documents] == [
        "orders_schema_change",
        "orders_library_row_count_gt_1000",
        "orders_library_row_count_lt_5000",
        "max_order_age",
        "orders_order_id_unique",
        "orders_customer_email_required",
        "orders_customer_email_format_email",
        "allowed_statuses",
    ]
    assert list(documents[0]) == [
        "kind",
        "version",
        "friendlyId",
        "name",
        "description",
        "schedule",
        "incident",
        "notifications",
        "datasets",
        "parameters",
    ]
    assert all("id" not in doc for doc in documents)
    assert documents[1]["schedule"] == "0 6 * * *"
    assert documents[1]["incident"]["severity"] == "Critical"
    assert documents[1]["name"] == "orders – row count > 1000"
    assert documents[1]["parameters"]["threshold"] == {"kind": "Static", "min": 1000, "isMinInclusive": False}
    assert documents[2]["parameters"]["threshold"] == {"kind": "Static", "max": 5000, "isMaxInclusive": False}
    sql = documents[3]
    assert sql["schedule"] == "@daily"
    assert sql["incident"] == {
        "severity": "High",
        "message": "Latest order must be less than one hour old",
    }
    assert sql["description"] == (
        "Latest order must be less than one hour old — Source: data contract orders-contract v1.2.0"
    )
    assert sql["parameters"]["sql"].endswith('FROM "SALES"."PUBLIC"."ORDERS"')
    assert documents[7]["incident"]["severity"] == "Low"
    assert "threshold" not in documents[7]["parameters"]
    assert documents[5]["parameters"] == {"kind": "FieldNulls", "field": "customer_email", "valueMode": "Count"}
    assert (
        "Rule at schema[orders].quality[3]: 'id' or 'name' is required for SQL quality rules in the Sifflet export; rule skipped."
        in caplog.text
    )


def test_cli_lists_the_shared_options_only():
    result = RUNNER.invoke(app, ["export", "sifflet", "--help"])
    assert result.exit_code == 0
    assert "--server" in result.stdout
    assert "--schema-name" in result.stdout
    assert "--output" in result.stdout
    assert "--datasource" not in result.stdout
    exported = RUNNER.invoke(app, ["export", "sifflet", FIXTURE])
    assert exported.exit_code == 0
    assert "orders_schema_change" in exported.stdout
