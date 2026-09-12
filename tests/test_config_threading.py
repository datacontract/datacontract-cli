"""Regression tests: the config object must actually arrive everywhere it is accepted.

The explicit-passing refactor left paths where config was accepted but not
forwarded (silently falling back to the process environment); these tests pin
the repaired paths and guard against new importers reopening the gap.
"""

import inspect

import pytest

from datacontract import Config
from datacontract.imports.importer_factory import importer_factory


def test_every_registered_importer_declares_the_config_parameter():
    """import_from_source only passes config to importers that declare it, so a
    first-party importer without the parameter silently loses credentials."""
    missing = []
    for format_name in list(importer_factory.dict_importer.keys()):
        importer = importer_factory.create(format_name)
        if "config" not in inspect.signature(importer.import_source).parameters:
            missing.append(format_name)
    assert missing == [], f"Importers silently dropping config: {missing}"


def test_definition_lookup_uses_the_passed_config(monkeypatch):
    from datacontract.lint.resolve import _build_request

    monkeypatch.delenv("ENTROPY_DATA_API_KEY", raising=False)
    monkeypatch.delenv("ENTROPY_DATA_HOST", raising=False)
    config = Config.resolve({"ENTROPY_DATA_API_KEY": "key-from-config", "ENTROPY_DATA_HOST": "https://dc.example.com"})

    url, headers, _ = _build_request("/api/definitions/orders", "definition", config)

    assert url == "https://dc.example.com/api/definitions/orders"
    assert headers["x-api-key"] == "key-from-config"


def test_s3_duckdb_setup_uses_the_passed_config(monkeypatch):
    from datacontract.engines.ibis.connections import aws_credentials, duckdb_connection

    seen = {}
    real = aws_credentials.client_kwargs

    def capture(region=None, config=None):
        seen["config"] = config
        return real(region, config)

    monkeypatch.setattr(aws_credentials, "client_kwargs", capture)
    duckdb = pytest.importorskip("duckdb")
    con = duckdb.connect()
    from open_data_contract_standard.model import Server

    config = Config.resolve({"DATACONTRACT_S3_ACCESS_KEY_ID": "AK", "DATACONTRACT_S3_SECRET_ACCESS_KEY": "SK"})
    try:
        duckdb_connection.setup_s3_connection(con, Server(server="s3", type="s3", location="s3://bucket/x"), config)
    except Exception:
        pass  # only the credential resolution is under test, not the duckdb secret

    assert seen.get("config") is config


def test_snowflake_private_key_accepts_pem():
    serialization = pytest.importorskip("cryptography.hazmat.primitives.serialization")
    from cryptography.hazmat.primitives.asymmetric import rsa

    from datacontract.engines.ibis.connections.connect import _snowflake_private_key

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    der = _snowflake_private_key(pem)

    assert isinstance(der, bytes)
    assert serialization.load_der_private_key(der, password=None) is not None


def test_snowflake_private_key_accepts_base64_der():
    import base64

    from datacontract.engines.ibis.connections.connect import _snowflake_private_key

    assert _snowflake_private_key(base64.b64encode(b"\x30\x82\x01\x00").decode()) == b"\x30\x82\x01\x00"


def test_snowflake_private_key_rejects_garbage():
    from datacontract.engines.ibis.connections.connect import _snowflake_private_key
    from datacontract.model.exceptions import DataContractException

    with pytest.raises(DataContractException, match="DATACONTRACT_SNOWFLAKE_PRIVATE_KEY"):
        _snowflake_private_key("not a key !!!")
