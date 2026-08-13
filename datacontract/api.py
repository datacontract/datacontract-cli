import json
import logging
import os
import tempfile
from importlib import metadata
from typing import Annotated, Optional

import pydantic
import yaml
from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field, ValidationError

from datacontract.config import Config, known_env_names
from datacontract.data_contract import DataContract, ExportFormat
from datacontract.model.changelog import ChangelogEntry
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Check, ResultEnum, Run

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


def _require_schema_url(schema: str | None) -> str | None:
    """Reject anything that is not an http(s) URL.

    The parameter is documented as a URL, but `fetch_schema` falls through to the
    filesystem for anything else — so without this an unauthenticated caller could
    have the server open its own files, and tell existing paths from missing ones
    by the error it got back.
    """
    if schema is None:
        return None
    if not schema.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The schema parameter must be an http:// or https:// URL.",
        )
    return schema


def _cli_version() -> str:
    try:
        return metadata.version("datacontract-cli")
    except metadata.PackageNotFoundError:
        return "0.0.0"


API_DESCRIPTION = """
The Data Contract CLI as a web server. Every endpoint takes an
[ODCS](https://bitol-io.github.io/open-data-contract-standard/) data contract and runs one of the
CLI commands against it, so anything `datacontract test|lint|export|changelog` can do on the command
line can be done over HTTP.

The data contract is the request body: `POST` it as `application/yaml` (or as a JSON string) —
there is no contract storage, every request is self-contained.

## Authentication

Authentication is off unless the server was started with the environment variable
`DATACONTRACT_CLI_API_KEY` set. When it is set, every endpoint requires the header `x-api-key` with
that value, and answers `401` when the header is missing and `403` when it is wrong.

Securing the API is strongly recommended: `POST /test` connects to your data sources, and test
results may contain sensitive information.

## Connecting to data sources

`POST /test` needs credentials for the server described in the contract's `servers` section. Provide
them either as environment variables when starting the server, or per request as `datacontract-*`
headers, which are matched case-insensitively and map mechanically to the environment variable names
(`datacontract-snowflake-password` sets `DATACONTRACT_SNOWFLAKE_PASSWORD` for that request only).
Per-request headers are never written to the process environment, so one server can serve several
tenants. Send them over HTTPS only.

See [Configuration](https://docs.datacontract.com/configuration) for the full list of options.
"""

app = FastAPI(
    docs_url="/",
    title="Data Contract CLI API",
    summary="Test, lint, export, and compare data contracts over HTTP.",
    description=API_DESCRIPTION,
    version=_cli_version(),
    license_info={
        "name": "MIT License",
        "identifier": "MIT",
    },
    contact={
        "name": "Data Contract CLI",
        "url": "https://docs.datacontract.com/",
    },
    # Relative, so the document works for any deployment. A second, absolute entry would
    # show up as a target in the Swagger UI dropdown and invite sending contracts there.
    servers=[{"url": "/", "description": "The server this document was loaded from"}],
    openapi_tags=[
        {
            "name": "test",
            "description": "Run the schema and quality tests of a data contract against the actual data.",
            "externalDocs": {
                "description": "Documentation",
                "url": "https://docs.datacontract.com/testing/",
            },
        },
        {
            "name": "lint",
            "description": "Validate that a data contract is syntactically correct and follows the standard.",
            "externalDocs": {
                "description": "Documentation",
                "url": "https://docs.datacontract.com/commands/lint",
            },
        },
        {
            "name": "export",
            "description": "Convert a data contract into another format, such as SQL DDL, Avro, or dbt.",
            "externalDocs": {
                "description": "Documentation",
                "url": "https://docs.datacontract.com/exports/",
            },
        },
        {
            "name": "changelog",
            "description": "Compare two versions of a data contract and list what changed.",
            "externalDocs": {
                "description": "Documentation",
                "url": "https://docs.datacontract.com/commands/changelog",
            },
        },
    ],
)

_fastapi_openapi = app.openapi


def _openapi_with_external_docs() -> dict:
    """Add the document-level `externalDocs`, which FastAPI has no constructor argument for."""
    schema = _fastapi_openapi()
    schema.setdefault(
        "externalDocs",
        {
            "description": "Data Contract CLI documentation",
            "url": "https://docs.datacontract.com/api",
        },
    )
    return schema


app.openapi = _openapi_with_external_docs

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(
    name="x-api-key",
    description="The secret the server was started with in the environment variable "
    "`DATACONTRACT_CLI_API_KEY`. Only required if that variable is set.",
    auto_error=False,  # this makes authentication optional
)


class ErrorResponse(BaseModel):
    """The body returned for a request that could not be handled."""

    detail: str = Field(
        description="A human-readable explanation of why the request failed.",
        examples=["Missing API key. Use Header 'x-api-key' to provide the API key."],
    )


class RequestValidationErrorItem(BaseModel):
    """A single violation found while validating the request itself."""

    loc: list[str | int] = Field(description="The path to the offending part of the request.")
    msg: str = Field(description="What is wrong with it.")
    type: str = Field(description="The machine-readable error type.")


class UnprocessableEntityResponse(BaseModel):
    """The body returned for a request that is well-formed but cannot be processed."""

    detail: str | list[RequestValidationErrorItem] = Field(
        description="A message explaining why the request was rejected, or — when the request itself "
        "failed validation — one entry per violation.",
        examples=["The schema parameter must be an http:// or https:// URL."],
    )


AUTHENTICATION_RESPONSES: dict[int | str, dict] = {
    401: {
        "description": "The API key is missing (only when the server runs with DATACONTRACT_CLI_API_KEY set).",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {"detail": "Missing API key. Use Header 'x-api-key' to provide the API key."}
            }
        },
    },
    403: {
        "description": "The provided API key is not correct.",
        "model": ErrorResponse,
        "content": {"application/json": {"example": {"detail": "The provided API key is not correct."}}},
    },
}


_CONFIG_HEADER_PREFIX = "datacontract-"


def config_from_headers(headers) -> "Config | None":
    """Build a per-request Config from configuration option headers.

    Header names are matched case-insensitively and map mechanically to the env
    var names: uppercase, dashes to underscores — ``datacontract-snowflake-password``
    → ``DATACONTRACT_SNOWFLAKE_PASSWORD``, ``entropy-data-api-key`` →
    ``ENTROPY_DATA_API_KEY``. Returns None when no config headers are present,
    so env-var-configured deployments behave exactly as before. Unknown
    ``datacontract-*`` option names are rejected with a 400.
    """
    known = known_env_names()
    values = {}
    for name, value in headers.items():
        lowered = name.lower()
        env = lowered.upper().replace("-", "_")
        if lowered.startswith(_CONFIG_HEADER_PREFIX) or env in known:
            values[env] = value
    if not values:
        return None
    try:
        return Config.resolve(values)
    except (ValueError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datacontract-* configuration header: {e}",
        )


def _parse_filters_query(filters: str | None) -> dict[str, str] | None:
    """Parse the `filters` query parameter (JSON object mapping schema name to predicate)."""
    if filters is None:
        return None
    detail = (
        "The filters parameter must be a JSON object mapping schema name to a SQL predicate, "
        'e.g., {"orders": "ingested_at >= CURRENT_DATE - 1"}.'
    )
    try:
        parsed = json.loads(filters)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)
    if (
        not isinstance(parsed, dict)
        or not parsed
        or not all(isinstance(predicate, str) and predicate.strip() for predicate in parsed.values())
    ):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)
    return {schema_name: predicate.strip() for schema_name, predicate in parsed.items()}


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
    operation_id="testDataContract",
    summary="Run the tests of a data contract",
    description="""
Run the schema and quality tests of a data contract against the actual data. The Data Contract CLI
connects to the data source described by the contract's `servers` section, so this usually requires
credentials — set them as environment variables when starting the server, or send them per request
as `datacontract-*` headers (see the API description).

`POST` the data contract as `application/yaml`. The response is a test run with one check per
executed test; `result` is `passed` only if every check passed. Note that a failed test is a
`200 OK` with `"result": "failed"` — a non-2xx status means the request itself could not be
handled. A contract that cannot be parsed is reported the same way, as a failed check.
            """,
    response_description="The test run, with one check per executed test.",
    responses={
        **AUTHENTICATION_RESPONSES,
        400: {
            "description": "A `datacontract-*` header does not name a known configuration option, "
            "or its value is not valid for that option.",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid datacontract-* configuration header: "
                        "DATACONTRACT_SNOWFLAKE_LOGIN_TIMEOUT: input should be a valid integer"
                    }
                }
            },
        },
        422: {
            "description": "`filter` and `filters` were both given, or `filters` is not a JSON object "
            "mapping schema name to a SQL predicate.",
            "model": UnprocessableEntityResponse,
        },
    },
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
)
async def test(
    request: Request,
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
    filter: Annotated[
        str | None,
        Query(
            description="A SQL predicate to filter the rows under test, in the dialect of the server. "
            "Only works if a single schema is tested; for contracts with multiple schemas, use filters. "
            "Schema checks and custom SQL queries are not filtered.",
            examples=["ingested_at >= CURRENT_DATE - 1"],
        ),
    ] = None,
    filters: Annotated[
        str | None,
        Query(
            description="Row filters per schema, as a JSON object mapping schema name to SQL predicate. "
            "Schema checks and custom SQL queries are not filtered.",
            examples=['{"orders": "ingested_at >= CURRENT_DATE - 1"}'],
        ),
    ] = None,
) -> Run:
    check_api_key(api_key)
    parsed_filters = _parse_filters_query(filters)
    if filter is not None and parsed_filters is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Use either the filter or the filters parameter, not both.",
        )
    logging.info("Testing data contract...")
    logging.info(body)
    return DataContract(
        data_contract_str=body,
        server=server,
        publish_url=publish_url,
        fastapi_url=str(request.url),
        config=config_from_headers(request.headers),
        filter=filter,
        filters=parsed_filters,
    ).test()


class LintResponse(BaseModel):
    """The outcome of validating a data contract against the schema."""

    result: ResultEnum = Field(
        description="`passed` if the data contract is valid, otherwise the most severe check result.",
        examples=["passed"],
    )
    checks: list[Check] = Field(
        description="One entry per validation performed. A valid contract yields a single passed check; "
        "an invalid one yields a failed check per schema violation.",
    )


@app.post(
    "/lint",
    tags=["lint"],
    operation_id="lintDataContract",
    summary="Validate that a data contract is correctly formatted",
    description="""
Validate that the data contract is syntactically correct and conforms to the Open Data Contract
Standard. No data source is contacted, so no credentials are needed.

An invalid contract is reported as a `200 OK` with `"result": "failed"` and one check per schema
violation — not as an error status. A `schema` that is not an `http(s)` URL is rejected with `422`.
            """,
    response_description="The lint result, with one check per validation performed.",
    responses={
        **AUTHENTICATION_RESPONSES,
        422: {
            "description": "The `schema` parameter is not an `http(s)` URL.",
            "model": UnprocessableEntityResponse,
        },
    },
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
    api_key: Annotated[str | None, Depends(api_key_header)] = None,
    schema: Annotated[
        str | None,
        Query(
            examples=["https://datacontract.com/datacontract.schema.json"],
            description="The JSON Schema to validate against, as an `http(s)` URL. "
            "Defaults to the schema for the contract's `apiVersion`.",
        ),
    ] = None,
    all_errors: Annotated[
        bool,
        Query(description="Report all JSON Schema validation errors instead of only the first one."),
    ] = False,
) -> LintResponse:
    check_api_key(api_key)
    data_contract = DataContract(
        data_contract_str=body, schema_location=_require_schema_url(schema), all_errors=all_errors
    )
    lint_result = data_contract.lint()
    return LintResponse(result=lint_result.result, checks=lint_result.checks)


class ChangelogRequest(BaseModel):
    """The two data contract versions to compare."""

    v1: str = Field(
        default=DATA_CONTRACT_EXAMPLE_PAYLOAD,
        title="Source Data Contract YAML",
        description="The data contract as it was before, as a YAML string.",
    )
    v2: str = Field(
        default=DATA_CONTRACT_EXAMPLE_PAYLOAD,
        title="Target Data Contract YAML",
        description="The data contract as it is now, as a YAML string.",
    )


class ChangelogResponse(BaseModel):
    """The differences between two versions of a data contract."""

    summary: list[ChangelogEntry] = Field(
        description="One entry per changed element, rolled up to the level a reader cares about "
        "(a renamed property is one entry, not one per changed attribute). Values are omitted.",
    )
    entries: list[ChangelogEntry] = Field(
        description="Every individual change, with the old and new value.",
    )


@app.post(
    "/changelog",
    tags=["changelog"],
    operation_id="changelogBetweenDataContracts",
    summary="Show a changelog between two data contracts",
    description="""
Compare two versions of an ODCS data contract and return what changed between them. Useful to
decide whether a new version is a breaking change before publishing it.

`POST` a JSON body with `v1` (before) and `v2` (after) as YAML strings. A contract that cannot be
parsed is answered with `422`.
    """,
    response_description="The changelog, as a rolled-up summary and the individual changes.",
    responses={
        **AUTHENTICATION_RESPONSES,
        422: {
            "description": "One of the two data contracts is not valid YAML or not a valid data contract.",
            "model": UnprocessableEntityResponse,
            "content": {"application/json": {"example": {"detail": "Invalid YAML: while parsing a block mapping"}}},
        },
    },
)
async def changelog_endpoint(
    body: ChangelogRequest,
    api_key: Annotated[str | None, Depends(api_key_header)] = None,
) -> ChangelogResponse:
    check_api_key(api_key)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f1:
        f1.write(body.v1)
        v1_path = f1.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f2:
        f2.write(body.v2)
        v2_path = f2.name

    try:
        result = DataContract(data_contract_file=v1_path).changelog(DataContract(data_contract_file=v2_path))
        return ChangelogResponse(summary=result.summary, entries=result.entries)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=422, detail=f"Invalid YAML: {e}")
    except pydantic.ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Invalid data contract: {e}")
    except DataContractException as e:
        raise HTTPException(status_code=422, detail=f"Data Contract Validation Failure: {e}")
    finally:
        os.unlink(v1_path)
        os.unlink(v2_path)


@app.post(
    "/export",
    tags=["export"],
    operation_id="exportDataContract",
    summary="Convert a data contract to another format",
    description="""
Convert a data contract into another format, such as SQL DDL, Avro, Protobuf, dbt, or HTML.

The response is the converted document as `text/plain`; its actual syntax depends on the requested
`format`. Some formats have extra parameters, marked with the format they apply to in their
description.
    """,
    response_description="The data contract converted to the requested format.",
    response_class=PlainTextResponse,
    # Spelled out rather than reusing the shared entries, because a route with a
    # non-JSON response_class would have FastAPI document every declared model in
    # that media type — while errors are always returned as JSON.
    responses={
        200: {
            "description": "The data contract converted to the requested format.",
            "content": {
                "text/plain": {
                    "schema": {"type": "string"},
                    "example": "CREATE TABLE orders (\n  order_id UUID PRIMARY KEY,\n  order_total INTEGER NOT NULL\n);",
                }
            },
        },
        401: {
            "description": AUTHENTICATION_RESPONSES[401]["description"],
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "example": {"detail": "Missing API key. Use Header 'x-api-key' to provide the API key."},
                }
            },
        },
        403: {
            "description": AUTHENTICATION_RESPONSES[403]["description"],
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "example": {"detail": "The provided API key is not correct."},
                }
            },
        },
        422: {
            "description": "The data contract could not be parsed, or is not a valid data contract.",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/UnprocessableEntityResponse"}}},
        },
    },
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
    format: Annotated[
        ExportFormat,
        Query(
            description="The format to convert the data contract to.",
            examples=["sql"],
        ),
    ],
    api_key: Annotated[str | None, Depends(api_key_header)] = None,
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
            examples=["all"],
        ),
    ] = "all",
    rdf_base: Annotated[
        Optional[str],
        Query(
            description="[rdf] The base URI used to generate the RDF graph.",
            examples=["https://example.com/"],
        ),
    ] = None,
    sql_server_type: Annotated[
        Optional[str],
        Query(
            description="[sql] The server type to determine the sql dialect. By default, it uses 'auto' to automatically detect the sql dialect via the specified servers in the data contract.",
            examples=["postgres"],
        ),
    ] = None,
):
    check_api_key(api_key)
    try:
        return DataContract(data_contract_str=body, server=server).export(
            export_format=format,
            model=model,
            rdf_base=rdf_base,
            sql_server_type=sql_server_type,
        )
    except yaml.YAMLError as e:
        raise HTTPException(status_code=422, detail=f"Invalid YAML: {e}")
    except pydantic.ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Invalid data contract: {e}")
    except DataContractException as e:
        raise HTTPException(status_code=422, detail=f"Data Contract Validation Failure: {e}")
