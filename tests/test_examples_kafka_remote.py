import os
import sys

import pytest
import six

# Fix for Python 3.12
if sys.version_info >= (3, 12, 1):
    sys.modules['kafka.vendor.six.moves'] = six.moves

import logging

from dotenv import load_dotenv

from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.INFO, force=True)

datacontract = "examples/kafka-remote/datacontract.yaml"


@pytest.mark.skipif(os.environ.get("DATACONTRACT_KAFKA_SASL_USERNAME") is None,
                    reason="Requires DATACONTRACT_KAFKA_SASL_USERNAME to be set")
def _test_examples_kafka_remote():
    load_dotenv(override=True)
    # os.environ['DATACONTRACT_KAFKA_SASL_USERNAME'] = "xxx"
    # os.environ['DATACONTRACT_KAFKA_SASL_PASSWORD'] = "xxx"
    data_contract = DataContract(data_contract_file=datacontract)

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
