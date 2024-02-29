from typing import Annotated

from fastapi import FastAPI, File, UploadFile

from datacontract.data_contract import DataContract

app = FastAPI()


@app.post("/lint")
def lint(file: Annotated[bytes, File()]):
    data_contract = DataContract(data_contract_str=str(file, encoding="utf-8"))
    lint_result = data_contract.lint()
    return {
        "result": lint_result.result,
        "checks": lint_result.checks
    }
