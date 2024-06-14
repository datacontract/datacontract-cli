from typing import Annotated, Union, Optional

import typer
from fastapi import FastAPI, File
from fastapi.responses import HTMLResponse

from datacontract.data_contract import DataContract, ExportFormat
from fastapi.responses import PlainTextResponse

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
def index():
    # TODO OpenAPI spec
    return """
    <html>
    <body>
    <h1>datacontract web server</h1>
    <ul>
    <li>POST /lint</li>
    <li>POST /export</li>
    </ul>
    </body>
    </html>
    """


@app.post("/lint")
def lint(file: Annotated[bytes, File()], linters: Union[str, set[str]] = "all"):
    data_contract = DataContract(data_contract_str=str(file, encoding="utf-8"))
    lint_result = data_contract.lint(enabled_linters=linters)
    return {"result": lint_result.result, "checks": lint_result.checks}


@app.post("/export", response_class=PlainTextResponse)
def export(
    file: Annotated[bytes, File()],
    export_format: Annotated[ExportFormat, typer.Option(help="The export format.")],
    server: Annotated[str, typer.Option(help="The server name to export.")] = None,
    model: Annotated[
        str,
        typer.Option(
            help="Use the key of the model in the data contract yaml file "
            "to refer to a model, e.g., `orders`, or `all` for all "
            "models (default)."
        ),
    ] = "all",
    rdf_base: Annotated[
        Optional[str],
        typer.Option(help="[rdf] The base URI used to generate the RDF graph.", rich_help_panel="RDF Options"),
    ] = None,
    sql_server_type: Annotated[
        Optional[str],
        typer.Option(
            help="[sql] The server type to determine the sql dialect. By default, it uses 'auto' to automatically detect the sql dialect via the specified servers in the data contract.",
            rich_help_panel="SQL Options",
        ),
    ] = "auto",
):
    result = DataContract(data_contract_str=str(file, encoding="utf-8"), server=server).export(
        export_format=export_format,
        model=model,
        rdf_base=rdf_base,
        sql_server_type=sql_server_type,
    )

    return result
