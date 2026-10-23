import os
from pathlib import Path

from typer.testing import CliRunner

from datacontract.cli import app


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "mermaid", "./fixtures/export/datacontract.odcs.yaml"])
    assert result.exit_code == 0


def test_cli_with_output(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "mermaid",
            "./fixtures/export/datacontract.odcs.yaml",
            "--output",
            tmp_path / "datacontract.mermaid",
        ],
    )
    assert result.exit_code == 0
    assert os.path.exists(tmp_path / "datacontract.mermaid")


def test_mermaid_structure(tmp_path: Path):
    datacontract_file = "fixtures/export/datacontract.odcs.yaml"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "mermaid",
            datacontract_file,
            "--output",
            tmp_path / "datacontract.mermaid",
        ],
    )
    assert result.exit_code == 0

    with open(tmp_path / "datacontract.mermaid") as file:
        content = file.read()

    # Check structure
    assert "erDiagram" in content
    assert "orders" in content
    assert "order_id" in content
    assert "order_total" in content
    assert "order_status" in content


def test_mermaid_sanitizes_html_dangerous_characters():
    """to_mermaid output is embedded `| safe` in the HTML export, so no token
    (model name, field name, or field type) may carry `<`/`>` that could break
    out of the <pre class="mermaid"> block."""
    from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty

    from datacontract.export.mermaid_exporter import to_mermaid

    contract = OpenDataContractStandard(
        apiVersion="v3.0.2",
        kind="DataContract",
        id="x",
        version="1.0.0",
        status="active",
        schema=[
            SchemaObject(
                name="orders</pre><script>alert(1)</script>",
                logicalType="object",
                properties=[
                    SchemaProperty(
                        name="id</pre><img src=x onerror=alert(1)>",
                        logicalType="string",
                        physicalType="varchar<svg onload=alert(1)>",
                    )
                ],
            )
        ],
    )

    diagram = to_mermaid(contract)

    assert diagram is not None
    assert "<" not in diagram
    assert ">" not in diagram


def test_mermaid_relationships_odcs_3_2():
    """Property-level and schema-level (composite) relationships, shorthand and id-based references."""
    from open_data_contract_standard.model import OpenDataContractStandard, Relationship, SchemaObject, SchemaProperty

    from datacontract.export.mermaid_exporter import to_mermaid

    contract = OpenDataContractStandard(
        apiVersion="v3.2.0",
        kind="DataContract",
        id="x",
        version="1.0.0",
        status="active",
        schema=[
            SchemaObject(
                id="customers_tbl",
                name="customers",
                properties=[SchemaProperty(id="cust_id", name="customer_id", logicalType="string", primaryKey=True)],
            ),
            SchemaObject(
                name="orders",
                properties=[
                    SchemaProperty(
                        name="customer_id",
                        logicalType="string",
                        relationships=[Relationship(to="schema/customers_tbl/properties/cust_id")],
                    ),
                    SchemaProperty(name="region", logicalType="string"),
                    SchemaProperty(name="site", logicalType="string"),
                ],
                relationships=[
                    Relationship(
                        type="foreignKey",
                        **{"from": ["orders.region", "orders.site"]},
                        to=["sites.region", "sites.site"],
                    )
                ],
            ),
        ],
    )

    diagram = to_mermaid(contract)

    assert diagram is not None
    assert '"**customers**" ||--o{ "**orders**" : "customer_id → customer_id"' in diagram
    assert '"**sites**" ||--o{ "**orders**" : "region, site → region, site"' in diagram
    assert "region🔗 string" in diagram
    assert "<" not in diagram and ">" not in diagram


def test_mermaid_limits_attributes_when_diagram_is_too_large(monkeypatch):
    """Above Mermaid's max text size, an entity keeps its keys and at most 5 attributes, then an ellipsis."""
    from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty

    from datacontract.export import mermaid_exporter

    properties = [SchemaProperty(name=f"col_{i}", logicalType="string") for i in range(20)]
    properties[15] = SchemaProperty(name="order_id", logicalType="string", primaryKey=True)
    properties[17] = SchemaProperty(name="email", logicalType="string", unique=True)
    contract = OpenDataContractStandard(
        apiVersion="v3.2.0",
        kind="DataContract",
        id="x",
        version="1.0.0",
        status="active",
        schema=[
            SchemaObject(name="orders", properties=properties),
            SchemaObject(name="small", properties=properties[:3]),
        ],
    )

    full = mermaid_exporter.to_mermaid(contract)
    assert "col_19" in full and "…" not in full

    monkeypatch.setattr(mermaid_exporter, "MAX_TEXT_SIZE", len(full) - 1)
    diagram = mermaid_exporter.to_mermaid(contract)

    orders = diagram.split('"**small**"')[0]
    assert orders.count(" string") == 5
    assert "order_id🔑 string" in orders and "email🆔 string" in orders
    assert "col_0 string" in orders and "col_19" not in orders
    assert orders.count("…") == 2
    # an entity with 5 attributes or fewer is untouched
    assert diagram.split('"**small**"')[1].count("…") == 0


def test_mermaid_truncates_entity_names_when_diagram_is_too_large(monkeypatch):
    from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty

    from datacontract.export import mermaid_exporter

    prefix = "a_very_long_entity_name_prefix_"  # 31 characters
    contract = OpenDataContractStandard(
        apiVersion="v3.2.0",
        kind="DataContract",
        id="x",
        version="1.0.0",
        status="active",
        schema=[
            SchemaObject(name=prefix + "one", properties=[SchemaProperty(name="id", logicalType="string")]),
            SchemaObject(name=prefix + "other", properties=[SchemaProperty(name="id", logicalType="string")]),
            SchemaObject(name="short", properties=[SchemaProperty(name="id", logicalType="string")]),
        ],
    )

    diagram, reduced = mermaid_exporter.to_mermaid_and_reduced(contract)
    assert not reduced and prefix + "one" in diagram

    monkeypatch.setattr(mermaid_exporter, "MAX_TEXT_SIZE", len(diagram) - 1)
    diagram, reduced = mermaid_exporter.to_mermaid_and_reduced(contract)

    assert reduced
    assert '"**a_very_long_entity_name_prefix_o**"' in diagram
    # a second name with the same 32 first characters stays distinct
    assert '"**a_very_long_entity_name_prefix_2**"' in diagram
    assert '"**short**"' in diagram


def test_mermaid_reduction_prioritizes_pk_then_fk_then_uk(monkeypatch):
    from open_data_contract_standard.model import (
        OpenDataContractStandard,
        Relationship,
        SchemaObject,
        SchemaProperty,
    )

    from datacontract.export import mermaid_exporter

    def prop(name, **kwargs):
        return SchemaProperty(name=name, logicalType="string", **kwargs)

    # 9 key columns, listed after 5 plain ones: only 5 fit
    properties = [prop(f"plain_{i}") for i in range(5)]
    properties += [prop(f"uk_{i}", unique=True) for i in range(4)]
    properties += [prop(f"fk_{i}", relationships=[Relationship(to="parents.id")]) for i in range(3)]
    properties += [prop(f"pk_{i}", primaryKey=True) for i in range(2)]
    contract = OpenDataContractStandard(
        apiVersion="v3.2.0",
        kind="DataContract",
        id="x",
        version="1.0.0",
        status="active",
        schema=[SchemaObject(name="orders", properties=properties)],
    )
    monkeypatch.setattr(mermaid_exporter, "MAX_TEXT_SIZE", 0)

    diagram = mermaid_exporter.to_mermaid(contract)

    kept = [line.split()[0].rstrip("🔑🆔🔗") for line in diagram.split("\n") if line.endswith(" string")]
    assert sorted(kept) == ["fk_0", "fk_1", "fk_2", "pk_0", "pk_1"]
    assert "plain_0" not in diagram and "uk_0" not in diagram


def test_mermaid_reduction_skips_relationship_labels(monkeypatch):
    from open_data_contract_standard.model import (
        OpenDataContractStandard,
        Relationship,
        SchemaObject,
        SchemaProperty,
    )

    from datacontract.export import mermaid_exporter

    contract = OpenDataContractStandard(
        apiVersion="v3.2.0",
        kind="DataContract",
        id="x",
        version="1.0.0",
        status="active",
        schema=[
            SchemaObject(name="parents", properties=[SchemaProperty(name="id", logicalType="string")]),
            SchemaObject(
                name="children",
                properties=[
                    SchemaProperty(
                        name="parent_id", logicalType="string", relationships=[Relationship(to="parents.id")]
                    )
                ],
            ),
        ],
    )

    assert '"**parents**" ||--o{ "**children**" : "parent_id → id"' in mermaid_exporter.to_mermaid(contract)

    monkeypatch.setattr(mermaid_exporter, "MAX_TEXT_SIZE", 0)
    assert '"**parents**" ||--o{ "**children**" : ""' in mermaid_exporter.to_mermaid(contract)
