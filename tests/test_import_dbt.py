import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.imports.dbt_importer import read_dbt_manifest

# logging.basicConfig(level=logging.DEBUG, force=True)

dbt_manifest = "fixtures/dbt/import/manifest_jaffle_duckdb.json"
dbt_manifest_bigquery = "fixtures/dbt/import/manifest_jaffle_bigquery.json"
dbt_manifest_empty_columns = "fixtures/dbt/import/manifest_empty_columns.json"


def test_read_dbt_manifest_():
    result = read_dbt_manifest(dbt_manifest)
    assert len([node for node in result.nodes.values() if node.resource_type == "model"]) == 5


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "dbt",
            "--source",
            dbt_manifest,
        ],
    )
    assert result.exit_code == 0


def test_cli_bigquery():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "dbt",
            "--source",
            dbt_manifest_bigquery,
        ],
    )
    assert result.exit_code == 0


def test_cli_with_filter():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "dbt",
            "--source",
            dbt_manifest,
            "--dbt-model",
            "customers",
            "--dbt-model",
            "orders",
        ],
    )
    assert result.exit_code == 0


def test_import_dbt_manifest():
    result = DataContract().import_from_source("dbt", dbt_manifest)

    expected = """
dataContractSpecification: 1.1.0
id: my-data-contract-id
info:
  title: jaffle_shop
  version: 0.0.1
  dbt_version: 1.8.0
models:
  orders:
    description: This table has basic information about orders, as well as some derived
      facts based on payments
    fields:
      order_id:
        type: integer
        description: This is a unique identifier for an order
        primaryKey: true
        required: true
        unique: true
      customer_id:
        type: integer
        description: Foreign key to the customers table
        required: true
        references: customers.customer_id
      order_date:
        type: date
        description: Date (UTC) that the order was placed
      status:
        type: varchar
        description: 'Orders can be one of the following statuses:


          | status         | description                                                                                                            |

          |----------------|------------------------------------------------------------------------------------------------------------------------|

          | placed         | The order has been placed but has not yet left the warehouse                                                           |

          | shipped        | The order has ben shipped to the customer and is currently
          in transit                                                  |

          | completed      | The order has been received by the customer                                                                            |

          | return_pending | The customer has indicated that they would like to return
          the order, but it has not yet been received at the warehouse |

          | returned       | The order has been returned by the customer and received
          at the warehouse                                              |'
      credit_card_amount:
        type: double
        description: Amount of the order (AUD) paid for by credit card
        required: true
      coupon_amount:
        type: double
        description: Amount of the order (AUD) paid for by coupon
        required: true
      bank_transfer_amount:
        type: double
        description: Amount of the order (AUD) paid for by bank transfer
        required: true
      gift_card_amount:
        type: double
        description: Amount of the order (AUD) paid for by gift card
        required: true
      amount:
        type: double
        description: Total amount (AUD) of the order
        required: true
    tags: []
  stg_customers:
    description: ''
    fields:
      customer_id:
        type: integer
        description: ''
        primaryKey: true
        required: true
        unique: true
      first_name:
        type: varchar
        description: ''
      last_name:
        type: varchar
        description: ''
    tags: []
  stg_orders:
    description: ''
    fields:
      order_id:
        type: integer
        description: ''
        primaryKey: true
        required: true
        unique: true
      customer_id:
        type: integer
        description: ''
      order_date:
        type: date
        description: ''
      status:
        type: varchar
        description: ''
    tags: []
  stg_payments:
    description: ''
    fields:
      payment_id:
        type: integer
        description: ''
        primaryKey: true
        required: true
        unique: true
      order_id:
        type: integer
        description: ''
      payment_method:
        type: varchar
        description: ''
      amount:
        type: double
        description: ''
    tags: []
  customers:
    description: This table has basic information about a customer, as well as some
      derived facts based on a customer's orders
    fields:
      customer_id:
        type: integer
        description: This is a unique identifier for a customer
        primaryKey: true
        required: true
        unique: true
      first_name:
        type: varchar
        description: Customer's first name. PII.
        tags:
        - PII
      last_name:
        type: varchar
        description: Customer's last name. PII.
        tags:
        - PII
      first_order:
        type: date
        description: Date (UTC) of a customer's first order
      most_recent_order:
        type: date
        description: Date (UTC) of a customer's most recent order
      number_of_orders:
        type: bigint
        description: Count of the number of orders a customer has placed
      customer_lifetime_value:
        type: double
        description: ''
    tags:
    - TABLE_PII"""
    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    assert DataContract(data_contract_str=expected).lint(enabled_linters="none").has_passed()


def test_import_dbt_manifest_bigquery():
    result = DataContract().import_from_source("dbt", dbt_manifest_bigquery)

    expected = """
dataContractSpecification: 1.1.0
id: my-data-contract-id
info:
  title: jaffle_shop
  version: 0.0.1
  dbt_version: 1.8.0
models:
  orders:
    description: This table has basic information about orders, as well as some derived
      facts based on payments
    fields:
      order_id:
        type: bigint
        description: This is a unique identifier for an order
        primaryKey: true
        required: true
        unique: true
      customer_id:
        type: bigint
        description: Foreign key to the customers table
        required: true
        references: customers.customer_id
      order_date:
        type: date
        description: Date (UTC) that the order was placed
      status:
        type: string
        description: 'Orders can be one of the following statuses:


          | status         | description                                                                                                            |

          |----------------|------------------------------------------------------------------------------------------------------------------------|

          | placed         | The order has been placed but has not yet left the warehouse                                                           |

          | shipped        | The order has ben shipped to the customer and is currently
          in transit                                                  |

          | completed      | The order has been received by the customer                                                                            |

          | return_pending | The customer has indicated that they would like to return
          the order, but it has not yet been received at the warehouse |

          | returned       | The order has been returned by the customer and received
          at the warehouse                                              |'
      credit_card_amount:
        type: double
        description: Amount of the order (AUD) paid for by credit card
        required: true
      coupon_amount:
        type: double
        description: Amount of the order (AUD) paid for by coupon
        required: true
      bank_transfer_amount:
        type: double
        description: Amount of the order (AUD) paid for by bank transfer
        required: true
      gift_card_amount:
        type: double
        description: Amount of the order (AUD) paid for by gift card
        required: true
      amount:
        type: double
        description: Total amount (AUD) of the order
        required: true
    tags: []
  stg_customers:
    description: ''
    fields:
      customer_id:
        type: bigint
        description: ''
        primaryKey: true
        required: true
        unique: true
      first_name:
        type: string
        description: ''
      last_name:
        type: string
        description: ''
    tags: []
  stg_orders:
    description: ''
    fields:
      order_id:
        type: bigint
        description: ''
        primaryKey: true
        required: true
        unique: true
      customer_id:
        type: bigint
        description: ''
      order_date:
        type: date
        description: ''
      status:
        type: string
        description: ''
    tags: []
  stg_payments:
    description: ''
    fields:
      payment_id:
        type: bigint
        description: ''
        primaryKey: true
        required: true
        unique: true
      order_id:
        type: bigint
        description: ''
      payment_method:
        type: string
        description: ''
      amount:
        type: double
        description: ''
    tags: []
  customers:
    description: This table has basic information about a customer, as well as some
      derived facts based on a customer's orders
    fields:
      customer_id:
        type: bigint
        description: This is a unique identifier for a customer
        primaryKey: true
        required: true
        unique: true
      first_name:
        type: string
        description: Customer's first name. PII.
        tags:
        - PII
      last_name:
        type: string
        description: Customer's last name. PII.
        tags:
        - PII
      first_order:
        type: date
        description: Date (UTC) of a customer's first order
      most_recent_order:
        type: date
        description: Date (UTC) of a customer's most recent order
      number_of_orders:
        type: bigint
        description: Count of the number of orders a customer has placed
      customer_lifetime_value:
        type: double
        description: ''
    tags:
    - TABLE_PII"""
    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    assert DataContract(data_contract_str=expected).lint(enabled_linters="none").has_passed()


def test_import_dbt_manifest_with_filter_and_empty_columns():
    result = DataContract().import_from_source("dbt", dbt_manifest_empty_columns, dbt_model=["customers"])

    expected = """
dataContractSpecification: 1.1.0
id: my-data-contract-id
info:
  title: jaffle_shop
  version: 0.0.1
  dbt_version: 1.8.0
models:
  customers:
    description: This table has basic information about a customer, as well as some
      derived facts based on a customer's orders
    tags:
      - TABLE_PII
    """
    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    assert DataContract(data_contract_str=expected).lint(enabled_linters="none").has_passed()


def test_import_dbt_manifest_with_filter():
    result = DataContract().import_from_source("dbt", dbt_manifest, dbt_model=["customers"])

    expected = """
dataContractSpecification: 1.1.0
id: my-data-contract-id
info:
  title: jaffle_shop
  version: 0.0.1
  dbt_version: 1.8.0
models:
  customers:
    description: This table has basic information about a customer, as well as some
      derived facts based on a customer's orders
    fields:
      customer_id:
        type: integer
        description: This is a unique identifier for a customer
        primaryKey: true
        required: true
        unique: true
      first_name:
        type: varchar
        description: Customer's first name. PII.
        tags:
        - PII
      last_name:
        type: varchar
        description: Customer's last name. PII.
        tags:
        - PII
      first_order:
        type: date
        description: Date (UTC) of a customer's first order
      most_recent_order:
        type: date
        description: Date (UTC) of a customer's most recent order
      number_of_orders:
        type: bigint
        description: Count of the number of orders a customer has placed
      customer_lifetime_value:
        type: double
        description: ''
    tags:
    - TABLE_PII"""
    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    assert DataContract(data_contract_str=expected).lint(enabled_linters="none").has_passed()
