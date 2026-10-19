"""A posted contract resolves ${VAR} against an allow-list, not the server's environment."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from open_data_contract_standard.model import DataQuality

from datacontract.api import app
from datacontract.config.variables import (
    _ENUM_VALUES,
    CONTRACT_VARIABLES_ENV,
    InvalidVariableValueError,
    UnresolvedVariableError,
    allowed_environment,
    resolve_runtime_variables,
    resolve_variables,
)
from datacontract.engines.checks.create_checks import _METRIC_LEVELS

SECRET = "SERVER-SIDE-SECRET-xyz"

CONTRACT = """apiVersion: v3.1.0
kind: DataContract
id: urn:test:variables
version: 1.0.0
status: active
name: Variables
servers:
  - server: s
    type: postgres
    host: nonexistent.invalid
    port: 5432
    database: d
    schema: public
schema:
  - name: orders
    logicalType: object
    properties:
      - name: "{reference}"
        logicalType: string
"""


@pytest.fixture
def environment(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_SNOWFLAKE_PASSWORD", SECRET)
    monkeypatch.setenv("TABLE_COL", "order_id")
    monkeypatch.delenv(CONTRACT_VARIABLES_ENV, raising=False)
    return monkeypatch


def _post(reference: str):
    return TestClient(app).post(
        "/test",
        content=CONTRACT.format(reference=reference),
        headers={"Content-Type": "application/yaml"},
    )


# ---------------------------------------------------------------------------
# the allow-list
# ---------------------------------------------------------------------------
def test_a_posted_contract_cannot_read_the_servers_environment(environment):
    response = _post("${DATACONTRACT_SNOWFLAKE_PASSWORD}")

    assert SECRET not in response.text


def test_an_allow_listed_variable_still_resolves(environment):
    environment.setenv(CONTRACT_VARIABLES_ENV, "TABLE_*")

    response = _post("${TABLE_COL}")

    assert "order_id" in response.text


def test_a_wildcard_does_not_reach_past_its_pattern(environment):
    environment.setenv(CONTRACT_VARIABLES_ENV, "TABLE_*")

    response = _post("${DATACONTRACT_SNOWFLAKE_PASSWORD}")

    assert SECRET not in response.text


def test_a_bare_star_exposes_everything_including_credentials(environment):
    # Documented behaviour, not an oversight: the operator asked for every variable.
    environment.setenv(CONTRACT_VARIABLES_ENV, "*")

    response = _post("${DATACONTRACT_SNOWFLAKE_PASSWORD}")

    assert SECRET in response.text


def test_globs_match_names_case_sensitively(environment):
    environment.setenv("CUTOFF_DATE", "2026-01-01")

    assert allowed_environment(["*_DATE"]) == {"CUTOFF_DATE": "2026-01-01"}
    assert allowed_environment(["*_date"]) == {}
    assert allowed_environment(["CUTOFF_DATE"]) == {"CUTOFF_DATE": "2026-01-01"}
    assert allowed_environment([]) == {}


# ---------------------------------------------------------------------------
# the error message
# ---------------------------------------------------------------------------
def test_an_unlisted_variable_reads_exactly_like_an_unset_one(environment):
    # Otherwise the difference between the two enumerates the host's environment.
    with pytest.raises(UnresolvedVariableError) as unlisted:
        resolve_variables("${DATACONTRACT_SNOWFLAKE_PASSWORD}", source="schema[0]", variables={})
    with pytest.raises(UnresolvedVariableError) as unset:
        resolve_variables("${NOT_SET_ANYWHERE}", source="schema[0]", variables={})

    assert str(unlisted.value).replace("DATACONTRACT_SNOWFLAKE_PASSWORD", "NAME") == str(unset.value).replace(
        "NOT_SET_ANYWHERE", "NAME"
    )
    assert "--contract-variables" in str(unlisted.value)


def test_a_default_still_applies_under_the_allow_list():
    assert resolve_variables("${MISSING:-fallback}", variables={}) == "fallback"


def test_the_trusted_message_does_not_mention_the_api_option(monkeypatch):
    monkeypatch.delenv("DB_HOST", raising=False)

    with pytest.raises(UnresolvedVariableError) as e:
        resolve_variables("${DB_HOST}", source="server 'prod' host")

    assert "--contract-variables" not in str(e.value)
    assert ".env file" in str(e.value)


# ---------------------------------------------------------------------------
# closed enums
# ---------------------------------------------------------------------------
def test_a_reference_resolving_to_a_valid_metric_is_accepted(environment):
    environment.setenv("METRIC", "nullValues")

    resolved = resolve_runtime_variables(DataQuality(metric="${METRIC}", mustBe=0))

    assert resolved.metric == "nullValues"


def test_a_reference_resolving_to_something_else_is_rejected_without_quoting_it(environment):
    with pytest.raises(InvalidVariableValueError) as e:
        resolve_runtime_variables(DataQuality(metric="${DATACONTRACT_SNOWFLAKE_PASSWORD}", mustBe=0))

    assert SECRET not in str(e.value)
    assert "${DATACONTRACT_SNOWFLAKE_PASSWORD}" in str(e.value)
    assert "nullValues" in str(e.value)


def test_a_literal_value_is_left_to_the_schema_check(environment):
    # Literal values are the JSON Schema's job.
    assert resolve_runtime_variables(DataQuality(metric="notAMetric", mustBe=0)).metric == "notAMetric"


def test_the_metric_route_out_of_the_api_is_closed(environment):
    body = CONTRACT.format(reference="order_id").replace(
        "        logicalType: string",
        "        logicalType: string\n"
        "        quality:\n"
        "          - type: library\n"
        '            metric: "${DATACONTRACT_SNOWFLAKE_PASSWORD}"\n'
        "            mustBe: 0",
    )
    response = TestClient(app).post("/test", content=body, headers={"Content-Type": "application/yaml"})

    assert SECRET not in response.text


def test_the_enum_values_match_the_bundled_odcs_schema():
    """`_METRIC_LEVELS` is here too: lint rejects unknown ODCS metrics first, so it would drift unnoticed."""
    schema = json.loads((Path(__file__).parent.parent / "datacontract/schemas/odcs-3.2.0.schema.json").read_text())
    defs = schema["$defs"]
    in_schema = {
        ("Server", "type"): defs["Server"]["properties"]["type"]["enum"],
        ("DataQuality", "metric"): defs["DataQualityLibrary"]["properties"]["metric"]["enum"],
        ("DataQuality", "type"): defs["DataQuality"]["properties"]["type"]["enum"],
        ("DataQuality", "dimension"): defs["DataQuality"]["properties"]["dimension"]["enum"],
        ("SchemaObject", "logicalType"): defs["SchemaObject"]["properties"]["logicalType"]["enum"],
        ("SchemaProperty", "logicalType"): defs["SchemaBaseProperty"]["properties"]["logicalType"]["enum"],
    }

    assert {key: set(values) for key, values in in_schema.items()} == {
        key: set(values) for key, values in _ENUM_VALUES.items()
    }
    assert set(_METRIC_LEVELS) == set(in_schema[("DataQuality", "metric")])


def test_a_defaulted_server_type_does_not_slip_past_the_local_files_guard(environment, tmp_path):
    body = CONTRACT.format(reference="id").replace(
        """    type: postgres
    host: nonexistent.invalid
    port: 5432
    database: d
    schema: public""",
        f"""    type: "${{X:-local}}"
    format: csv
    path: {tmp_path}/data.csv""",
    )
    environment.delenv("DATACONTRACT_CLI_API_ALLOW_LOCAL_FILES", raising=False)

    response = TestClient(app).post("/test", content=body, headers={"Content-Type": "application/yaml"})

    assert response.status_code == 422
    assert "reads from the file system" in response.text
