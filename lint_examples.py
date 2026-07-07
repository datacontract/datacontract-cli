#!/usr/bin/env python3
"""Lint every example data contract under examples/.

Ensures all contracts referenced by the documentation stay valid ODCS.
Run it directly (`python lint_examples.py`) or via CI. Exits non-zero if any
example fails to lint.
"""

import sys
from pathlib import Path

from datacontract.data_contract import DataContract

EXAMPLES_DIR = Path(__file__).parent / "examples"


def main() -> int:
    contracts = sorted(EXAMPLES_DIR.rglob("*.odcs.yaml"))
    if not contracts:
        print(f"No example contracts found under {EXAMPLES_DIR}/")
        return 1

    failures = 0
    for contract in contracts:
        run = DataContract(data_contract_file=str(contract)).lint()
        rel = contract.relative_to(EXAMPLES_DIR.parent)
        if run.has_passed():
            print(f"PASS  {rel}")
        else:
            failures += 1
            print(f"FAIL  {rel}")
            for check in run.checks:
                if check.result != "passed":
                    print(f"        {check.name}: {check.reason}")

    total = len(contracts)
    print(f"\n{total - failures}/{total} example contracts valid.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
