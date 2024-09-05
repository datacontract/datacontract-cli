import os
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Ensure the required directory exists
output_dir = "../data"
os.makedirs(output_dir, exist_ok=True)


def write_parquet(df, file_name, schema=None):
    file_path = output_dir / Path(file_name)
    table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)
    pq.write_table(table, file_path)
    print(f"Written {file_path}")


# Define data for all supported types
supported_data_types = {
    "string": (["example", "test", "data"], pa.string()),
    "blob": ([b"example", b"test", b"data"], pa.binary()),
    "boolean": ([True, False, True], pa.bool_()),
    "decimal": ([Decimal("123.45"), Decimal("456.78"), Decimal("789.01")], pa.decimal128(10, 2)),
    "float": ([1.23, 4.56, 7.89], pa.float32()),
    "double": ([1.23, 4.56, 7.89], pa.float64()),
    "integer": ([100, 200, 300], pa.int32()),
    "bigint": ([1000000000000000000, 2000000000000000000, 3000000000000000000], pa.int64()),
    "struct": (
        [{"a": 1, "b": "test"}, {"a": 2, "b": "data"}, {"a": 3, "b": "example"}],
        pa.struct([pa.field("a", pa.int32()), pa.field("b", pa.string())]),
    ),
    "array": ([[1, 2, 3], [4, 5, 6], [7, 8, 9]], pa.list_(pa.int32())),
    "list": ([[1, 2, 3], [4, 5, 6], [7, 8, 9]], pa.list_(pa.int32())),
    "map": (
        [
            {"key1": "value1", "key2": "value2"},
            {"key1": "value3", "key2": "value4"},
            {"key1": "value5", "key2": "value6"},
        ],
        pa.map_(pa.string(), pa.string()),
    ),
    "date": (
        [pd.Timestamp("2024-01-01").date(), pd.Timestamp("2024-01-02").date(), pd.Timestamp("2024-01-03").date()],
        pa.date32(),
    ),
    "time": (
        [
            pd.Timestamp("2024-01-01 12:00:00").time(),
            pd.Timestamp("2024-01-02 12:00:00").time(),
            pd.Timestamp("2024-01-03 12:00:00").time(),
        ],
        pa.time32("s"),
    ),
    "timestamp": (
        [
            pd.Timestamp("2024-01-01 00:00:00", tz="UTC"),
            pd.Timestamp("2024-01-02 00:00:00", tz="UTC"),
            pd.Timestamp("2024-01-03 00:00:00", tz="UTC"),
        ],
        pa.timestamp("s", tz="UTC"),
    ),
}

# Write parquet files for supported data types
for type_name, (data, dtype) in supported_data_types.items():
    df = pd.DataFrame({f"{type_name}_field": data})
    schema = pa.schema([pa.field(f"{type_name}_field", dtype)])
    write_parquet(df, f"{type_name}.parquet", schema=schema)

# Write combined parquet file
combined_data = {f"{type_name}_field": data for type_name, (data, dtype) in supported_data_types.items()}
combined_schema = pa.schema(
    [pa.field(f"{type_name}_field", dtype) for type_name, (data, dtype) in supported_data_types.items()]
)
combined_df = pd.DataFrame(combined_data)
write_parquet(combined_df, "combined.parquet", schema=combined_schema)
