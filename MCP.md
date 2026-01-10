# Data Contract CLI MCP Server

Data Contract CLI can be started as an MCP (Model Context Protocol) server
to provide AI assistants with data contract-aware SQL execution capabilities.

## Starting the MCP Server

Start the MCP server:

```
datacontract mcp
```

You can specify the `--port` to change the port (default is `8000`) and
`--host` to change the host binding (default is `127.0.0.1`).
If you run the MCP server in a Docker container, you should bind to `--host 0.0.0.0`.

## Claude Desktop Configuration

### Local (stdio)

For local usage with Claude Desktop, add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "datacontract": {
      "command": "datacontract",
      "args": ["mcp"]
    }
  }
}
```

### Remote (Streamable HTTP)

For remote server deployments (MCP spec 2025-03-26):

```json
{
  "mcpServers": {
    "datacontract": {
      "url": "https://your-server.com/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

## The execute_sql Tool

The MCP server exposes a single tool `execute_sql` with the following parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sql` | string | Yes | SQL query to execute. Must be a SELECT statement (read-only). |
| `data_contract_path` | string | No | Path to data contract YAML file. |
| `data_contract_yaml` | string | No | Data contract YAML content as string. |
| `server` | string | No | Server name from data contract. Uses first supported server if not specified. |
| `output_format` | string | No | Output format: `markdown` (default), `json`, or `csv`. |

Either `data_contract_path` or `data_contract_yaml` must be provided.

### Example Usage

```
execute_sql(
    sql="SELECT * FROM orders LIMIT 10",
    data_contract_path="/path/to/datacontract.yaml",
    server="production"
)
```

### Supported Server Types

- `postgres` - PostgreSQL databases
- `snowflake` - Snowflake data warehouse
- `databricks` - Databricks SQL
- `bigquery` - Google BigQuery

## Configure Server Credentials

To connect to a data source (server), define the required credentials as environment variables
before starting the MCP server.

### PostgreSQL

```
export DATACONTRACT_POSTGRES_USERNAME=myuser
export DATACONTRACT_POSTGRES_PASSWORD=mypassword
```

### Snowflake

```
export DATACONTRACT_SNOWFLAKE_USERNAME=myuser
export DATACONTRACT_SNOWFLAKE_PASSWORD=mypassword
export DATACONTRACT_SNOWFLAKE_WAREHOUSE=MY_WAREHOUSE  # optional
```

### Databricks

```
export DATACONTRACT_DATABRICKS_TOKEN=dapi...
export DATACONTRACT_DATABRICKS_HTTP_PATH=/sql/1.0/endpoints/...
```

### BigQuery

```
export DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH=/path/to/service-account.json
# Or use the standard Google environment variable:
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

## Secure the MCP Server

To protect the MCP server, set the environment variable `DATACONTRACT_MCP_TOKEN` to a secret token.

To authenticate, clients must include the header `Authorization: Bearer <token>` with the
correct token.

This is highly recommended for production deployments.

```
export DATACONTRACT_MCP_TOKEN=<your-secret-token>
```

## Run as Docker Container

You can use the pre-built Docker image to start the MCP server in a container.
You can run it in any container environment, such as Docker Compose, Kubernetes, Azure Container
Apps, Google Cloud Run, etc.

Example for Docker Compose:

```yaml
services:
  datacontract-mcp:
    image: datacontract/cli:latest
    ports:
      - "8000:8000"
    environment:
      - DATACONTRACT_MCP_TOKEN=your-secret-token
      - DATACONTRACT_POSTGRES_USERNAME=myuser
      - DATACONTRACT_POSTGRES_PASSWORD=mypassword
    command: ["mcp", "--host", "0.0.0.0"]
```

_docker-compose.yml_

Start with:

```
docker compose up -d
```

## Security Notes

- Only read-only (SELECT) queries are allowed. INSERT, UPDATE, DELETE, and other modifying statements are rejected.
- SQL queries are validated using sqlglot before execution.
- Always set `DATACONTRACT_MCP_TOKEN` in production to prevent unauthorized access.
- Database credentials are never exposed to MCP clients; they are only used server-side.
