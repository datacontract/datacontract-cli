import logging
import os
from importlib import metadata
from uuid import uuid4
import math

from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.metrics import Observation

from datacontract.model.run import \
    Run
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader

logging.basicConfig(level=logging.DEBUG, force=True)


def publish_opentelemetry(run: Run, publish_url: str):
    try:
        otel_exporter_otlp_endpoint = publish_url
        otel_exporter_otlp_headers = os.getenv('OTEL_EXPORTER_OTLP_HEADERS')
        otel_service_name = "datacontract-cli"
        otel_service_version = metadata.version("datacontract-cli")

        if run.dataContractId is None:
            raise Exception("Cannot publish run results, as data contract ID is unknown")

        if otel_exporter_otlp_endpoint is None:
            raise Exception("Cannot publish run results, as publish_url is not set")

        if otel_exporter_otlp_headers is None:
            raise Exception("Cannot publish run results, as OTEL_EXPORTER_OTLP_HEADERS is not set")

        telemetry = Telemetry(endpoint=otel_exporter_otlp_endpoint, headers={
            "Authorization": "Bearer GfGQRPmvr8piYGFX7I",
        })
        provider = metrics.get_meter_provider()
        meter = provider.get_meter(otel_service_name, otel_service_version)
        meter.create_observable_gauge(
            name="datacontract.cli.run",
            callbacks=[lambda x: _to_observation(run)],
            unit="result",
            description="The overall result of the data contract test run")

        telemetry.send_to_publish_url()

        logging.info("Published test results to %s", publish_url)
    except Exception as e:
        logging.error(f"Failed publishing test results. Error: {str(e)}")


def _to_observation(run):
    attributes = {
        "datacontract.id": run.dataContractId,
        "datacontract.version": run.dataContractVersion,
    }
    if run.result == "passed":
        result_value = 0 # think of exit codes
    elif run.result == "warning":
        result_value = 1
    else:
        result_value = 2

    yield Observation(value=result_value, attributes=attributes)


class Telemetry:
    def __init__(self, endpoint: str, headers):
        self.exporter = ConsoleMetricExporter()
        self.remote_exporter = OTLPMetricExporter(endpoint=endpoint, headers=headers)
        # using math.inf so it does not collect periodically. we do this in collect ourselves, one-time.
        self.reader = PeriodicExportingMetricReader(self.exporter, export_interval_millis=math.inf)
        self.remote_reader = PeriodicExportingMetricReader(self.remote_exporter, export_interval_millis=math.inf)
        provider = MeterProvider(metric_readers=[self.reader, self.remote_reader])
        metrics.set_meter_provider(provider)

    def send_to_publish_url(self):
        self.reader.collect()
        self.remote_reader.collect()


# create a main method I can run
if __name__ == "__main__":
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
    publish_opentelemetry(run, "TBD")
