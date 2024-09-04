from uuid import uuid4

from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter as OTLPgRPCMetricExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.metrics import Observation

from datacontract.integration.opentelemetry import _to_observation, Telemetry
from datacontract.model.run import Run

# logging.basicConfig(level=logging.DEBUG, force=True)


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
    expected = Observation(
        value=0,
        attributes={
            "datacontract.id": "datacontract-id-1234",
            "datacontract.version": "1.0.0",
        },
    )

    actual = _to_observation(run)

    assert expected == actual


def test_http_exporter_chosen_without_env():
    telemetry = Telemetry()

    assert isinstance(telemetry.remote_exporter, OTLPMetricExporter), (
        "Should use OTLPMetricExporter when OTEL_EXPORTER_OTLP_PROTOCOL is " "not set"
    )


def test_http_exporter_chosen_with_env_httpprotobuf(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")

    telemetry = Telemetry()

    assert isinstance(telemetry.remote_exporter, OTLPMetricExporter), (
        "Should use OTLPMetricExporter when OTEL_EXPORTER_OTLP_PROTOCOL is " "http/protobuf"
    )


def test_http_exporter_chosen_with_env_httpjson(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_PROTOCOL", "http/json")

    telemetry = Telemetry()

    assert isinstance(telemetry.remote_exporter, OTLPMetricExporter), (
        "Should use OTLPMetricExporter when OTEL_EXPORTER_OTLP_PROTOCOL is " "http/json"
    )


def test_grpc_exporter_chosen_with_env_GRPC(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_PROTOCOL", "GRPC")

    telemetry = Telemetry()

    assert isinstance(telemetry.remote_exporter, OTLPgRPCMetricExporter), (
        "Should use OTLPMetricExporter from gRPC package " "when OTEL_EXPORTER_OTLP_PROTOCOL is GRPC"
    )
