CREATE TABLE public.orders
(
    order_id    varchar(20) PRIMARY KEY,
    order_total numeric     NOT NULL
);

INSERT INTO public.orders VALUES ('O-GOOD1', 10.0);
INSERT INTO public.orders VALUES ('O-GOOD2', 20.0);
INSERT INTO public.orders VALUES ('O-BAD123', -5.0);
