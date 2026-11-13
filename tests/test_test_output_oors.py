import json
from pathlib import Path

import yaml
from jsonschema import Draft201909Validator, FormatChecker
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.model.run import Check, ResultEnum, Run
from datacontract.output.oors_test_results import to_oors

runner = CliRunner()

# A copy of the published OORS schema, so a version bump shows exactly what breaks.
with open(Path(__file__).parent / "fixtures/oors/oors-json-schema-v0.8.1.json", encoding="utf-8") as f:
    oors_validator = Draft201909Validator(json.load(f), format_checker=FormatChecker())


def test_output_oors_yaml_inferred_from_file_name(tmp_path):
    output = tmp_path / "results.oors.yaml"
    result = runner.invoke(app, ["test", "--output", str(output), "./fixtures/diagnostics/datacontract.yaml"])

    assert output.exists(), result.output
    document = yaml.safe_load(output.read_text())
    oors_validator.validate(document)
    assert document["apiVersion"] == "v0.8.1"
    assert document["contract"] == {
        "contractId": "diagnostics_test",
        "standard": "ODCS",
        "version": "1.0.0",
        "server": "local",
    }
    assert document["status"] == "fail"
    assert "startedAt" in document["run"]

    unique = next(r for r in document["results"] if r["id"] == "orders__order_id__field_unique")
    assert unique["status"] == "fail"
    assert unique["target"] == {"resourceType": "column", "resourceIdentifier": "orders.order_id"}
    assert unique["relatesTo"] == "schema/orders/properties/order_id"
    assert unique["measure"]["metric"] == "duplicateValues"
    assert unique["measure"]["threshold"] == {"mustBe": 0}
    assert unique["measure"]["rowCount"] > 0
    assert unique["measure"]["failedRowCount"] > 0
    assert {"property": "checkType", "value": "field_unique", "vendor": "datacontract-cli"} in unique[
        "customProperties"
    ]

    required = next(r for r in document["results"] if r["id"] == "orders__order_id__field_required")
    assert required["measure"]["metric"] == "nullValues"


def test_output_oors_json_with_output_format(tmp_path):
    output = tmp_path / "results.json"
    result = runner.invoke(
        app,
        ["test", "--output-format", "oors", "--output", str(output), "./fixtures/diagnostics/datacontract.yaml"],
    )

    assert output.exists(), result.output
    document = json.loads(output.read_text())
    oors_validator.validate(document)
    assert document["kind"] == "ObservabilityResults"
    assert len(document["results"]) > 0


def test_output_oors_lint(tmp_path):
    output = tmp_path / "results.oors.json"
    result = runner.invoke(app, ["lint", "--output", str(output), "./fixtures/lint/valid.odcs.yaml"])

    assert output.exists(), result.output
    document = json.loads(output.read_text())
    oors_validator.validate(document)
    assert document["source"]["process"] == "datacontract lint"


def test_output_oors_freshness_measures_age_in_seconds():
    run = Run.create_run()
    run.checks = [
        Check(
            type="servicelevel_freshness",
            category="servicelevel",
            result=ResultEnum.failed,
            diagnostics={
                "metric": "freshness",
                "field": "updated_at",
                "age_seconds": 259201,
                "threshold_seconds": 86400,
            },
        )
    ]
    run.finish()

    document = to_oors(run, "datacontract test")

    oors_validator.validate(document)
    assert document["results"][0]["measure"] == {
        "metric": "freshness",
        "value": 259201,
        "threshold": {"mustBeLessThan": 86400},
        "unit": "seconds",
    }
