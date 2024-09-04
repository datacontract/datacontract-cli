import logging
import math
import os
from importlib import metadata

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter as OTLPgRPCMetricExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.metrics import Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader

from datacontract.model.run import Run


# Publishes metrics of a test run.
# Metric contains the values:
# 0 == test run passed,
# 1 == test run has warnings
# 2 == test run failed
# 3 == test run not possible due to an error
# 4 == test status unknown
#
# Tested with these environment variables:
#
# OTEL_SERVICE_NAME=datacontract-cli
# OTEL_EXPORTER_OTLP_ENDPOINT=https://YOUR_ID.apm.westeurope.azure.elastic-cloud.com:443
# OTEL_EXPORTER_OTLP_HEADERS=Authorization=Bearer%20secret (Optional, when using SaaS Products)
# OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf and OTEL_EXPORTER_OTLP_PROTOCOL=grpc
#
# Current limitations:
# - no gRPC support
# - currently, only ConsoleExporter and OTLP Exporter
# - Metrics only, no logs yet (but loosely planned)


def publish_test_results_to_opentelemetry(run: Run):
    try:
        if run.dataContractId is None:
            raise Exception("Cannot publish run results, as data contract ID is unknown")

        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        logging.info(f"Publishing test results to opentelemetry at {endpoint}")

        telemetry = Telemetry()
        provider = metrics.get_meter_provider()
        meter = provider.get_meter("com.datacontract.cli", metadata.version("datacontract-cli"))
        meter.create_observable_gauge(
            name="datacontract.cli.test",
            callbacks=[lambda x: _to_observation_callback(run)],
            unit="result",
            description="The overall result of the data contract test run",
        )

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
    elif run.result == "failed":
        result_value = 2
    elif run.result == "error":
        result_value = 3
    else:
        result_value = 4
    return Observation(value=result_value, attributes=attributes)


class Telemetry:
    def __init__(self):
        protocol = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL")

        # lower to allow grpc, GRPC and alike values.
        if protocol and protocol.lower() == "grpc":
            self.remote_exporter = OTLPgRPCMetricExporter()
        else:
            # Fallback to default OTEL http/protobuf which is used when the variable is not set.
            # This Exporter also works for http/json.
            self.remote_exporter = OTLPMetricExporter()

        self.console_exporter = ConsoleMetricExporter()
        # using math.inf so it does not collect periodically. we do this in collect ourselves, one-time.
        self.reader = PeriodicExportingMetricReader(self.console_exporter, export_interval_millis=math.inf)
        self.remote_reader = PeriodicExportingMetricReader(self.remote_exporter, export_interval_millis=math.inf)
        provider = MeterProvider(metric_readers=[self.reader, self.remote_reader])
        metrics.set_meter_provider(provider)

    def publish(self):
        self.reader.collect()
        self.remote_reader.collect()
