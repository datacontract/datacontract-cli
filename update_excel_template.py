"""Vendor the official ODCS Excel template and its conformance pair into the CLI.

Downloads from the Open Data Contract Standard Excel Template repository:
- odcs-template.xlsx into datacontract/templates/excel/, which `datacontract export excel` uses by
  default so that no network access is needed at runtime (committed and shipped with the package)
- the examples/*.xlsx and examples/*.yaml conformance pairs into tests/fixtures/excel/, the
  workbooks + expected YAML the Excel tests assert against

Usage:
    python update_excel_template.py [base-url]
    python update_excel_template.py --check    # exit 1 when the vendored files differ from the repository

If no base URL is given, the main branch is used.
"""

import sys
from pathlib import Path

import requests

ODCS_EXCEL_TEMPLATE_BASE_URL = (
    "https://github.com/datacontract/open-data-contract-standard-excel-template/raw/refs/heads/main"
)
ROOT = Path(__file__).parent
FILES = {
    "odcs-template.xlsx": ROOT / "datacontract" / "templates" / "excel" / "odcs-template.xlsx",
    "examples/shipments-odcs.xlsx": ROOT / "tests" / "fixtures" / "excel" / "shipments-odcs.xlsx",
    "examples/shipments-odcs.yaml": ROOT / "tests" / "fixtures" / "excel" / "shipments-odcs.yaml",
    "examples/full-odcs-3.2.xlsx": ROOT / "tests" / "fixtures" / "excel" / "full-odcs-3.2.xlsx",
    "examples/full-odcs-3.2.yaml": ROOT / "tests" / "fixtures" / "excel" / "full-odcs-3.2.yaml",
}


def main() -> int:
    args = [arg for arg in sys.argv[1:] if arg != "--check"]
    check = "--check" in sys.argv
    base_url = (args[0] if args else ODCS_EXCEL_TEMPLATE_BASE_URL).rstrip("/")

    stale = []
    for name, target in FILES.items():
        url = f"{base_url}/{name}"
        print(f"Downloading {url}")
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        if check:
            if not target.exists() or target.read_bytes() != response.content:
                stale.append(str(target.relative_to(ROOT)))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(response.content)
        print(f"Vendored {len(response.content)} bytes into {target}")

    if stale:
        print("Vendored copies differ from the template repository: " + ", ".join(stale))
        print("Run: python update_excel_template.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
