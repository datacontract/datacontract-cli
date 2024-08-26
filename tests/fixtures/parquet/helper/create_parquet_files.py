import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
import os
import uuid

# Ensure the required directory exists
output_dir = "../data"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Sample data for Orders table
orders_data = {
    "order_id": ["1001", "1002", "1003", "1004", "1005", "1006", "1007", "1008"],
    "order_timestamp": [
        "2024-01-01T10:00:00.000Z",
        "2024-01-01T11:30:00.000Z",
        "2024-01-01T12:45:00.000Z",
        "2024-01-02T08:20:00.000Z",
        "2024-01-02T09:15:00.000Z",
        "2024-01-02T10:05:00.000Z",
        "2024-01-02T10:45:00.000Z",
        "2024-01-02T11:30:00.000Z",
    ],
    "order_total": [5000, 7500, 3000, 2000, 6500, 12000, 4500, 8000],
}

orders_df = pd.DataFrame(orders_data)
orders_df["order_timestamp"] = pd.to_datetime(orders_df["order_timestamp"], format="%Y-%m-%dT%H:%M:%S.%fZ")

# Sample data for Line Items table
line_items_data = {
    "line_item_id": [
        "LI-001",
        "LI-002",
        "LI-003",
        "LI-004",
        "LI-005",
        "LI-006",
        "LI-007",
        "LI-008",
        "LI-009",
        "LI-010",
        "LI-011",
        "LI-012",
    ],
    "order_id": ["1001", "1001", "1002", "1004", "1004", "1005", "1005", "1006", "1006", "1007", "1008", "1008"],
    "sku": [
        "SKU-12345",
        "SKU-12346",
        "SKU-12347",
        "SKU-12348",
        "SKU-12349",
        "SKU-12350",
        "SKU-12351",
        "SKU-12352",
        "SKU-12353",
        "SKU-12354",
        "SKU-12355",
        "SKU-12356",
    ],
}
line_items_df = pd.DataFrame(line_items_data)

# Write to Parquet files
orders_df.to_parquet(os.path.join(output_dir, "orders.parquet"))
line_items_df.to_parquet(os.path.join(output_dir, "line_items.parquet"))

# Define additional data for various types
data = {
    "string": pa.array(["example", "test", "data"], pa.string()),
"date": pa.array([pd.Timestamp('2024-01-01').date()], pa.date32()),
"time": pa.array([pd.Timestamp('2024-01-01 12:00:00').time()], pa.time32('s')),
"float": pa.array([1.23, 4.56, 7.89], pa.float32()),
"double": pa.array([1.23, 4.56, 7.89], pa.float64()),
"integer": pa.array([100, 200, 300], pa.int32()),
"bigint": pa.array([1000000000000000000, 2000000000000000000, 3000000000000000000], pa.int64()),
"smallint": pa.array([10, 20, 30], pa.int16()),
"tinyint": pa.array([1, 2, 3], pa.int8()),
"ubigint": pa.array([1000000000000000000, 2000000000000000000, 3000000000000000000], pa.uint64()),
"uhugeint": pa.array([100000, 200000, 300000], pa.uint64()),
"uinteger": pa.array([100, 200, 300], pa.uint32()),
"usmallint": pa.array([10, 20, 30], pa.uint16()),
"utinyint": pa.array([1, 2, 3], pa.uint8()),
"boolean": pa.array([True, False, True], pa.bool_()),
"blob": pa.array([b"example", b"test", b"data"], pa.binary()),
"bit": pa.array([b"1010", b"1100", b"1111"], pa.binary()),
"interval": pa.array([pd.Timedelta(seconds=3600)], pa.duration('s')),
"uuid": pa.array([uuid.uuid4().bytes], pa.binary(16)),
"hugeint": pa.array([1000000000000000000, 2000000000000000000, 3000000000000000000], pa.int64()),
"struct": pa.array([{"a": 1, "b": "test"}], pa.struct([("a", pa.int32()), ("b", pa.string())])),
"array": pa.array([[1, 2, 3], [4, 5, 6]], pa.list_(pa.int32())),
"list": pa.array([[1, 2, 3], [4, 5, 6]], pa.list_(pa.int32())),
"map": pa.array([{"key1": "value1", "key2": "value2"}], pa.map_(pa.string(), pa.string()))
}

# Write additional Parquet files
for type_name, array in data.items():
    table = pa.Table.from_arrays([array], [type_name])
    pq.write_table(table, os.path.join(output_dir, f"{type_name}.parquet"))