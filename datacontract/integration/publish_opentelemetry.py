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

# Tested with three environment variables:
#
# OTEL_SERVICE_NAME=datacontract-cli
# OTEL_EXPORTER_OTLP_ENDPOINT=https://YOUR_ID.apm.westeurope.azure.elastic-cloud.com:443
# OTEL_EXPORTER_OTLP_HEADERS=Authorization=Bearer%20secret
def publish_opentelemetry(run: Run):
    try:
        meter_name = "datacontract-cli"
        meter_version = metadata.version("datacontract-cli")

        if run.dataContractId is None:
            raise Exception("Cannot publish run results, as data contract ID is unknown")

        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        logging.info(f"Publishing test results to opentelemetry at {endpoint}")

        telemetry = Telemetry()
        provider = metrics.get_meter_provider()
        meter = provider.get_meter(meter_name, meter_version)
        meter.create_observable_gauge(
            name="datacontract.cli.run",
            callbacks=[lambda x: _to_observation_callback(run)],
            unit="result",
            description="The overall result of the data contract test run")

        telemetry.publish()
    except Exception as e:
        logging.error(f"Failed publishing test results. Error: {str(e)}")


def _to_observation_callback(run):
    yield _to_observation(run)


def _to_observation(run):
    attributes = {
        "datacontract.id": run.dataContractId,
        "datacontract.version": run.dataContractVersion,
    }
    if run.result == "passed":
        result_value = 0  # think of exit codes
    elif run.result == "warning":
        result_value = 1
    else:
        result_value = 2
    return Observation(value=result_value, attributes=attributes)


class Telemetry:
    def __init__(self):
        self.exporter = ConsoleMetricExporter()
        self.remote_exporter = OTLPMetricExporter()
        # using math.inf so it does not collect periodically. we do this in collect ourselves, one-time.
        self.reader = PeriodicExportingMetricReader(self.exporter, export_interval_millis=math.inf)
        self.remote_reader = PeriodicExportingMetricReader(self.remote_exporter, export_interval_millis=math.inf)
        provider = MeterProvider(metric_readers=[self.reader, self.remote_reader])
        metrics.set_meter_provider(provider)

    def publish(self):
        self.reader.collect()
        self.remote_reader.collect()
