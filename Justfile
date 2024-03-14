test:
    cd tests && pytest

format:
    black tests/ datacontract/

check:
    mypy datacontract/ tests/