"""The check fields renamed to camelCase keep working under their old names.

`quality_id` / `failed_samples` were renamed to `qualityId` / `failedSamples` to
match the rest of the test-results model (`runId`, `dataContractId`, ...). Code
and stored test results written against the old names must keep working.
"""

import pytest

from datacontract.model.run import Check


def test_reading_the_old_name_returns_the_new_value():
    check = Check(type="field_type", qualityId="orders_not_empty", failedSamples=[{"id": 1}])

    with pytest.warns(DeprecationWarning, match="Check.quality_id is deprecated"):
        assert check.quality_id == "orders_not_empty"
    with pytest.warns(DeprecationWarning, match="Check.failed_samples is deprecated"):
        assert check.failed_samples == [{"id": 1}]


def test_writing_the_old_name_sets_the_new_field():
    check = Check(type="field_type")

    with pytest.warns(DeprecationWarning, match="Check.quality_id is deprecated"):
        check.quality_id = "orders_not_empty"
    with pytest.warns(DeprecationWarning, match="Check.failed_samples is deprecated"):
        check.failed_samples = [{"id": 1}]

    assert check.qualityId == "orders_not_empty"
    assert check.failedSamples == [{"id": 1}]


def test_the_old_names_are_still_accepted_as_input():
    # keyword construction, and test results serialized by an older version
    assert Check(type="field_type", quality_id="r", failed_samples=[1]).qualityId == "r"
    restored = Check.model_validate({"type": "field_type", "quality_id": "r", "failed_samples": [1]})
    assert (restored.qualityId, restored.failedSamples) == ("r", [1])


def test_a_set_field_is_serialized_under_both_names():
    # the test results are published to /api/test-results, so a consumer still
    # reading the old names keeps working
    check = Check(type="field_type", quality_id="r", failed_samples=[1])

    serialized = check.model_dump(exclude_none=True)

    assert serialized == {
        "type": "field_type",
        "qualityId": "r",
        "failedSamples": [1],
        "quality_id": "r",
        "failed_samples": [1],
    }


def test_an_unset_field_is_not_serialized_under_the_old_name():
    check = Check(type="field_type")

    serialized = check.model_dump()

    assert serialized["qualityId"] is None
    assert serialized["failedSamples"] is None
    assert "quality_id" not in serialized
    assert "failed_samples" not in serialized
