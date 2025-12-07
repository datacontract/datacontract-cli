# urn:datacontract:checkout:orders-latest
## Info
*Successful customer orders in the webshop. <br>All orders since 2020-01-01. <br>Orders with their line items are in their current state (no history included).<br>*
- **name:** Orders Latest
- **version:** 2.0.0
- **team:** Checkout Team

## Terms of Use
*No terms of use defined.*

## Servers
| Name | Type | Attributes |
| ---- | ---- | ---------- |
| production | s3 | *No description.*<br>• **environment:** prod<br>• **delimiter:** new_line<br>• **format:** json<br>• **location:** s3://datacontract-example-orders-latest/v2/{model}/*.json |
| development | s3 | *No description.*<br>• **environment:** dev<br>• **delimiter:** new_line<br>• **format:** json<br>• **location:** s3://datacontract-example-orders-latest/v2/{model}/*.json |

## Schema
### orders
*One record per order. Includes cancelled and deleted orders.*

| Field | Type | Attributes |
| ----- | ---- | ---------- |
|  order_id | string | *An internal ID that identifies an order in the online shop.*<br>• **businessName:** Order ID<br>• **tags:** ['orders']<br>• **customProperties:** [{'property': 'pii', 'value': 'True'}]<br>• `primaryKey`<br>• **logicalTypeOptions:** {'format': 'uuid'}<br>• `required`<br>• `unique`<br>• **classification:** restricted |
|  order_timestamp | timestamp | *The business timestamp in UTC when the order was successfully registered in the source system and the payment was successful.*<br>• **tags:** ['business-timestamp']<br>• `required` |
|  order_total | integer | *Total amount the smallest monetary unit (e.g., cents).*<br>• `required` |
|  customer_id | string | *Unique identifier for the customer.*<br>• **logicalTypeOptions:** {'minLength': 10, 'maxLength': 20} |
|  customer_email_address | string | *The email address, as entered by the customer.*<br>• **customProperties:** [{'property': 'pii', 'value': 'True'}]<br>• **logicalTypeOptions:** {'format': 'email'}<br>• `required`<br>• **classification:** sensitive<br>• **quality:** [{'description': 'The email address is not verified and may be invalid.', 'type': 'text'}] |
|  processed_timestamp | timestamp | *The timestamp when the record was processed by the data platform.*<br>• **customProperties:** [{'property': 'jsonType', 'value': 'string'}, {'property': 'jsonFormat', 'value': 'date-time'}]<br>• `required` |
### line_items
*A single article that is part of an order.*

| Field | Type | Attributes |
| ----- | ---- | ---------- |
|  line_item_id | string | *Primary key of the lines_item_id table*<br>• `primaryKey`<br>• **primaryKeyPosition:** 2<br>• `required` |
|  order_id | string | *An internal ID that identifies an order in the online shop.*<br>• **businessName:** Order ID<br>• **tags:** ['orders']<br>• **customProperties:** [{'property': 'pii', 'value': 'True'}]<br>• `primaryKey`<br>• **primaryKeyPosition:** 1<br>• **logicalTypeOptions:** {'format': 'uuid'}<br>• **classification:** restricted<br>• **relationships:** [{'type': 'foreignKey', 'to': 'orders.order_id'}] |
|  sku | string | *The purchased article number*<br>• **businessName:** Stock Keeping Unit<br>• **tags:** ['inventory']<br>• **logicalTypeOptions:** {'pattern': '^[A-Za-z0-9]{8,14}$'} |

## SLA Properties
| Property | Value | Unit |
| -------- | ----- | ---- |
| generalAvailability | The server is available during support hours |  |
| retention | P1Y |  |
| freshness | 25 | h |