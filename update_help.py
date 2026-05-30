import os
import re
import subprocess
from pathlib import Path

markdown_file_path = Path("README.md")


def fetch_help(command_path: list[str]) -> str:
    label = " ".join(command_path) or "<root>"
    print(f"Fetching help text for command: {label}")
    env = {"COLUMNS": "100"}
    result = subprocess.run(
        ["datacontract", *command_path, "--help"],
        capture_output=True,
        text=True,
        check=True,
        env={**env, **dict(os.environ)},
    )
    print(f"Help text fetched for command: {label}\n{result.stdout}")
    return result.stdout.strip()


def discover_commands(readme: str, prefix: list[str] | None = None) -> list[list[str]]:
    """Walk `datacontract --help` and return command paths to document.

    Stops recursing once the README already has a `### <path>` heading — the README's
    existing granularity decides where each section ends (e.g. `### export` covers
    every format under `export`, but `### dbt sync` requires walking past `dbt`).
    """
    prefix = prefix or []
    if prefix and re.search(rf"(?m)^###\s*{re.escape(' '.join(prefix))}\s*$", readme):
        return [prefix]

    help_text = fetch_help(prefix)
    match = re.search(r"╭─+ Commands ─+╮\n(.*?)╰─+╯", help_text, flags=re.DOTALL)
    if not match:
        return [prefix] if prefix else []

    subcommands = []
    for line in match.group(1).splitlines():
        # Command rows start with "│ " + name; description continuations have more leading spaces.
        m = re.match(r"│ (\S+)\s", line)
        if m:
            subcommands.append(m.group(1))

    leaves = []
    for sub in subcommands:
        leaves.extend(discover_commands(readme, prefix + [sub]))
    return leaves


def update_markdown(file_path: Path, command_paths: list[list[str]]) -> None:
    print(f"Reading markdown file from: {file_path}")
    content = file_path.read_text()

    for command_path in command_paths:
        command = " ".join(command_path)
        print(f"Processing command: {command}")
        help_text = fetch_help(command_path)

        escaped_command = re.escape(command)
        pattern = rf"(?m)^###\s*{escaped_command}\s*\n```.*?```"
        print(f"Regex pattern for command: {pattern}")

        if re.search(pattern, content, flags=re.DOTALL):
            print(f"Match found for command: {command}")
        else:
            print(f"No match found for command: {command}")

        updated_content = f"### {command}\n```\n{help_text}\n```"
        content = re.sub(pattern, updated_content, content, flags=re.DOTALL)

    print(f"Writing updated content back to file: {file_path}")
    file_path.write_text(content)


print("Starting markdown update process")
commands = discover_commands(markdown_file_path.read_text())
print(f"Discovered commands: {[' '.join(c) for c in commands]}")
update_markdown(markdown_file_path, commands)
print("Markdown update process completed")
