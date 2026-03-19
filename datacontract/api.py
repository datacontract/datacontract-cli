import logging
import os
from typing import Annotated, Optional

import typer
from fastapi import Body, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.security.api_key import APIKeyHeader

from datacontract.data_contract import DataContract, ExportFormat
from datacontract.model.run import Run

DATA_CONTRACT_EXAMPLE_PAYLOAD = """apiVersion: v3.1.0
kind: DataContract
id: orders
name: Orders
version: 1.0.0
status: active
description:
  purpose: "Provides order and line item data for analytics and reporting"
  usage: "Used by analytics team for sales analysis and business intelligence"
  limitations: "Contains only the last 2 years of data"
  customProperties:
    - property: "sensitivity"
      value: "secret"
      description: "Data contains personally identifiable information"
  authoritativeDefinitions:
    - url: "https://entropy-data.com/policies/gdpr-compliance"
      type: "businessDefinition"
      description: "GDPR compliance policy for handling customer data"
schema:
  - name: orders
    physicalType: TABLE
    description: All historic web shop orders since 2020-01-01. Includes successful and cancelled orders.
    properties:
      - name: order_id
        logicalType: string
        description: The internal order id for every orders. Do not show this to a customer.
        businessName: Internal Order ID
        physicalType: UUID
        examples:
          - 99e8bb10-3785-4634-9664-8dc79eb69d43
        primaryKey: true
        classification: internal
        required: true
        unique: true
      - name: customer_id
        logicalType: string
        description: A reference to the customer number
        businessName: Customer Number
        physicalType: TEXT
        examples:
          - c123456789
        required: true
        unique: false
        logicalTypeOptions:
          minLength: 10
          maxLength: 10
        authoritativeDefinitions:
          - type: definition
            url: https://example.com/definitions/sales/customer/customer_id
        tags:
          - pii:true
        classification: internal
        criticalDataElement: true
      - name: order_total
        logicalType: integer
        description: The order total amount in cents, including tax, after discounts.
          Includes shipping costs.
        physicalType: INTEGER
        examples:
          - "9999"
        quality:
          - type: text
            description: The order_total equals the sum of all related line items.
        required: true
        businessName: Order Amount
      - name: order_timestamp
        logicalType: timestamp
        description: The time including timezone when the order payment was successfully
          confirmed.
        physicalType: TIMESTAMPTZ
        businessName: Order Date
        examples:
          - "2025-03-01 14:30:00+01"
      - name: order_status
        businessName: Status
        description: The business status of the order
        logicalType: string
        physicalType: TEXT
        examples:
          - shipped
        quality:
          - type: library
            description: Ensure that there are no other status values.
            metric: invalidValues
            arguments:
              validValues:
                - pending
                - paid
                - processing
                - shipped
                - delivered
                - cancelled
                - refunded
            mustBe: 0
    quality:
      - type: library
        metric: rowCount
        mustBeGreaterThan: 100000
        description: If there are less than 100k rows, something is wrong.
  - name: line_items
    physicalType: table
    description: Details for each item in an order
    properties:
      - name: line_item_id
        logicalType: string
        description: Unique identifier for the line item
        physicalType: UUID
        examples:
          - 12c9ba21-0c44-4e29-ba72-b8fd01c1be30
        logicalTypeOptions:
          format: uuid
        required: true
        primaryKey: true
      - name: sku
        logicalType: string
        businessName: Stock Keeping Unit
        description: Identifier for the purchased product
        physicalType: TEXT
        examples:
          - 111222333
        required: true
      - name: price
        logicalType: integer
        description: Price in cents for this line item including tax
        physicalType: INTEGER
        examples:
          - 9999
        required: true
      - name: order_id
        required: false
        primaryKey: false
        logicalType: string
        physicalType: UUID
        relationships:
          - type: foreignKey
            to: orders.order_id
servers:
  - server: production
    environment: prod
    type: postgres
    host: aws-1-eu-central-2.pooler.supabase.com
    port: 6543
    database: postgres
    schema: dp_orders_v1
team:
  name: sales
  description: This data product is owned by the "Sales" team
  members:
    - username: john@example.com
      name: John Doe
      role: Owner
  authoritativeDefinitions:
    - type: slack
      url: https://slack.example.com/teams/sales
roles:
  - role: analyst_us
    description: Read access for analytics to US orders
  - role: analyst_eu
    description: Read access for analytics to EU orders
slaProperties:
  - property: availability
    value: 99.9%
    description: Data platform uptime guarantee
  - property: retention
    value: "1"
    unit: year
    description: Data will be deleted after 1 year
  - property: freshness
    value: "24"
    unit: hours
    description: Within 24 hours of order placement
  - property: support
    value: business hours
    description: Support only during business hours
price:
  priceAmount: 0
  priceCurrency: USD
  priceUnit: monthly
tags:
  - e-commerce
  - transactions
  - pii
customProperties:
  - property: dataPlatformRole
    value: role_orders_v1
contractCreatedTs: "2025-01-15T10:00:00Z"
"""

app = FastAPI(
    docs_url="/",
    title="Data Contract CLI API",
    summary="You can use the API to test, export, and lint your data contracts.",
    license_info={
        "name": "MIT License",
        "identifier": "MIT",
    },
    contact={"name": "Data Contract CLI", "url": "https://cli.datacontract.com/"},
    openapi_tags=[
        {
            "name": "test",
            "externalDocs": {
                "description": "Documentation",
                "url": "https://cli.datacontract.com/#test",
            },
        },
        {
            "name": "lint",
            "externalDocs": {
                "description": "Documentation",
                "url": "https://cli.datacontract.com/#lint",
            },
        },
        {
            "name": "export",
            "externalDocs": {
                "description": "Documentation",
                "url": "https://cli.datacontract.com/#export",
            },
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(
    name="x-api-key",
    auto_error=False,  # this makes authentication optional
)


def check_api_key(api_key_header: str | None):
    correct_api_key = os.getenv("DATACONTRACT_CLI_API_KEY")
    if correct_api_key is None or correct_api_key == "":
        logging.info("Environment variable DATACONTRACT_CLI_API_KEY is not set. Skip API key check.")
        return
    if api_key_header is None or api_key_header == "":
        logging.info("The API key is missing.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Use Header 'x-api-key' to provide the API key.",
        )
    if api_key_header != correct_api_key:
        logging.info("The provided API key is not correct.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The provided API key is not correct.",
        )
    logging.info("Request authenticated with API key.")
    pass


@app.post(
    "/test",
    tags=["test"],
    summary="Run data contract tests",
    description="""
              Run schema and quality tests. Data Contract CLI connects to the data sources configured in the server section.
              This usually requires credentials to access the data sources.
              Credentials must be provided via environment variables when running the web server.
              POST the data contract YAML as payload.
            """,
    responses={
        401: {
            "description": "Unauthorized (when an environment variable DATACONTRACT_CLI_API_KEY is configured).",
            "content": {
                "application/json": {
                    "examples": {
                        "api_key_missing": {
                            "summary": "API key Missing",
                            "value": {"detail": "Missing API key. Use Header 'x-api-key' to provide the API key."},
                        },
                        "api_key_wrong": {
                            "summary": "API key Wrong",
                            "value": {"detail": "The provided API key is not correct."},
                        },
                    }
                }
            },
        },
    },
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
)
async def test(
    body: Annotated[
        str,
        Body(
            title="Data Contract YAML",
            media_type="application/yaml",
            examples=[DATA_CONTRACT_EXAMPLE_PAYLOAD],
        ),
    ],
    api_key: Annotated[str | None, Depends(api_key_header)] = None,
    server: Annotated[
        str | None,
        Query(
            description="The server name to test. Optional, if there is only one server.",
            examples=["production"],
        ),
    ] = None,
    publish_url: Annotated[
        str | None,
        Query(
            description="URL to publish test results. Optional, if you want to publish the test results to a Data Mesh Manager or Data Contract Manager. Example: https://api.datamesh-manager.com/api/test-results",
            examples=["https://api.datamesh-manager.com/api/test-results"],
        ),
    ] = None,
) -> Run:
    check_api_key(api_key)
    logging.info("Testing data contract...")
    logging.info(body)
    return DataContract(data_contract_str=body, server=server, publish_url=publish_url).test()


@app.post(
    "/lint",
    tags=["lint"],
    summary="Validate that the datacontract.yaml is correctly formatted.",
    description="""Validate that the datacontract.yaml is correctly formatted.""",
)
async def lint(
    body: Annotated[
        str,
        Body(
            title="Data Contract YAML",
            media_type="application/yaml",
            examples=[DATA_CONTRACT_EXAMPLE_PAYLOAD],
        ),
    ],
    schema: Annotated[
        str | None,
        Query(
            examples=["https://datacontract.com/datacontract.schema.json"],
            description="The schema to use for validation. This must be a URL.",
        ),
    ] = None,
):
    data_contract = DataContract(data_contract_str=body, schema_location=schema)
    lint_result = data_contract.lint()
    return {"result": lint_result.result, "checks": lint_result.checks}


@app.post(
    "/export",
    tags=["export"],
    summary="Convert data contract to a specific format.",
    response_class=PlainTextResponse,
)
def export(
    body: Annotated[
        str,
        Body(
            title="Data Contract YAML",
            media_type="application/yaml",
            examples=[DATA_CONTRACT_EXAMPLE_PAYLOAD],
        ),
    ],
    format: Annotated[ExportFormat, typer.Option(help="The export format.")],
    server: Annotated[
        str | None,
        Query(
            examples=["production"],
            description="The server name to export. Optional, if there is only one server.",
        ),
    ] = None,
    model: Annotated[
        str | None,
        Query(
            description="Use the key of the model in the data contract yaml file "
            "to refer to a model, e.g., `orders`, or `all` for all "
            "models (default).",
        ),
    ] = "all",
    rdf_base: Annotated[
        Optional[str],
        typer.Option(help="[rdf] The base URI used to generate the RDF graph.", rich_help_panel="RDF Options"),
    ] = None,
    sql_server_type: Annotated[
        Optional[str],
        Query(
            description="[sql] The server type to determine the sql dialect. By default, it uses 'auto' to automatically detect the sql dialect via the specified servers in the data contract.",
        ),
    ] = None,
):
    result = DataContract(data_contract_str=body, server=server).export(
        export_format=format,
        model=model,
        rdf_base=rdf_base,
        sql_server_type=sql_server_type,
    )

    return result
