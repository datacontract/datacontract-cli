"""Unit tests for how connect_ibis builds the Exasol connection.

These do not hit Exasol: ``ibis.exasol.connect`` is patched, and we only assert
which connection kwargs the dispatch passes for a given server block and set of
env vars.
"""

import ssl
import types
from unittest.mock import patch

import pytest
from open_data_contract_standard.model import Server

from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Run

EXASOL_ENV_VARS = [
    "DATACONTRACT_EXASOL_USERNAME",
    "DATACONTRACT_EXASOL_PASSWORD",
    "DATACONTRACT_EXASOL_HOST",
    "DATACONTRACT_EXASOL_PORT",
    "DATACONTRACT_EXASOL_SCHEMA",
    "DATACONTRACT_EXASOL_FINGERPRINT",
    "DATACONTRACT_EXASOL_VALIDATE_CERTIFICATE",
]


@pytest.fixture
def env(monkeypatch):
    for name in EXASOL_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DATACONTRACT_EXASOL_USERNAME", "sys")
    monkeypatch.setenv("DATACONTRACT_EXASOL_PASSWORD", "exasol")
    return monkeypatch


def _server(host="exasol.acme.com", **kwargs):
    return Server(server="exasol", type="exasol", host=host, **kwargs)


def _connect(server):
    with patch("ibis.exasol.connect") as connect:
        connect_ibis(Run.create_run(), None, server)
    return connect.call_args.kwargs


def test_server_block_is_passed_with_the_default_port(env):
    kwargs = _connect(_server(schema="SALES"))

    assert kwargs["host"] == "exasol.acme.com"
    assert kwargs["port"] == 8563
    assert kwargs["user"] == "sys"
    assert kwargs["password"] == "exasol"
    assert kwargs["schema"] == "SALES"


def test_schema_is_omitted_when_not_set(env):
    assert "schema" not in _connect(_server())


def test_env_variables_override_the_contract_server_details(env):
    env.setenv("DATACONTRACT_EXASOL_HOST", "n11..14.acme.com")
    env.setenv("DATACONTRACT_EXASOL_PORT", "8564")
    env.setenv("DATACONTRACT_EXASOL_SCHEMA", "ENV_SCHEMA")

    kwargs = _connect(_server(port=8563, schema="SALES"))

    assert kwargs["host"] == "n11..14.acme.com"
    assert kwargs["port"] == 8564
    assert kwargs["schema"] == "ENV_SCHEMA"


def test_certificates_are_verified_by_default(env):
    """ibis would default to CERT_NONE; the CLI restores pyexasol's strict default."""
    assert _connect(_server())["websocket_sslopt"] == {"cert_reqs": ssl.CERT_REQUIRED}


def test_a_fingerprint_pins_the_certificate_instead_of_the_ca_check(env):
    """pyexasol takes the fingerprint as a host suffix and verifies the server by it."""
    env.setenv("DATACONTRACT_EXASOL_FINGERPRINT", "135A1D2DCE102DE866F58267521F4232")

    kwargs = _connect(_server())

    assert kwargs["host"] == "exasol.acme.com/135A1D2DCE102DE866F58267521F4232"
    assert kwargs["websocket_sslopt"] == {"cert_reqs": ssl.CERT_NONE}


def test_certificate_validation_can_be_switched_off(env):
    env.setenv("DATACONTRACT_EXASOL_VALIDATE_CERTIFICATE", "false")

    kwargs = _connect(_server())

    assert kwargs["host"] == "exasol.acme.com/nocertcheck"
    assert kwargs["websocket_sslopt"] == {"cert_reqs": ssl.CERT_NONE}


def test_missing_username_is_rejected(env):
    env.delenv("DATACONTRACT_EXASOL_USERNAME")

    with pytest.raises(DataContractException) as exc_info:
        _connect(_server())

    assert "DATACONTRACT_EXASOL_USERNAME" in exc_info.value.reason


def test_a_geometry_column_with_an_srid_is_read_as_geometry():
    """ibis reads the parameter of GEOMETRY(4326) as a geometry subtype and fails on it."""
    from ibis.backends.sql.datatypes import ExasolType

    from datacontract.engines.ibis.connections.exasol_patch import apply_exasol_compatibility_patch

    apply_exasol_compatibility_patch(types.SimpleNamespace())

    assert ExasolType.from_string("GEOMETRY(4326)").srid == 4326
    assert ExasolType.from_string("GEOMETRY").is_geospatial()
