"""ODCS v3.2.0 descriptive metadata: semanticType, synonyms, deprecated, context, vendor, relationship id, SLA extras."""

import yaml

from datacontract.changelog.changelog import diff
from datacontract.changelog.normalize import normalize
from datacontract.data_contract import DataContract

FIXTURE = "fixtures/lint/valid-3.2.0.odcs.yaml"


def test_html_renders_the_metadata_fields():
    html = DataContract(data_contract_file=FIXTURE).export("html")

    # contract-level context
    assert "Use this contract for revenue analysis." in html
    assert "What was the total revenue last year?" in html
    assert "Do not expose individual order details." in html
    assert 'href="https://example.com/ontology"' in html
    # schema object: synonyms, context
    assert "Synonyms:" in html
    assert "Chiffre d&#39;affaires (fr-FR)" in html or "Chiffre d'affaires (fr-FR)" in html
    assert "Always filter by turnover_ts when querying time ranges." in html
    assert "Reference data, do not aggregate." in html
    # properties: semanticType, deprecated, synonyms
    assert ">measure<" in html and ">dimension<" in html
    assert ">deprecated<" in html
    assert ">TO<" in html
    # custom property vendor, SLA extras
    assert ">acme<" in html
    assert 'href="https://example.com/sla-policy"' in html
    assert "sla_source:contract-2024" in html


def test_rdf_writes_the_new_fields_as_literals():
    rdf = DataContract(data_contract_file=FIXTURE).export("rdf")

    assert 'semanticType "measure"' in rdf
    assert "deprecated" in rdf
    assert 'vendor "acme"' in rdf


def test_changelog_keys_the_new_lists_by_their_natural_key():
    contract = {
        "apiVersion": "v3.2.0",
        "kind": "DataContract",
        "id": "x",
        "context": {
            "instructions": "Use with care.",
            "verifiedStatements": [{"question": "Q1"}, {"id": "s2", "question": "Q2", "answer": "A2"}],
            "constraints": [{"constraint": "No PII."}, {"id": "c2", "constraint": "Aggregate."}],
        },
        "schema": [
            {
                "name": "orders",
                "synonyms": [{"synonym": "Sales"}, {"id": "syn-ca", "synonym": "Chiffre d'affaires"}],
                "context": {"constraints": [{"constraint": "Filter by date."}]},
                "relationships": [{"id": "rel-1", "from": "orders.a", "to": "b.c"}, {"from": "orders.d", "to": "e.f"}],
                "properties": [
                    {
                        "name": "status",
                        "enum": [{"value": "placed"}, {"id": "shp", "value": "shipped", "label": "Shipped"}],
                        "synonyms": [{"synonym": "state"}],
                    },
                    {
                        "name": "attributes",
                        "logicalType": "map",
                        "map": {
                            "key": {"logicalType": "string"},
                            "value": {
                                "logicalType": "object",
                                "properties": [{"name": "unit", "enum": [{"value": "EUR"}]}],
                            },
                        },
                    },
                ],
            }
        ],
        "slaProperties": [
            {
                "property": "latency",
                "value": 4,
                "customProperties": [{"property": "sla_source", "value": "contract-2024"}],
                "authoritativeDefinitions": [{"url": "https://example.com/sla-policy", "type": "policy"}],
            }
        ],
    }

    out = normalize(contract)

    assert set(out["context"]["verifiedStatements"]) == {"Q1", "s2"}
    assert set(out["context"]["constraints"]) == {"No PII.", "c2"}
    orders = out["schema"]["orders"]
    assert set(orders["synonyms"]) == {"Sales", "syn-ca"}
    assert set(orders["context"]["constraints"]) == {"Filter by date."}
    assert set(orders["relationships"]) == {"rel-1", "orders.d:e.f"}
    status = orders["properties"]["status"]
    assert set(status["enum"]) == {"placed", "shp"}
    assert set(status["synonyms"]) == {"state"}
    unit = orders["properties"]["attributes"]["map"]["value"]["properties"]["unit"]
    assert set(unit["enum"]) == {"EUR"}
    latency = out["slaProperties"]["latency"]
    assert set(latency["customProperties"]) == {"sla_source"}
    assert set(latency["authoritativeDefinitions"]) == {"https://example.com/sla-policy"}


def test_changelog_reports_a_synonym_change_by_name():
    base = """apiVersion: v3.2.0
kind: DataContract
id: orders
version: 1.0.0
status: active
schema:
  - name: orders
    synonyms:
      - synonym: Sales
      - synonym: Turnover
    properties:
      - name: status
        logicalType: string
"""
    changed = base.replace("      - synonym: Sales\n", "")

    result = str(diff(yaml.safe_load(base), yaml.safe_load(changed)))

    # the removed synonym is reported by name; the one that stayed is not touched
    assert "['synonyms']['Sales']" in result
    assert "Turnover" not in result
