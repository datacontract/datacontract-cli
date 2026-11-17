import importlib.util
import sys
from types import ModuleType


def test_geometry_type_is_imported_as_object(monkeypatch):
    pyspark = ModuleType("pyspark")
    sql = ModuleType("pyspark.sql")
    types = ModuleType("pyspark.sql.types")
    data_type = type("DataType", (), {})
    geometry_type = type("GeometryType", (data_type,), {})

    sql.DataFrame = type("DataFrame", (), {})
    sql.SparkSession = type("SparkSession", (), {})
    sql.types = types
    types.DataType = data_type
    types.GeometryType = geometry_type
    pyspark.sql = sql
    monkeypatch.setitem(sys.modules, "pyspark", pyspark)
    monkeypatch.setitem(sys.modules, "pyspark.sql", sql)
    monkeypatch.setitem(sys.modules, "pyspark.sql.types", types)

    # loaded without registering it, so the copy bound to the fake pyspark never outlives the test
    spec = importlib.util.find_spec("datacontract.imports.spark_importer")
    spark_importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(spark_importer)

    assert spark_importer._data_type_from_spark(geometry_type()) == "object"
