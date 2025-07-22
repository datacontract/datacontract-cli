# urn:datacontract:checkout:orders-latest
## Info
*Successful customer orders in the webshop. <br>All orders since 2020-01-01. <br>Orders with their line items are in their current state (no history included).<br>*

- **title:** Orders Latest

- **version:** 2.0.0

- **owner:** Checkout Team

- **contact:** {'name': 'John Doe (Data Product Owner)', 'url': 'https://teams.microsoft.com/l/channel/example/checkout'}

## Servers
| Server | Type | description | environment | format | delimiter | location | roles |
| ------ | ---- | ----------- | ----------- | ------ | --------- | -------- | ----- |
| production | s3 | One folder per model. One file per day. | prod | json | new_line | s3://datacontract-example-orders-latest/v2/{model}/*.json | [{'name': 'analyst_us', 'description': 'Access to the data for US region'}, {'name': 'analyst_cn', 'description': 'Access to the data for China region'}] |

## Terms
*No description.*

- **usage:** Data can be used for reports, analytics and machine learning use cases.
Order may be linked and joined by other tables


- **limitations:** Not suitable for real-time use cases.
Data may not be used to identify individual customers.
Max data processing per day: 10 TiB


- **policies:** [{'url': 'https://example.com/privacy-policy', 'name': 'privacy-policy'}, {'description': 'External data is licensed under agreement 1234.', 'url': 'https://example.com/license/1234', 'name': 'license'}]

- **billing:** 5000 USD per month

- **noticePeriod:** P3M

## Models
### orders
*One record per order. Includes cancelled and deleted orders.*

| ref | title | type | format | required | primaryKey | unique | description | pii | classification | tags | examples | minLength | maxLength | quality | lineage | config |
| --- | ----- | ---- | ------ | -------- | ---------- | ------ | ----------- | --- | -------------- | ---- | -------- | --------- | --------- | ------- | ------- | ------ |
| #/definitions/order_id | Order ID | text | uuid | True | True | True | An internal ID that identifies an order in the online shop. | True | restricted | ['orders'] | ['243c25e5-a081-43a9-aeab-6d5d5b6cb5e2'] |  |  |  |  |  |
|  |  | timestamp |  | True |  |  | The business timestamp in UTC when the order was successfully registered in the source system and the payment was successful. |  |  | ['business-timestamp'] | ['2024-09-09T08:30:00Z'] |  |  |  |  |  |
|  |  | long |  | True |  |  | Total amount the smallest monetary unit (e.g., cents). |  |  |  | [9999] |  |  |  |  |  |
|  |  | text |  |  |  |  | Unique identifier for the customer. |  |  |  |  | 10 | 20 |  |  |  |
|  |  | text | email | True |  |  | The email address, as entered by the customer. | True | sensitive |  |  |  |  | [{'type': 'text', 'description': 'The email address is not verified and may be invalid.'}] | {'inputFields': [{'namespace': 'com.example.service.checkout', 'name': 'checkout_db.orders', 'field': 'email_address'}]} |  |
|  |  | timestamp |  | True |  |  | The timestamp when the record was processed by the data platform. |  |  |  |  |  |  |  |  | {'jsonType': 'string', 'jsonFormat': 'date-time'} |
### line_items
*A single article that is part of an order.*

| type | required | description | ref | title | format | references | pii | classification | tags | examples | pattern | links |
| ---- | -------- | ----------- | --- | ----- | ------ | ---------- | --- | -------------- | ---- | -------- | ------- | ----- |
| text | True | Primary key of the lines_item_id table |  |  |  |  |  |  |  |  |  |  |
| text |  | An internal ID that identifies an order in the online shop. | #/definitions/order_id | Order ID | uuid | orders.order_id | True | restricted | ['orders'] | ['243c25e5-a081-43a9-aeab-6d5d5b6cb5e2'] |  |  |
| text |  | The purchased article number | #/definitions/sku | Stock Keeping Unit |  |  |  |  | ['inventory'] | ['96385074'] | ^[A-Za-z0-9]{8,14}$ | {'wikipedia': 'https://en.wikipedia.org/wiki/Stock_keeping_unit'} |

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
