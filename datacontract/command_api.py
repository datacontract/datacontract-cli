import os

import typer
from typing_extensions import Annotated

from datacontract.cli import app, debug_option, enable_debug_logging
from datacontract.config.variables import CONTRACT_VARIABLES_ENV


def _get_uvicorn_arguments(port: int, host: str, reload: bool, context: typer.Context) -> dict:
    """
    Take the default datacontract uvicorn arguments and merge them with the
    extra arguments passed to the command to start the API.
    """
    default_args = {
        "app": "datacontract.api:app",
        "port": port,
        "host": host,
        "reload": reload,
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
    reload: Annotated[
        bool,
        typer.Option(
            "--reload/--no-reload",
            help="Watch the source files and restart the server on changes. For development only; off by default.",
        ),
    ] = False,
    contract_variables: Annotated[
        str | None,
        typer.Option(
            help="Environment variables a posted data contract may read through ${VAR} references, "
            "as comma-separated fnmatch globs (e.g. 'TABLE_*,CUTOFF_DATE', or '*' to allow all). Empty by default.",
        ),
    ] = None,
    allow_local_files: Annotated[
        bool | None,
        typer.Option(
            "--allow-local-files/--no-allow-local-files",
            help="Let a posted data contract read the server's own disk through servers[].type: local. Off by default.",
        ),
    ] = None,
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
    https://docs.datacontract.com/configuration

    It is possible to run the API with extra arguments for `uvicorn.run()` as keyword arguments, e.g.:
    `datacontract api --port 1234 --root_path /datacontract`.
    """
    enable_debug_logging(debug)

    # Passed through the environment, which survives uvicorn's --reload respawn.
    from datacontract.api import ALLOW_LOCAL_FILES_ENV

    if contract_variables is not None:
        os.environ[CONTRACT_VARIABLES_ENV] = contract_variables
    if allow_local_files is not None:
        os.environ[ALLOW_LOCAL_FILES_ENV] = "true" if allow_local_files else "false"

    import uvicorn
    from uvicorn.config import LOGGING_CONFIG

    log_config = LOGGING_CONFIG
    log_config["root"] = {"level": "INFO", "handlers": ["default"]}

    uvicorn_args = _get_uvicorn_arguments(port, host, reload, ctx)
    # Add the log config
    uvicorn_args["log_config"] = log_config
    # Run uvicorn
    uvicorn.run(**uvicorn_args)
