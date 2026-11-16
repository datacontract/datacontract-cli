"""Vendor the Data Contract Editor assets and the HTML export's Markdown libraries into the CLI package.

Downloads the datacontract-editor npm package and extracts its dist/ files into
datacontract/editor_assets/, which `datacontract edit` serves locally so that
no CDN access is needed at runtime. Also downloads the latest marked and DOMPurify
into datacontract/templates/vendor/, which the HTML export and the catalog inline
to render Markdown. The files are committed to the repository and shipped with
the Python package.

Usage:
    python update_vendored_assets.py [version]

If no version is given, the latest datacontract-editor published to npm is used.
"""

import io
import shutil
import sys
import tarfile
from pathlib import Path

import requests

TARGET_DIR = Path(__file__).parent / "datacontract" / "editor_assets"
TARBALL_PREFIX = "package/dist/"
VENDOR_DIR = Path(__file__).parent / "datacontract" / "templates" / "vendor"
MARKDOWN_LIBRARIES = {  # npm package: {file in its tarball: file in VENDOR_DIR}
    "marked": {"package/lib/marked.umd.js": "marked.umd.js", "package/LICENSE": "marked.LICENSE"},
    "dompurify": {"package/dist/purify.min.js": "purify.min.js", "package/LICENSE": "purify.LICENSE"},
}


def download(package: str, version: str | None = None) -> tuple[str, tarfile.TarFile]:
    if version is None:
        response = requests.get(f"https://registry.npmjs.org/{package}/latest", timeout=30)
        response.raise_for_status()
        version = response.json()["version"]

    tarball_url = f"https://registry.npmjs.org/{package}/-/{package}-{version}.tgz"
    print(f"Downloading {tarball_url}")
    response = requests.get(tarball_url, timeout=60)
    response.raise_for_status()
    return version, tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz")


def main():
    version, tar = download("datacontract-editor", sys.argv[1] if len(sys.argv) > 1 else None)

    if TARGET_DIR.exists():
        shutil.rmtree(TARGET_DIR)
    TARGET_DIR.mkdir(parents=True)

    count = 0
    with tar:
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

    if VENDOR_DIR.exists():
        shutil.rmtree(VENDOR_DIR)
    VENDOR_DIR.mkdir(parents=True)
    for package, files in MARKDOWN_LIBRARIES.items():
        version, tar = download(package)
        with tar:
            for source, target in files.items():
                (VENDOR_DIR / target).write_bytes(tar.extractfile(source).read())
        print(f"Vendored {package} {version} into {VENDOR_DIR}")


if __name__ == "__main__":
    main()
