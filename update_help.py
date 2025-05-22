import os
import re
import subprocess
from pathlib import Path

# File path to your markdown file
markdown_file_path = Path("README.md")

# List of commands to update
commands = [
    "init",
    "lint",
    "test",
    "export",
    "import",
    "publish",
    "catalog",
    "breaking",
    "changelog",
    "diff",
    "api",
]


def fetch_help(command: str) -> str:
    print(f"Fetching help text for command: {command}")
    env = {"COLUMNS": "100"}  # Set terminal width to 100 columns (or your preferred width)
    result = subprocess.run(
        ["datacontract", command, "--help"],
        capture_output=True,
        text=True,
        check=True,
        env={**env, **dict(os.environ)},  # Merge with existing environment variables
    )
    print(f"Help text fetched for command: {command}\n{result.stdout}")
    return result.stdout


# Function to update the markdown file
def update_markdown(file_path: Path, commands: list[str]) -> None:
    print(f"Reading markdown file from: {file_path}")
    content = file_path.read_text()

    for command in commands:
        print(f"Processing command: {command}")
        help_text = fetch_help(command)

        # Escape special characters for regex
        escaped_command = re.escape(command)
        print(f"Escaped command for regex: {escaped_command}")

        # Match the specific command section in the markdown
        pattern = rf"(?m)^###\s*{escaped_command}\s*\n```.*?```"
        print(f"Regex pattern for command: {pattern}")

        # Check if the pattern matches any part of the content
        if re.search(pattern, content, flags=re.DOTALL):
            print(f"Match found for command: {command}")
        else:
            print(f"No match found for command: {command}")

        # Replace the matched section with the updated help text
        updated_content = f"### {command}\n```\n{help_text}```"
        content = re.sub(pattern, updated_content, content, flags=re.DOTALL)

    print(f"Writing updated content back to file: {file_path}")
    file_path.write_text(content)


# Call the function to update the markdown
print("Starting markdown update process")
update_markdown(markdown_file_path, commands)
print("Markdown update process completed")
