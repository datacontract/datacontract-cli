import logging
from uuid import uuid4

from opentelemetry.metrics import Observation
from typer.testing import CliRunner

from datacontract.integration.publish_opentelemetry import _to_observation
from datacontract.model.run import Run

logging.basicConfig(level=logging.DEBUG, force=True)


def test_convert_to_observation():
    run = Run(
        runId=uuid4(),
        dataContractId="datacontract-id-1234",
        dataContractVersion="1.0.0",
        result="passed",
        timestampStart="2021-01-01T00:00:00Z",
        timestampEnd="2021-01-01T00:00:00Z",
        checks=[],
        logs=[],
    )
    expected = Observation(value=0, attributes={
        "datacontract.id": "datacontract-id-1234",
        "datacontract.version": "1.0.0",
    })

    actual = _to_observation(run)

    assert expected == actual
