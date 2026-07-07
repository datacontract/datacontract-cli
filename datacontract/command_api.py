import typer
from typing_extensions import Annotated

from datacontract.cli import app, debug_option, enable_debug_logging


def _get_uvicorn_arguments(port: int, host: str, context: typer.Context) -> dict:
    """
    Take the default datacontract uvicorn arguments and merge them with the
    extra arguments passed to the command to start the API.
    """
    default_args = {
        "app": "datacontract.api:app",
        "port": port,
        "host": host,
        "reload": True,
    }

    # Create a list of the extra arguments, remove the leading -- from the cli arguments
    trimmed_keys = list(map(lambda x: str(x).replace("--", ""), context.args[::2]))
    # Merge the two dicts and return them as one dict
    return default_args | dict(zip(trimmed_keys, context.args[1::2]))


@app.command(
    name="api",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    epilog="Example: datacontract api --port 4242 --host 0.0.0.0",
)
def api(
    ctx: Annotated[typer.Context, typer.Option(help="Extra arguments to pass to uvicorn.run().")],
    port: Annotated[int, typer.Option(help="Bind socket to this port.")] = 4242,
    host: Annotated[
        str, typer.Option(help="Bind socket to this host. Hint: For running in docker, set it to 0.0.0.0")
    ] = "127.0.0.1",
    debug: debug_option = None,
):
    """
    Start the datacontract CLI as server application with REST API.

    The OpenAPI documentation as Swagger UI is available on http://localhost:4242.
    You can execute the commands directly from the Swagger UI.

    To protect the API, you can set the environment variable DATACONTRACT_CLI_API_KEY to a secret API key.
    To authenticate, requests must include the header 'x-api-key' with the correct API key.
    This is highly recommended, as data contract tests may be subject to SQL injections or leak sensitive information.

    To connect to servers (such as a Snowflake data source), set the credentials as environment variables as documented in
    https://cli.datacontract.com/#test

    It is possible to run the API with extra arguments for `uvicorn.run()` as keyword arguments, e.g.:
    `datacontract api --port 1234 --root_path /datacontract`.
    """
    enable_debug_logging(debug)

    import uvicorn
    from uvicorn.config import LOGGING_CONFIG

    log_config = LOGGING_CONFIG
    log_config["root"] = {"level": "INFO"}

    uvicorn_args = _get_uvicorn_arguments(port, host, ctx)
    # Add the log config
    uvicorn_args["log_config"] = log_config
    # Run uvicorn
    uvicorn.run(**uvicorn_args)
