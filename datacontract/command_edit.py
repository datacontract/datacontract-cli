import json
import mimetypes
import os
import webbrowser
from importlib import metadata
from pathlib import Path
from urllib.parse import quote

import typer
from typing_extensions import Annotated

from datacontract.cli import app, console, debug_option, enable_debug_logging
from datacontract.init.init_template import get_init_template

EDITOR_ASSETS_URL_TEMPLATE = "https://cdn.jsdelivr.net/npm/datacontract-editor@{version}/dist"

# The Data Contract Editor assets are bundled with the package (vendored from the
# datacontract-editor npm package via update_editor_assets.py), so the editor
# works offline without any CDN access.
BUNDLED_EDITOR_ASSETS_DIR = Path(__file__).parent / "editor_assets"

# Editor assets are always served from this server (from the bundled files, or
# proxied when a CDN version/URL override is given), because browsers refuse to
# construct Monaco's web workers from a cross-origin URL.
EDITOR_ASSETS_PATH = "/editor"


def resolve_editor_assets_url(editor_version: str | None, editor_assets_url: str | None) -> str | None:
    """Return the remote URL to load the editor assets from, or None to use the bundled assets."""
    if editor_assets_url is not None:
        return editor_assets_url
    if editor_version is not None:
        return EDITOR_ASSETS_URL_TEMPLATE.format(version=quote(editor_version))
    return None


def _cli_version() -> str:
    try:
        return metadata.version("datacontract-cli")
    except metadata.PackageNotFoundError:
        return "unknown"


def _generate_index_html(filename: str) -> str:
    """
    Generate the editor page, mirroring the CLI mode of the datacontract-editor npm launcher:
    load the YAML from the local file API, write it back on save, and point the
    editor's test runner at this server's own /test endpoint.
    """
    filename_js = json.dumps(filename)
    file_api_path = f"/api/files/{quote(filename)}"
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{filename} - Data Contract Editor</title>
    <link rel="icon" type="image/svg+xml" href="{EDITOR_ASSETS_PATH}/logo_fuchsia_v2.svg" />
    <link href="{EDITOR_ASSETS_PATH}/datacontract-editor.css" rel="stylesheet">
    <style>
      html, body {{ height: 100%; margin: 0; }}
      #root {{ height: 100%; width: 100%; }}
    </style>
  </head>
  <body>
    <div id="root"></div>
    <script type="module">
      import {{ init }} from '{EDITOR_ASSETS_PATH}/datacontract-editor.es.js';

      async function initCli() {{
        try {{
          const response = await fetch('{file_api_path}');
          if (!response.ok) {{
            throw new Error('Failed to load file: ' + response.statusText);
          }}
          const yaml = await response.text();

          const notify = (notification) => editor?.getStore().getState().addNotification(notification);

          const editor = init({{
            container: '#root',
            mode: 'CLI',
            yaml: yaml,
            persistence: 'none',
            initialView: 'form',
            tests: {{
              enabled: true,
              dataContractCliApiServerUrl: window.location.origin,
            }},
            onSave: async (yamlContent) => {{
              try {{
                const saveResponse = await fetch('{file_api_path}', {{
                  method: 'PUT',
                  headers: {{ 'Content-Type': 'text/yaml' }},
                  body: yamlContent,
                }});
                if (!saveResponse.ok) {{
                  throw new Error('Failed to save file');
                }}
                notify({{ type: 'success', message: 'Saved ' + {filename_js} }});
              }} catch (error) {{
                notify({{ type: 'error', message: 'Failed to save ' + {filename_js} + ': ' + error.message, duration: 5000 }});
                throw error;
              }}
            }},
          }});
        }} catch (error) {{
          console.error('Failed to initialize editor:', error);
          document.getElementById('root').innerText = 'Failed to load ' + {filename_js} + ': ' + error.message;
        }}
      }}

      initCli();
    </script>
  </body>
</html>
"""


def create_app(
    file_path: Path,
    editor_assets_url: str | None = None,
    editor_assets_dir: Path = BUNDLED_EDITOR_ASSETS_DIR,
    open_browser_url: str | None = None,
):
    """
    Create the FastAPI app serving the Data Contract Editor for a single local file.

    The editor assets are served from editor_assets_dir (the bundled files by default),
    unless editor_assets_url is given, in which case they are proxied from that URL.
    """
    from contextlib import asynccontextmanager

    import requests
    from fastapi import FastAPI, HTTPException, Request, Response, status
    from fastapi.responses import HTMLResponse, PlainTextResponse

    from datacontract.api import test as api_test

    filename = file_path.name
    if editor_assets_url is not None:
        editor_assets_url = editor_assets_url.rstrip("/")
    asset_cache: dict[str, tuple[bytes, str]] = {}

    @asynccontextmanager
    async def lifespan(_app):
        if open_browser_url:
            webbrowser.open(open_browser_url)
        yield

    edit_app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)

    @edit_app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index():
        return _generate_index_html(filename)

    @edit_app.get(EDITOR_ASSETS_PATH + "/{asset_path:path}", include_in_schema=False)
    def editor_asset(asset_path: str):
        if ".." in asset_path or asset_path.startswith("/"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        if editor_assets_url is None:
            assets_root = os.path.realpath(editor_assets_dir)
            asset_file = os.path.realpath(os.path.join(assets_root, asset_path))
            # the canonical path must stay within the assets directory
            if not asset_file.startswith(assets_root + os.sep):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
            if not os.path.isfile(asset_file):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Editor asset not found: {asset_path}",
                )
            content_type = mimetypes.guess_type(asset_file)[0] or "application/octet-stream"
            with open(asset_file, "rb") as f:
                return Response(content=f.read(), media_type=content_type)
        cached = asset_cache.get(asset_path)
        if cached is None:
            upstream_url = f"{editor_assets_url}/{asset_path}"
            try:
                upstream = requests.get(upstream_url, timeout=30)
            except requests.RequestException as e:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to load editor asset from {upstream_url}: {e}",
                )
            if upstream.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Editor asset not found at {upstream_url} (status {upstream.status_code})",
                )
            content_type = upstream.headers.get("content-type", "application/octet-stream")
            cached = (upstream.content, content_type)
            asset_cache[asset_path] = cached
        content, content_type = cached
        return Response(content=content, media_type=content_type)

    @edit_app.get("/api/health")
    def health():
        return {"status": "ok", "version": _cli_version()}

    @edit_app.get("/api/config")
    def config():
        return {"mode": "CLI", "filename": filename, "filepath": str(file_path)}

    def check_filename(requested_filename: str):
        # Only the file passed to `datacontract edit` is accessible.
        if requested_filename != filename:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Only the specified target file can be accessed.",
            )

    @edit_app.get("/api/files/{requested_filename}")
    def read_file(requested_filename: str):
        check_filename(requested_filename)
        return PlainTextResponse(file_path.read_text(encoding="utf-8"), media_type="text/yaml")

    @edit_app.put("/api/files/{requested_filename}")
    async def write_file(requested_filename: str, request: Request):
        check_filename(requested_filename)
        content = (await request.body()).decode("utf-8")
        file_path.write_text(content, encoding="utf-8")
        console.print(f"Saved: {file_path}")
        return {"success": True, "filename": filename}

    # The editor's "Run test" posts the contract YAML to <origin>/test,
    # so this server doubles as the test runner by reusing the API endpoint.
    edit_app.post("/test", response_model_exclude_none=True, response_model_exclude_unset=True)(api_test)

    return edit_app


@app.command(
    name="edit",
    epilog="Example: datacontract edit datacontract.yaml",
)
def edit(
    location: Annotated[
        str,
        typer.Argument(
            help="The path of the data contract yaml to edit. "
            "If the file does not exist, you are asked whether to initialize a new data contract."
        ),
    ] = "datacontract.yaml",
    port: Annotated[int, typer.Option(help="Bind socket to this port.")] = 4243,
    host: Annotated[
        str, typer.Option(help="Bind socket to this host. Hint: For running in docker, set it to 0.0.0.0")
    ] = "127.0.0.1",
    editor_version: Annotated[
        str | None,
        typer.Option(
            help="Version of the datacontract-editor npm package to load from the CDN, e.g. '0.1.9' or 'latest'. "
            "By default, the editor version bundled with the CLI is used (works offline)."
        ),
    ] = None,
    editor_assets_url: Annotated[
        str | None,
        typer.Option(
            help="Base URL to load the Data Contract Editor assets (JS/CSS) from, "
            "e.g. a self-hosted editor build. Takes precedence over --editor-version."
        ),
    ] = None,
    open_browser: Annotated[
        bool, typer.Option("--open/--no-open", help="Open the editor in the default browser.")
    ] = True,
    debug: debug_option = None,
):
    """
    Edit a data contract file in the Data Contract Editor (web UI).

    Starts a local web server that opens the Data Contract Editor for the given file.
    The editor is bundled with the CLI, so no internet access is required.
    Saving in the editor writes directly back to the local file.
    The server also acts as the editor's test runner: "Run test" in the editor executes
    the data contract tests locally against the servers defined in the data contract.
    Credentials for the data sources must be provided as environment variables, see
    https://cli.datacontract.com/#test
    """
    enable_debug_logging(debug)

    try:
        import uvicorn
    except ImportError:
        console.print("[red]Install the extra datacontract-cli\\[api] to use edit.[/red]")
        raise typer.Exit(code=1)

    file_path = Path(location).resolve()
    if file_path.suffix not in (".yaml", ".yml"):
        console.print("[red]Error: File must be a YAML file (.yaml or .yml).[/red]")
        raise typer.Exit(code=1)
    if not file_path.exists():
        if not typer.confirm(f"File '{location}' does not exist. Initialize a new data contract?"):
            console.print(f"Aborted. Use `datacontract init {location}` to create the file.")
            raise typer.Exit(code=1)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(get_init_template(), encoding="utf-8")
        console.print(f"📄 data contract written to {location}")

    url = f"http://{'localhost' if host == '127.0.0.1' else host}:{port}"
    console.print(f"Editing: {file_path}")
    console.print(f"Data Contract Editor running at {url}")
    console.print("Press Ctrl+C to stop")

    assets_url = resolve_editor_assets_url(editor_version, editor_assets_url)
    if assets_url is None and not BUNDLED_EDITOR_ASSETS_DIR.is_dir():
        console.print(
            "[red]Error: Bundled editor assets not found in this installation. "
            "Use --editor-version latest to load the editor from the CDN instead.[/red]"
        )
        raise typer.Exit(code=1)

    edit_app = create_app(
        file_path,
        editor_assets_url=assets_url,
        open_browser_url=url if open_browser else None,
    )
    uvicorn.run(edit_app, port=port, host=host, log_level="warning")
