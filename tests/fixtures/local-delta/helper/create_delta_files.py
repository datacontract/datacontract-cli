import os

import pandas as pd
from deltalake import write_deltalake

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
    "order_id": [1001, 1001, 1002, 1004, 1004, 1005, 1005, 1006, 1006, 1007, 1008, 1008],
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
write_deltalake("data/orders", orders_df)
write_deltalake("data/line_items", line_items_df)
# Write to Parquet files
# orders_df.to_parquet(os.path.join(output_dir, "orders.parquet"))
# line_items_df.to_parquet(os.path.join(output_dir, "line_items.parquet"))
