from open_data_contract_standard.model import (
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
    ServiceLevelAgreementProperty,
)

from datacontract.engines.checks.create_checks import create_checks


def _contract(schema: SchemaObject, sla: ServiceLevelAgreementProperty):
    return OpenDataContractStandard(
        version="1",
        kind="DataContract",
        apiVersion="v3.1.0",
        id="x",
        schema=[schema],
        slaProperties=[sla],
    )


def test_freshness_check_uses_physical_name_when_set():
    schema = SchemaObject(
        name="orders",
        physicalName="RAW_ORDERS",
        properties=[SchemaProperty(name="updated_at", logicalType="date")],
    )
    sla = ServiceLevelAgreementProperty(property="freshness", element="orders.updated_at", value=60, unit="m")
    checks = create_checks(_contract(schema, sla), Server(server="s", type="bigquery"))

    check = next(c for c in checks if c.type == "servicelevel_freshness")
    assert check.model == "RAW_ORDERS"
    assert check.field == "updated_at"


def test_freshness_check_falls_back_to_name_without_physical_name():
    schema = SchemaObject(name="orders", properties=[SchemaProperty(name="updated_at", logicalType="date")])
    sla = ServiceLevelAgreementProperty(property="freshness", element="orders.updated_at", value=60, unit="m")
    checks = create_checks(_contract(schema, sla), Server(server="s", type="bigquery"))

    check = next(c for c in checks if c.type == "servicelevel_freshness")
    assert check.model == "orders"


def test_retention_check_uses_physical_name_when_set():
    schema = SchemaObject(
        name="orders",
        physicalName="RAW_ORDERS",
        properties=[SchemaProperty(name="created_at", logicalType="date")],
    )
    sla = ServiceLevelAgreementProperty(property="retention", element="orders.created_at", value=1, unit="y")
    checks = create_checks(_contract(schema, sla), Server(server="s", type="bigquery"))

    check = next(c for c in checks if c.type == "servicelevel_retention")
    assert check.model == "RAW_ORDERS"
    assert check.field == "created_at"
