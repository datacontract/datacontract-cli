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


def test_connect_skips_memtable_volume_creation():
    # ibis's Databricks backend runs CREATE VOLUME at connect time for memtable
    # staging; tests never use memtables and a read-only principal may not be
    # allowed to create volumes, so the connect helper must suppress it.
    from ibis.backends.databricks import Backend

    from datacontract.engines.ibis.connections.connect import _databricks_connect

    original = Backend._post_connect
    seen = {}

    class StubDatabricks:
        @staticmethod
        def connect(**kwargs):
            seen["post_connect"] = Backend._post_connect
            return "connection"

    class StubIbis:
        databricks = StubDatabricks()

    assert _databricks_connect(StubIbis(), server_hostname="example") == "connection"
    assert seen["post_connect"] is not original
    assert seen["post_connect"](object(), memtable_volume="unused") is None
    assert Backend._post_connect is original


def test_connect_applies_the_type_compatibility_patch(monkeypatch):
    # Databricks-only column types (GEOGRAPHY(4326)) break ibis's schema
    # reflection, which fails every check of the model, so the patch must be in
    # place before the first table is read.
    from datacontract.engines.ibis.connections.connect import _databricks_connect

    applied = []
    monkeypatch.setattr(
        "datacontract.engines.ibis.connections.databricks_patch.apply_databricks_compatibility_patch",
        lambda: applied.append(True),
    )

    class StubIbis:
        class databricks:
            @staticmethod
            def connect(**kwargs):
                return "connection"

    assert _databricks_connect(StubIbis(), server_hostname="example") == "connection"
    assert applied == [True]


@pytest.fixture
def databricks_type_patch():
    """Apply the Databricks type patch, restoring ibis's originals afterwards."""
    from ibis.backends import databricks as databricks_backend
    from ibis.backends.sql.datatypes import DatabricksType

    from datacontract.engines.ibis.connections.databricks_patch import apply_databricks_compatibility_patch

    geo_methods = ("_from_sqlglot_GEOGRAPHY", "_from_sqlglot_GEOMETRY")
    # not defined on DatabricksType itself, so None means "restore by removing"
    originals = {name: DatabricksType.__dict__.get(name) for name in geo_methods}
    original_schema_reader = databricks_backend._databricks_schema_to_ibis

    apply_databricks_compatibility_patch()
    try:
        yield
    finally:
        for name, method in originals.items():
            if method is None:
                delattr(DatabricksType, name)
            else:
                setattr(DatabricksType, name, method)
        databricks_backend._databricks_schema_to_ibis = original_schema_reader


def test_geospatial_type_with_srid(databricks_type_patch):
    # Databricks declares a geospatial column as GEOGRAPHY(<srid>), while ibis
    # reads the first type parameter as a geometry subtype (PostGIS's
    # GEOGRAPHY(POINT, 4326)) and fails with KeyError: '4326'.
    from ibis.backends.sql.datatypes import DatabricksType

    geography = DatabricksType.from_string("geography(4326)")
    assert geography.geotype == "geography"
    assert geography.srid == 4326

    geometry = DatabricksType.from_string("geometry(4326)")
    assert geometry.geotype == "geometry"
    assert geometry.srid == 4326


def test_geospatial_type_without_srid_and_with_subtype(databricks_type_patch):
    # The subtype spellings ibis already understood must keep working.
    import ibis.expr.datatypes as dt
    from ibis.backends.sql.datatypes import DatabricksType

    assert DatabricksType.from_string("geography").srid is None
    assert DatabricksType.from_string("geometry(point,4326)") == dt.Point(geotype="geometry", srid=4326)
    assert DatabricksType.from_string("int") == dt.int32


def test_unconvertible_column_does_not_affect_the_other_columns(databricks_type_patch):
    # One column ibis cannot represent must not fail the whole model: it becomes
    # unknown (its type checks fail), every other column keeps its real type.
    import ibis.expr.datatypes as dt
    from ibis.backends import databricks as databricks_backend

    schema = databricks_backend._databricks_schema_to_ibis(
        [
            {"name": "id", "type": {"name": "int"}, "nullable": False},
            {"name": "geo", "type": {"name": "geography(4326)"}, "nullable": True},
            {"name": "mystery", "type": {"name": "geography(OGC:CRS84)"}, "nullable": True},
        ]
    )

    assert schema["id"] == dt.Int32(nullable=False)
    assert schema["geo"].srid == 4326
    assert schema["mystery"] == dt.unknown


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
