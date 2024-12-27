# urn:datacontract:checkout:orders-latest
## Info
*Successful customer orders in the webshop. <br>All orders since 2020-01-01. <br>Orders with their line items are in their current state (no history included).<br>*
- **title:** Orders Latest
- **version:** 2.0.0
- **owner:** Checkout Team
- **contact:** {'name': 'John Doe (Data Product Owner)', 'url': 'https://teams.microsoft.com/l/channel/example/checkout'}

## Servers
| Name | Type | Attributes |
| ---- | ---- | ---------- |
| production | s3 | *One folder per model. One file per day.*<br>• **environment:** prod<br>• **format:** json<br>• **delimiter:** new_line<br>• **location:** s3://datacontract-example-orders-latest/v2/{model}/*.json<br>• **roles:** [{'name': 'analyst_us', 'description': 'Access to the data for US region'}, {'name': 'analyst_cn', 'description': 'Access to the data for China region'}] |

## Terms
*No description.*
- **usage:** Data can be used for reports, analytics and machine learning use cases.
Order may be linked and joined by other tables

- **limitations:** Not suitable for real-time use cases.
Data may not be used to identify individual customers.
Max data processing per day: 10 TiB

- **billing:** 5000 USD per month
- **noticePeriod:** P3M
- **policies:** [{'name': 'privacy-policy', 'url': 'https://example.com/privacy-policy'}, {'name': 'license', 'description': 'External data is licensed under agreement 1234.', 'url': 'https://example.com/license/1234'}]

## Models
### orders
*One record per order. Includes cancelled and deleted orders.*

| Field | Type | Attributes |
| ----- | ---- | ---------- |
|  order_id | None | *No description.*<br>• **ref:** #/definitions/order_id<br>• `required`<br>• `primaryKey`<br>• `unique` |
|  order_timestamp | timestamp | *The business timestamp in UTC when the order was successfully registered in the source system and the payment was successful.*<br>• `required`<br>• **tags:** ['business-timestamp']<br>• **examples:** ['2024-09-09T08:30:00Z'] |
|  order_total | long | *Total amount the smallest monetary unit (e.g., cents).*<br>• `required`<br>• **examples:** [9999] |
|  customer_id | text | *Unique identifier for the customer.*<br>• **minLength:** 10<br>• **maxLength:** 20 |
|  customer_email_address | text | *The email address, as entered by the customer.*<br>• **format:** email<br>• `required`<br>• `pii`<br>• **classification:** sensitive<br>• **quality:** [{'type': 'text', 'description': 'The email address is not verified and may be invalid.'}]<br>• **lineage:** {'inputFields': [{'namespace': 'com.example.service.checkout', 'name': 'checkout_db.orders', 'field': 'email_address'}]} |
|  processed_timestamp | timestamp | *The timestamp when the record was processed by the data platform.*<br>• `required`<br>• **config:** {'jsonType': 'string', 'jsonFormat': 'date-time'} |
### line_items
*A single article that is part of an order.*

| Field | Type | Attributes |
| ----- | ---- | ---------- |
|  line_item_id | text | *Primary key of the lines_item_id table*<br>• `required` |
|  order_id | None | *No description.*<br>• **ref:** #/definitions/order_id<br>• **references:** orders.order_id |
|  sku | None | *The purchased article number*<br>• **ref:** #/definitions/sku |

## Definitions
| Name | Type | Domain | Attributes |
| ---- | ---- | ------ | ---------- |
| order_id | text |  | *An internal ID that identifies an order in the online shop.*<br>• **title:** Order ID<br>• **format:** uuid<br>• `pii`<br>• **classification:** restricted<br>• **tags:** ['orders']<br>• **examples:** ['243c25e5-a081-43a9-aeab-6d5d5b6cb5e2'] |
| sku | text |  | *A Stock Keeping Unit (SKU) is an internal unique identifier for an article. <br>It is typically associated with an article's barcode, such as the EAN/GTIN.<br>*<br>• **title:** Stock Keeping Unit<br>• **pattern:** ^[A-Za-z0-9]{8,14}$<br>• **tags:** ['inventory']<br>• **links:** {'wikipedia': 'https://en.wikipedia.org/wiki/Stock_keeping_unit'}<br>• **examples:** ['96385074'] |

## Service levels
### Availability
*The server is available during support hours*
- **percentage:** 99.9%

### Retention
*Data is retained for one year*
- **period:** P1Y

### Latency
*Data is available within 25 hours after the order was placed*
- **threshold:** 25h
- **sourceTimestampField:** orders.order_timestamp
- **processedTimestampField:** orders.processed_timestamp

### Freshness
*The age of the youngest row in a table.*
- **threshold:** 25h
- **timestampField:** orders.order_timestamp

### Frequency
*Data is delivered once a day*
- **type:** batch
- **interval:** daily
- **cron:** 0 0 * * *

### Support
*The data is available during typical business hours at headquarters*
- **time:** 9am to 5pm in EST on business days
- **responseTime:** 1h

### Backup
*Data is backed up once a week, every Sunday at 0:00 UTC.*
- **interval:** weekly
- **cron:** 0 0 * * 0
- **recoveryTime:** 24 hours
- **recoveryPoint:** 1 week
