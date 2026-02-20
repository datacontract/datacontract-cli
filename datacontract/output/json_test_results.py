from pathlib import Path

from datacontract.model.run import Run


def write_json_test_results(run: Run, output_path: Path):
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        if not output_path.parent.is_dir():
            raise
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(run.model_dump_json(indent=2))
