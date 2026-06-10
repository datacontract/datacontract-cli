"""Vendor the Data Contract Editor assets into the CLI package.

Downloads the datacontract-editor npm package and extracts its dist/ files into
datacontract/editor_assets/, which `datacontract edit` serves locally so that
no CDN access is needed at runtime. The files are committed to the repository
and shipped with the Python package.

Usage:
    python update_editor_assets.py [version]

If no version is given, the latest version published to npm is used.
"""

import io
import shutil
import sys
import tarfile
from pathlib import Path

import requests

TARGET_DIR = Path(__file__).parent / "datacontract" / "editor_assets"
TARBALL_PREFIX = "package/dist/"


def main():
    if len(sys.argv) > 1:
        version = sys.argv[1]
    else:
        response = requests.get("https://registry.npmjs.org/datacontract-editor/latest", timeout=30)
        response.raise_for_status()
        version = response.json()["version"]

    tarball_url = f"https://registry.npmjs.org/datacontract-editor/-/datacontract-editor-{version}.tgz"
    print(f"Downloading {tarball_url}")
    response = requests.get(tarball_url, timeout=60)
    response.raise_for_status()

    if TARGET_DIR.exists():
        shutil.rmtree(TARGET_DIR)
    TARGET_DIR.mkdir(parents=True)

    count = 0
    with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile() or not member.name.startswith(TARBALL_PREFIX):
                continue
            target = (TARGET_DIR / member.name[len(TARBALL_PREFIX) :]).resolve()
            if not target.is_relative_to(TARGET_DIR.resolve()):
                raise ValueError(f"Refusing to extract outside target directory: {member.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(tar.extractfile(member).read())
            count += 1

    (TARGET_DIR / "VERSION").write_text(version + "\n", encoding="utf-8")
    print(f"Vendored {count} files of datacontract-editor {version} into {TARGET_DIR}")


if __name__ == "__main__":
    main()
