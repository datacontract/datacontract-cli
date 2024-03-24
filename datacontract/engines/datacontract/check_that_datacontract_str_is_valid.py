import logging

import fastjsonschema
import yaml
from fastjsonschema import JsonSchemaValueException

from datacontract.lint.schema import fetch_schema
from datacontract.model.run import Check, Run


def check_that_datacontract_str_is_valid(run: Run, data_contract_str: str):
    schema = fetch_schema()
    data_contract_yaml = yaml.safe_load(data_contract_str)
    try:
        fastjsonschema.validate(schema, data_contract_yaml)
        logging.debug("YAML data is valid.")
        run.checks.append(
            Check(
                type="lint",
                result="passed",
                name="Check that data contract YAML is valid",
                engine="datacontract",
            )
        )
    except JsonSchemaValueException as e:
        logging.warning("YAML data is invalid.")
        logging.warning(f"Validation error: {e.message}")
        run.checks.append(
            Check(
                type="lint",
                result="failed",
                name="Check that data contract YAML is valid",
                reason=e.message,
                engine="datacontract",
            )
        )
    except Exception as e:
        logging.warning("YAML data is invalid.")
        logging.warning(f"Validation error: {str(e)}")
        run.checks.append(
            Check(
                type="lint",
                result="failed",
                name="Check that data contract YAML is valid",
                reason=str(e),
                engine="datacontract",
            )
        )
