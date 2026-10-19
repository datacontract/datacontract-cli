import os
from decimal import Decimal

import pandas as pd
import pyarrow as pa
from deltalake import write_deltalake

# a timezone-aware timestamp (duckdb: TIMESTAMP WITH TIME ZONE), a decimal, and a list without a logicalType mapping
output_dir = "../data"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

events_df = pd.DataFrame(
    {
        "event_id": ["e1", "e2", "e3"],
        "event_time": pd.to_datetime(
            ["2024-01-01T10:00:00Z", "2024-01-01T11:30:00Z", "2024-01-02T08:20:00Z"], utc=True
        ),
        "amount": [Decimal("12.50"), Decimal("7.25"), Decimal("100.00")],
        "tags": [["new"], ["new", "vip"], []],
    }
)
schema = pa.schema(
    [
        ("event_id", pa.string()),
        ("event_time", pa.timestamp("us", tz="UTC")),
        ("amount", pa.decimal128(10, 2)),
        ("tags", pa.list_(pa.string())),
    ]
)

write_deltalake(os.path.join(output_dir, "events.delta"), pa.Table.from_pandas(events_df, schema=schema))
