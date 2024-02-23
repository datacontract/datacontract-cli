import logging

from typer.testing import CliRunner

from datacontract.cli import app

runner = CliRunner()

logging.basicConfig(level=logging.DEBUG, force=True)


def test_field_removed():
    result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-v1.yaml",
                                 "./examples/breaking/datacontract-v2.yaml"])
    assert result.exit_code == 1
    assert result.stdout == r"""1 breaking changes: 1 error, 0 warning
error   [field-removed] at ./examples/breaking/datacontract-v2.yaml
        in model my_table
            removed the field updated_at
"""
