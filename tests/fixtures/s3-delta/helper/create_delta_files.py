import os

import pandas as pd
from deltalake.writer import write_deltalake

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

# Write to Delta table files
write_deltalake(os.path.join(output_dir, "orders.delta"), orders_df)
