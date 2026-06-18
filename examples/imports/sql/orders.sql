CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    order_timestamp TIMESTAMPTZ NOT NULL,
    customer_id TEXT NOT NULL,
    order_total NUMERIC NOT NULL,
    status TEXT NOT NULL
);
