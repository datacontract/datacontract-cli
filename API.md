# Data Contract CLI API

Data Contract CLI can be started as a web server to provide a REST API for data contract testing,
linting, and exports.

## Demo

Open the Demo: [https://api.datacontract.com](https://api.datacontract.com)

You can use the API to test, export, and lint your data contracts.
Please note, that this demo endpoint cannot test to your secured data sources.

## Starting the API

Start the API

```
datacontract api
```

You can specify the `--port` to change the port (default is `4242`) and
`--host` to change the host binding (default is `127.0.0.1`).
If you run the API in a Docker container, you should bind to `--host 0.0.0.0`.

## Open the OpenAPI documentation

By default, the API will start on port 4242.
You can open the OpenAPI documentation in a Swagger UI by navigating
to [http://localhost:4242](http://localhost:4242).

## Test Data Contract

You can now use the REST API to test data contracts.
POST a data contract as payload to the `/test` endpoint, and receive a response as JSON with the
test results.

```bash
curl -X 'POST' \
  'http://localhost:4242/test?server=production' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/yaml' \
  -d 'dataContractSpecification: 1.1.0
id: urn:datacontract:checkout:orders-latest
info:
  title: Orders Latest
  version: 2.0.0
  owner: Sales Team
servers:
  production:
    type: s3
    location: s3://datacontract-example-orders-latest/v2/{model}/*.json
    format: json
    delimiter: new_line
models:
  orders:
    description: One record per order. Includes cancelled and deleted orders.
    type: table
    fields:
      order_id:
        type: string
        primaryKey: true
      order_timestamp:
        description: The business timestamp in UTC when the order was successfully registered in the source system and the payment was successful.
        type: timestamp
        required: true
        examples:
          - '\''2024-09-09T08:30:00Z'\''
      order_total:
        description: Total amount the smallest monetary unit (e.g., cents).
        type: long
        required: true
        examples:
          - 9999
        quality:
          - type: sql
            description: 95% of all order total values are expected to be between 10 and 499 EUR.
            query: |
              SELECT quantile_cont(order_total, 0.95) AS percentile_95
              FROM orders
            mustBeBetween:
              - 1000
              - 99900
      customer_id:
        description: Unique identifier for the customer.
        type: text
        minLength: 10
        maxLength: 20'
```

Or if you have the file locally available:

```
curl -X POST "http://localhost:4242/test?server=production" \
  --data-binary @datacontract.yaml
```

## Export a Data Contract

Example to generate SQL code from a data contract:

```
curl -X POST "http://localhost:4242/export?format=sql" \
  --data-binary @datacontract.yaml
```

## Try it out

You can also use the Swagger UI to execute the commands directly.

## Configure Server Credentials

To connect to a data source (server), define the required credentials as environment variables,
before starting the API.

Example for Databricks:

```
export DATACONTRACT_SNOWFLAKE_USERNAME=123
export DATACONTRACT_SNOWFLAKE_PASSWORD=
export DATACONTRACT_SNOWFLAKE_WAREHOUSE=
export DATACONTRACT_SNOWFLAKE_ROLE=
```

## Secure the API

To protect the API, you can set the environment variable `DATACONTRACT_CLI_API_KEY` to a secret API
key.

To authenticate, requests must include the header `x-api-key` with the    
correct API key.

This is highly recommended, as data contract tests may be subject to SQL injections or leak
sensitive information.

```
export DATACONTRACT_CLI_API_KEY=<your-secret-key-such-as-a-random-uuid>
```

## Run as Docker Container

You can use the pre-built Docker image to start the API in a container.
You can run it in any container environment, such as Docker Compose, Kubernetes, Azure Container
Apps, Google Cloud Run, ...

Example for Docker Compose:

```
services:
  datacontract-api:
    image: datacontract/cli:latest
    ports:
      - "4242:4242"
    environment:
      - DATACONTRACT_CLI_API_KEY=a079ce4c-af90-45ab-abe5-a8d7697f60d6
      - DATACONTRACT_SNOWFLAKE_USERNAME=
      - DATACONTRACT_SNOWFLAKE_PASSWORD=
      - DATACONTRACT_SNOWFLAKE_WAREHOUSE=
      - DATACONTRACT_SNOWFLAKE_ROLE=
    command: ["api", "--host", "0.0.0.0"]
```

_docker-compose.yml_

and start with

```
docker compose up -d
```