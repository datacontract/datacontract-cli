"""Vendor the official ODCS Excel template into the CLI package.

Downloads odcs-template.xlsx from the Open Data Contract Standard Excel Template
repository into datacontract/templates/excel/, which `datacontract export excel`
uses by default so that no network access is needed at runtime. The file is
committed to the repository and shipped with the Python package.

Usage:
    python update_excel_template.py [url]

If no URL is given, the template on the main branch is used.
"""

import sys
from pathlib import Path

import requests

ODCS_EXCEL_TEMPLATE_URL = (
    "https://github.com/datacontract/open-data-contract-standard-excel-template/raw/refs/heads/main/odcs-template.xlsx"
)
TARGET_FILE = Path(__file__).parent / "datacontract" / "templates" / "excel" / "odcs-template.xlsx"


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else ODCS_EXCEL_TEMPLATE_URL

    print(f"Downloading {url}")
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    TARGET_FILE.parent.mkdir(parents=True, exist_ok=True)
    TARGET_FILE.write_bytes(response.content)
    print(f"Vendored {len(response.content)} bytes into {TARGET_FILE}")


if __name__ == "__main__":
    main()
