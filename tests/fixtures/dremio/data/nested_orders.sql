-- __TABLE__ is replaced by the path of the table, a folder below $scratch
-- order 2 has an item without a sku and an email without @; order 3 repeats a sku, repeats a discount
-- code within one item, has a negative discount, two disallowed tags and no email; orders 4 and 5 have no items.
-- Order 1 has the discount code X in two items, which is no repeat.
CREATE TABLE __TABLE__ AS
SELECT o.r.order_id AS order_id, o.r.items AS items, o.r.tags AS tags, o.r.customer AS customer
FROM (SELECT FLATTEN(CONVERT_FROM('[
  {"order_id": 1, "items": [{"sku": "A", "discounts": [{"code": "X", "amount": 1.5}]}, {"sku": "B", "discounts": [{"code": "X", "amount": 2.5}]}],
   "tags": ["new"], "customer": {"id": 1, "email": "a@example.com"}},
  {"order_id": 2, "items": [{"sku": null, "discounts": []}], "tags": ["vip"], "customer": {"id": 2, "email": "b.example.com"}},
  {"order_id": 3, "items": [{"sku": "C", "discounts": [{"code": "Y", "amount": -1.0}, {"code": "Y", "amount": 1.0}]}, {"sku": "C", "discounts": []}],
   "tags": ["bogus", "wrong"], "customer": {"id": 3, "email": null}},
  {"order_id": 4, "items": [], "tags": ["new"], "customer": {"id": 4, "email": "d@example.com"}},
  {"order_id": 5, "items": null, "tags": null, "customer": {"id": 5, "email": "e@example.com"}}
]', 'JSON')) AS r) o
