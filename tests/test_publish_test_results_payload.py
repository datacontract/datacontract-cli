"""The payload the `/api/test-results` API is published with."""

from datacontract.integration.entropy_data import to_test_results_payload
from datacontract.model.run import Check, ResultEnum, Run


def _published(check: Check) -> dict:
    run = Run.create_run()
    run.dataContractId = "orders"
    run.checks = [check]
    return to_test_results_payload(run)["checks"][0]


def _counted(metric: str, **diagnostics) -> dict:
    return _published(
        Check(
            type="field_required",
            result=ResultEnum.failed,
            diagnostics={"metric": metric, **diagnostics},
        )
    )


def test_the_run_is_identified_by_id_as_well_as_run_id():
    run = Run.create_run()
    run.dataContractId = "orders"

    payload = to_test_results_payload(run)

    assert payload["id"] == str(run.runId)
    assert payload["runId"] == str(run.runId)


def test_missing_values_are_published_as_failed_rows_of_the_total():
    assert _counted("missing_count", value=3, row_count=10) == {
        "type": "field_required",
        "result": "failed",
        "failedNumber": 3,
        "totalNumber": 10,
        "diagnostics": {"metric": "missing_count", "value": 3, "row_count": 10},
    }


def test_invalid_values_are_published_as_failed_rows_of_the_total():
    counts = _counted("invalid_count", value=1, row_count=10)

    assert (counts["failedNumber"], counts["totalNumber"]) == (1, 10)


def test_duplicates_are_published_as_the_rows_they_cost_not_the_duplicated_keys():
    """`value` counts key values occurring more than once; `failed_rows` counts the rows
    those keys span, which is the unit the denominator is in."""
    counts = _counted("duplicate_count", value=2, failed_rows=5, row_count=10)

    assert (counts["failedNumber"], counts["totalNumber"]) == (5, 10)


def test_a_row_count_check_is_published_as_a_total_without_a_failed_count():
    counts = _counted("row_count", value=10)

    assert counts["totalNumber"] == 10
    assert "failedNumber" not in counts


def test_a_custom_query_result_is_not_published_as_a_row_count():
    """The value is whatever the author's query returned -- a count, a ratio, an
    age -- so it cannot be summed with other checks' row counts."""
    counts = _counted("custom_sql", value=42)

    assert "failedNumber" not in counts
    assert "totalNumber" not in counts


def test_a_check_that_measures_no_rows_publishes_no_counts():
    for metric in ("field_type", "field_present", "freshness", "retention"):
        counts = _counted(metric, value=1)

        assert "failedNumber" not in counts, metric
        assert "totalNumber" not in counts, metric


def test_a_check_without_diagnostics_publishes_no_counts():
    counts = _published(Check(type="schema", result=ResultEnum.failed, engine="jsonschema"))

    assert "failedNumber" not in counts
    assert "totalNumber" not in counts


def test_the_api_reads_the_quality_fields_under_its_own_names():
    published = _published(
        Check(
            type="field_unique",
            result=ResultEnum.failed,
            category="quality",
            qualityId="order_id_is_unique",
            dimension="uniqueness",
            qualityDefinition="id: order_id_is_unique\ntype: library\n",
        )
    )

    assert published["qualityReference"] == "order_id_is_unique"
    assert published["qualityCategory"] == "quality"
    assert published["qualityCheckDefinition"] == "id: order_id_is_unique\ntype: library\n"
    # dimension is the one field of the four the API names the same way
    assert published["dimension"] == "uniqueness"
    assert published["qualityId"] == "order_id_is_unique"
    assert published["category"] == "quality"


def test_failed_samples_are_published_as_json_documents():
    published = _published(
        Check(
            type="field_required",
            result=ResultEnum.failed,
            failedSamples=[{"order_id": "B", "amount": None}],
        )
    )

    assert published["failedSamples"] == ['{"order_id": "B", "amount": null}']


def test_a_field_the_check_does_not_have_is_left_out_rather_than_published_as_null():
    published = _published(Check(type="field_required", result=ResultEnum.passed))

    assert published == {"type": "field_required", "result": "passed"}


def test_the_deprecated_check_field_names_are_still_published():
    """`failedSamples` changes shape to the JSON documents the API reads, so the
    deprecated `failed_samples` is what still carries the raw rows."""
    published = _published(
        Check(
            type="field_unique",
            result=ResultEnum.failed,
            qualityId="order_id_is_unique",
            failedSamples=[{"order_id": "A"}],
        )
    )

    assert published["quality_id"] == "order_id_is_unique"
    assert published["failed_samples"] == [{"order_id": "A"}]
