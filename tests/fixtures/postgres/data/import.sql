CREATE TABLE public.orders (
    order_id VARCHAR(36) PRIMARY KEY,
    order_total NUMERIC(10, 2),
    line_count INT NOT NULL,
    ordered_at TIMESTAMPTZ,
    payload JSONB
);

COMMENT ON TABLE public.orders IS 'All orders';
COMMENT ON COLUMN public.orders.order_id IS 'The order id';

INSERT INTO public.orders (order_id, order_total, line_count, ordered_at, payload) VALUES
    ('CX-263-DU', 50.00, 2, '2023-06-16 13:12:56', '{"channel": "web"}'),
    ('IK-894-MN', 47.50, 1, '2023-10-08 22:40:57', '{"channel": "app"}');

CREATE VIEW public.open_orders AS
    SELECT order_id FROM public.orders WHERE line_count > 1;
