CREATE TABLE public.customers (
    customer_id INT PRIMARY KEY
);

CREATE TABLE public.orders (
    order_id VARCHAR(36) PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES public.customers(customer_id),
    order_total NUMERIC(10, 2),
    line_count INT NOT NULL,
    ordered_at TIMESTAMPTZ,
    payload JSONB
);

COMMENT ON TABLE public.orders IS 'All orders';
COMMENT ON COLUMN public.orders.order_id IS 'The order id';

INSERT INTO public.customers (customer_id) VALUES
    (1);

INSERT INTO public.orders (order_id, customer_id, order_total, line_count, ordered_at, payload) VALUES
    ('CX-263-DU', 1, 50.00, 2, '2023-06-16 13:12:56', '{"channel": "web"}'),
    ('IK-894-MN', 1, 47.50, 1, '2023-10-08 22:40:57', '{"channel": "app"}');

CREATE VIEW public.open_orders AS
    SELECT order_id FROM public.orders WHERE line_count > 1;

CREATE SCHEMA select_only_keys;

CREATE TABLE select_only_keys.simple_target (
    target_id INT PRIMARY KEY
);

CREATE TABLE select_only_keys.simple_source (
    source_id INT PRIMARY KEY,
    target_id INT NOT NULL REFERENCES select_only_keys.simple_target(target_id)
);

CREATE TABLE select_only_keys.composite_target (
    first_id INT NOT NULL,
    second_id INT NOT NULL,
    PRIMARY KEY (first_id, second_id)
);

CREATE TABLE select_only_keys.composite_source (
    source_second_id INT NOT NULL,
    source_first_id INT NOT NULL,
    PRIMARY KEY (source_second_id, source_first_id),
    FOREIGN KEY (source_first_id, source_second_id)
        REFERENCES select_only_keys.composite_target(first_id, second_id)
);

CREATE ROLE select_only_key_reader LOGIN PASSWORD 'select-only-key-reader-password';
GRANT USAGE ON SCHEMA select_only_keys TO select_only_key_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA select_only_keys TO select_only_key_reader;

CREATE SCHEMA key_visibility;
CREATE SCHEMA key_visibility_other;

CREATE TABLE key_visibility.selected_target (
    target_id INT PRIMARY KEY
);

CREATE TABLE key_visibility.selected_source (
    source_id INT PRIMARY KEY,
    target_id INT NOT NULL REFERENCES key_visibility.selected_target(target_id)
);

CREATE TABLE key_visibility.composite_target (
    first_id INT NOT NULL,
    second_id INT NOT NULL,
    PRIMARY KEY (first_id, second_id)
);

CREATE TABLE key_visibility.composite_source (
    source_id INT PRIMARY KEY,
    source_first_id INT NOT NULL,
    source_second_id INT NOT NULL,
    FOREIGN KEY (source_first_id, source_second_id)
        REFERENCES key_visibility.composite_target(first_id, second_id)
);

CREATE TABLE key_visibility_other.cross_schema_target (
    target_id INT PRIMARY KEY
);

CREATE TABLE key_visibility.cross_schema_source (
    source_id INT PRIMARY KEY,
    target_id INT NOT NULL REFERENCES key_visibility_other.cross_schema_target(target_id)
);

CREATE TABLE key_visibility.same_named (
    local_second_id INT NOT NULL,
    local_first_id INT NOT NULL,
    PRIMARY KEY (local_second_id, local_first_id)
);

CREATE TABLE key_visibility_other.same_named (
    other_id INT PRIMARY KEY
);

CREATE TABLE key_visibility.partial_target (
    first_id INT NOT NULL,
    second_id INT NOT NULL,
    PRIMARY KEY (first_id, second_id)
);

CREATE TABLE key_visibility.partial_source (
    source_first_id INT NOT NULL,
    source_second_id INT NOT NULL,
    PRIMARY KEY (source_first_id, source_second_id),
    FOREIGN KEY (source_first_id, source_second_id)
        REFERENCES key_visibility.partial_target(first_id, second_id)
);

CREATE ROLE partial_key_reader LOGIN PASSWORD 'partial-key-reader-password';
GRANT USAGE ON SCHEMA key_visibility TO partial_key_reader;
GRANT SELECT (source_first_id) ON key_visibility.partial_source TO partial_key_reader;
GRANT SELECT (first_id) ON key_visibility.partial_target TO partial_key_reader;

CREATE TABLE key_visibility.column_reference_primary_key (
    first_id INT NOT NULL,
    second_id INT NOT NULL,
    PRIMARY KEY (second_id, first_id)
);

CREATE ROLE column_reference_key_reader LOGIN PASSWORD 'column-reference-key-reader-password';
GRANT USAGE ON SCHEMA key_visibility TO column_reference_key_reader;
GRANT SELECT ON key_visibility.column_reference_primary_key TO column_reference_key_reader;
GRANT REFERENCES (first_id) ON key_visibility.column_reference_primary_key TO column_reference_key_reader;
