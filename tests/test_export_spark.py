import subprocess
import sys
import textwrap
from types import ModuleType

import pytest
from datacontract_specification.model import DataContractSpecification
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.spark_exporter import SparkDataType, to_pyspark, to_spark
from datacontract.imports.dcs_importer import convert_dcs_to_odcs

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["export", "spark", "./fixtures/spark/export/datacontract.yaml"],
    )
    assert result.exit_code == 0
    assert result.output == expected_str


def test_export_does_not_need_pyspark():
    """The export renders the schema as source code, so requiring pyspark to produce
    that text would make a JVM a prerequisite of a string operation. Run it in a
    subprocess where importing pyspark raises, because this process has it loaded."""
    script = textwrap.dedent("""
        import sys

        class Blocker:
            def find_spec(self, name, path=None, target=None):
                if name == "pyspark" or name.startswith("pyspark."):
                    raise ImportError(f"pyspark is not installed: {name}")
                return None

        sys.meta_path.insert(0, Blocker())

        from typer.testing import CliRunner
        from datacontract.cli import app

        result = CliRunner().invoke(app, ["export", "spark", "./fixtures/spark/export/datacontract.yaml"])
        if result.exit_code != 0:
            raise SystemExit(result.output)
        sys.stdout.write(result.output)
    """)

    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == expected_str


def test_to_spark_schema():
    dcs = DataContractSpecification.from_file("fixtures/spark/export/datacontract.yaml")
    data_contract = convert_dcs_to_odcs(dcs)

    # the trailing newline in expected_str is the one the CLI prints
    assert to_spark(data_contract) == expected_str.rstrip("\n")


def _stub_pyspark(monkeypatch, version: str, *type_names: str):
    """Stand in for an installed PySpark that has only `type_names`.

    Stubbed rather than installed: PySpark is not a dependency of this project any
    more, and what is under test is what we do when a type is absent from it.
    """
    pyspark = ModuleType("pyspark")
    pyspark.__version__ = version
    sql = ModuleType("pyspark.sql")
    types = ModuleType("pyspark.sql.types")
    for name in type_names:
        setattr(types, name, lambda name=name: f"<{name}>")
    sql.types = types
    pyspark.sql = sql
    for name, module in [("pyspark", pyspark), ("pyspark.sql", sql), ("pyspark.sql.types", types)]:
        monkeypatch.setitem(sys.modules, name, module)


def test_a_type_missing_from_the_installed_pyspark_is_reported(monkeypatch):
    """VariantType only exists from PySpark 4.0 on. A bare AttributeError on the types
    module would name neither the version that is installed nor the way around it."""
    _stub_pyspark(monkeypatch, "3.5.8", "StringType")

    with pytest.raises(RuntimeError) as excinfo:
        to_pyspark(SparkDataType("VariantType"))

    assert "PySpark 3.5.8 has no VariantType" in str(excinfo.value)
    assert "datacontract export spark" in str(excinfo.value)


def test_a_type_the_installed_pyspark_has_is_built(monkeypatch):
    _stub_pyspark(monkeypatch, "3.5.8", "StringType")

    assert to_pyspark(SparkDataType("StringType")) == "<StringType>"


expected_str = """orders = StructType([
    StructField("orderdate",
        DateType(),
        True
    ),
    StructField("order_timestamp",
        TimestampType(),
        True
    ),
    StructField("delivery_timestamp",
        TimestampNTZType(),
        True
    ),
    StructField("orderid",
        IntegerType(),
        True
    ),
    StructField("item_list",
        ArrayType(StructType([
            StructField("itemid",
                StringType(),
                True
            ),
            StructField("quantity",
                IntegerType(),
                True
            )
        ])),
        True
    ),
    StructField("orderunits",
        DoubleType(),
        True
    ),
    StructField("tags",
        ArrayType(StringType()),
        True
    ),
    StructField("address",
        StructType([
            StructField("city",
                StringType(),
                False
            ),
            StructField("state",
                StringType(),
                True
            ),
            StructField("zipcode",
                LongType(),
                True
            )
        ]),
        True
    )
])

customers = StructType([
    StructField("id",
        IntegerType(),
        True
    ),
    StructField("name",
        StringType(),
        True,
        {"comment": "First and last name of the customer"}
    ),
    StructField("metadata",
        MapType(
            StringType(), StructType([
            StructField("value",
                StringType(),
                True
            ),
            StructField("type",
                StringType(),
                True
            ),
            StructField("timestamp",
                LongType(),
                True
            ),
            StructField("source",
                StringType(),
                True
            )
        ])),
        True
    )
])
"""
