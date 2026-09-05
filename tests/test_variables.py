"""``${VAR}`` references in contract values (ODCS v3.2.0, RFC 0050)."""

import pytest
from open_data_contract_standard.model import CustomProperty, Server

from datacontract.config.variables import (
    UnresolvedVariableError,
    contains_variables,
    resolve_runtime_variables,
    resolve_server_variables,
    resolve_variables,
)


def test_reference_is_replaced_by_the_environment_value(monkeypatch):
    monkeypatch.setenv("DB_HOST", "db.example.com")

    assert resolve_variables("${DB_HOST}") == "db.example.com"


def test_reference_may_be_a_substring_and_appear_more_than_once(monkeypatch):
    monkeypatch.setenv("TABLE", "orders")
    monkeypatch.setenv("CUTOFF", "2024-01-01")

    query = "SELECT COUNT(*) FROM ${TABLE} WHERE created_at > '${CUTOFF}' AND t = '${TABLE}'"

    assert resolve_variables(query) == "SELECT COUNT(*) FROM orders WHERE created_at > '2024-01-01' AND t = 'orders'"


def test_default_is_used_when_the_variable_is_unset(monkeypatch):
    monkeypatch.delenv("DB_PORT", raising=False)

    assert resolve_variables("${DB_PORT:-5432}") == "5432"


def test_default_is_used_when_the_variable_is_empty(monkeypatch):
    monkeypatch.setenv("DB_PORT", "")

    assert resolve_variables("${DB_PORT:-5432}") == "5432"


def test_environment_wins_over_the_default(monkeypatch):
    monkeypatch.setenv("DB_PORT", "6543")

    assert resolve_variables("${DB_PORT:-5432}") == "6543"


def test_default_may_be_empty_or_contain_punctuation(monkeypatch):
    monkeypatch.delenv("DB_SCHEMA", raising=False)
    monkeypatch.delenv("PATH_PREFIX", raising=False)

    assert resolve_variables("${DB_SCHEMA:-}") == ""
    assert resolve_variables("${PATH_PREFIX:-s3://bucket/raw/}orders") == "s3://bucket/raw/orders"


def test_unset_variable_without_default_is_an_error_naming_the_variable(monkeypatch):
    monkeypatch.delenv("DB_HOST", raising=False)

    with pytest.raises(UnresolvedVariableError, match="DB_HOST") as e:
        resolve_variables("${DB_HOST}", source="server 'prod' host")

    assert "server 'prod' host" in str(e.value)
    assert e.value.name == "DB_HOST"


def test_empty_variable_without_default_is_an_error(monkeypatch):
    monkeypatch.setenv("DB_HOST", "")

    with pytest.raises(UnresolvedVariableError, match="DB_HOST"):
        resolve_variables("${DB_HOST}")


def test_values_without_references_pass_through_unchanged():
    assert resolve_variables("plain") == "plain"
    assert resolve_variables("$HOME and {braces}") == "$HOME and {braces}"
    assert resolve_variables(5432) == 5432
    assert resolve_variables(None) is None


def test_contains_variables():
    assert contains_variables("${X}")
    assert contains_variables("prefix-${X:-d}-suffix")
    assert not contains_variables("no reference")
    assert not contains_variables(5432)


def test_server_fields_are_resolved_into_a_copy(monkeypatch):
    monkeypatch.setenv("DB_HOST", "db.example.com")
    monkeypatch.setenv("DB_PORT", "6543")
    monkeypatch.delenv("DB_NAME", raising=False)
    monkeypatch.setenv("CUSTOM_TYPE", "trino")
    server = Server(
        server="prod",
        type="postgresql",
        host="${DB_HOST}",
        port="${DB_PORT}",
        database="${DB_NAME:-orders}",
        schema="public",
        customProperties=[CustomProperty(property="customType", value="${CUSTOM_TYPE}")],
    )

    resolved = resolve_server_variables(server)

    assert resolved.host == "db.example.com"
    assert resolved.port == 6543
    assert resolved.database == "orders"
    assert resolved.schema_ == "public"
    assert resolved.customProperties[0].value == "trino"
    # The contract's server keeps its references, so exports stay round-trip safe.
    assert server.host == "${DB_HOST}"
    assert server.port == "${DB_PORT}"
    assert server.customProperties[0].value == "${CUSTOM_TYPE}"


def test_server_without_references_is_returned_as_is():
    server = Server(server="prod", type="postgresql", host="localhost", port=5432)

    assert resolve_server_variables(server) is server


def test_unresolvable_server_field_names_the_server_and_field(monkeypatch):
    monkeypatch.delenv("DB_HOST", raising=False)
    server = Server(server="prod", type="postgresql", host="${DB_HOST}")

    with pytest.raises(UnresolvedVariableError, match="DB_HOST") as e:
        resolve_server_variables(server)

    assert "server 'prod' host" in str(e.value)


def test_runtime_resolution_covers_nested_maps_arrays_and_options(monkeypatch):
    from open_data_contract_standard.model import SchemaProperty

    monkeypatch.setenv("STATUS", "ready")
    prop = SchemaProperty.model_validate(
        {
            "name": "attributes",
            "logicalType": "map",
            "description": "Keep ${DOCUMENTATION_TOKEN} verbatim",
            "map": {
                "key": {"logicalType": "string"},
                "value": {
                    "logicalType": "array",
                    "items": {
                        "logicalType": "string",
                        "enum": [{"value": "${STATUS}"}],
                        "logicalTypeOptions": {"pattern": "^${STATUS}$"},
                    },
                },
            },
        }
    )
    resolved = resolve_runtime_variables(prop)
    assert resolved.map.value.items.enum[0].value == "ready"
    assert resolved.map.value.items.logicalTypeOptions["pattern"] == "^ready$"
    assert prop.map.value.items.enum[0].value == "${STATUS}"
    assert resolved.description == prop.description
