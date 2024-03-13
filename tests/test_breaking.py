import logging

import pytest
from typer.testing import CliRunner

from datacontract.cli import app

runner = CliRunner()

logging.basicConfig(level=logging.DEBUG, force=True)


def test_no_breaking_changes():
    result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-fields-v2.yaml",
                                 "./examples/breaking/datacontract-fields-v2.yaml"])
    assert result.exit_code == 0
    assert "0 breaking changes: 0 error, 0 warning\n" in result.stdout


def test_quality_added():
    result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-quality-v1.yaml",
                                 "./examples/breaking/datacontract-quality-v2.yaml"])
    assert result.exit_code == 0
    assert "0 breaking changes: 0 error, 0 warning\n" in result.stdout


def test_quality_removed():
    result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-quality-v2.yaml",
                                 "./examples/breaking/datacontract-quality-v1.yaml"])
    assert result.exit_code == 0
    assert "1 breaking changes: 0 error, 1 warning\n" in result.stdout


def test_quality_updated():
    result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-quality-v2.yaml",
                                 "./examples/breaking/datacontract-quality-v3.yaml"])
    assert result.exit_code == 0
    assert "2 breaking changes: 0 error, 2 warning\n" in result.stdout


class TestModelsAdded:

    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-models-v1.yaml",
                                     "./examples/breaking/datacontract-models-v2.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 0

    def test_headline(self, output):
        assert "0 breaking changes: 0 error, 0 warning\n" in output

    def test_infos_not_in_output(self, output):
        assert "model_added" not in output
        assert "model_description_added" not in output


class TestModelsRemoved:

    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-models-v2.yaml",
                                     "./examples/breaking/datacontract-models-v1.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 1

    def test_headline(self, output):
        assert "1 breaking changes: 1 error, 0 warning\n" in output

    def test_infos_not_in_output(self, output):
        assert "model_description_removed" not in output


class TestModelsUpdated:

    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-models-v2.yaml",
                                     "./examples/breaking/datacontract-models-v3.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 1

    def test_headline(self, output):
        assert "1 breaking changes: 1 error, 0 warning\n" in output

    def test_infos_not_in_output(self, output):
        assert "model_description_updated" not in output


class TestFieldsAdded:

    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-fields-v1.yaml",
                                     "./examples/breaking/datacontract-fields-v2.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 0

    def test_headline(self, output):
        assert "14 breaking changes: 0 error, 14 warning\n" in output

    def test_infos_not_in_output(self, output):
        assert "field_added" not in output
        assert "field_description_added" not in output
        assert "field_tags_added" not in output


class TestFieldsRemoved:
    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-fields-v2.yaml",
                                     "./examples/breaking/datacontract-fields-v1.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 1

    def test_headline(self, output):
        assert "15 breaking changes: 5 error, 10 warning\n" in output

    def test_infos_not_in_output(self, output):
        assert "field_description_removed" not in output
        assert "field_enum_removed" not in output
        assert "field_tags_removed" not in output


class TestFieldsUpdated:

    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-fields-v2.yaml",
                                     "./examples/breaking/datacontract-fields-v3.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 1

    def test_headline(self, output):
        assert "18 breaking changes: 15 error, 3 warning\n" in output

    def test_infos_not_in_output(self, output):
        assert "field_description_updated" not in output
        assert "field_tags_updated" not in output


class TestDefinitionAdded:

    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-definitions-v1.yaml",
                                     "./examples/breaking/datacontract-definitions-v2.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 0

    def test_headline(self, output):
        assert "13 breaking changes: 0 error, 13 warning\n" in output

    def test_infos_not_in_output(self, output):
        assert "field_description_added" not in output
        assert "field_tags_added" not in output


class TestDefinitionRemoved:

    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-definitions-v2.yaml",
                                     "./examples/breaking/datacontract-definitions-v1.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 1

    def test_headline(self, output):
        assert "12 breaking changes: 3 error, 9 warning\n" in output

    def test_infos_not_in_output(self, output):
        assert "field_description_removed" not in output
        assert "field_tags_removed" not in output
        assert "field_enum_removed" not in output


class TestDefinitionUpdated:

    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-definitions-v2.yaml",
                                     "./examples/breaking/datacontract-definitions-v3.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 1

    def test_headline(self, output):
        assert "13 breaking changes: 12 error, 1 warning\n" in output

    def test_infos_not_in_output(self, output):
        assert "field_description_updated" not in output
        assert "field_tags_updated" not in output
