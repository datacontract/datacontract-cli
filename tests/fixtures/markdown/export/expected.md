# urn:datacontract:checkout:orders-latest
## Info
<i>Successful customer orders in the webshop. 
All orders since 2020-01-01. 
Orders with their line items are in their current state (no history included).
</i>
<li><b>title:</b> Orders Latest</li>
<li><b>version:</b> 2.0.0</li>
<li><b>owner:</b> Checkout Team</li>
<li><b>contact:</b> {'name': 'John Doe (Data Product Owner)', 'url': 'https://teams.microsoft.com/l/channel/example/checkout'}</li>

## Servers
<table>
<tr>
<th>Name</th>
<th>Type</th>
<th>Attributes</th>
</tr>
<tr>
<td>production</td>
<td>s3</td>
<td>
<i>One folder per model. One file per day.</i>
<li><b>environment:</b> prod</li>
<li><b>format:</b> json</li>
<li><b>delimiter:</b> new_line</li>
<li><b>location:</b> s3://datacontract-example-orders-latest/v2/{model}/*.json</li>
<li><b>roles:</b> [{'name': 'analyst_us', 'description': 'Access to the data for US region'}, {'name': 'analyst_cn', 'description': 'Access to the data for China region'}]</li>
</td>
</tr>
</table>

## Terms
<i>No description.</i>
<li><b>usage:</b> Data can be used for reports, analytics and machine learning use cases.
Order may be linked and joined by other tables
</li>
<li><b>limitations:</b> Not suitable for real-time use cases.
Data may not be used to identify individual customers.
Max data processing per day: 10 TiB
</li>
<li><b>billing:</b> 5000 USD per month</li>
<li><b>noticePeriod:</b> P3M</li>
<li><b>policies:</b> [{'name': 'privacy-policy', 'url': 'https://example.com/privacy-policy'}, {'name': 'license', 'description': 'External data is licensed under agreement 1234.', 'url': 'https://example.com/license/1234'}]</li>

## Models
<table>
<tr>
<th colspan=3>ORDERS<br/>
<i>One record per order. Includes cancelled and deleted orders.</i></th>
</tr>
<tr>
<td> order_id</td>
<td>None</td>
<td><i>No description.</i>
<li><b>ref:</b> #/definitions/order_id</li>
<li><code>required</code></li>
<li><code>primaryKey</code></li>
<li><code>unique</code></li></td>
</tr>
<tr>
<td> order_timestamp</td>
<td>timestamp</td>
<td><i>The business timestamp in UTC when the order was successfully registered in the source system and the payment was successful.</i>
<li><code>required</code></li>
<li><b>tags:</b> ['business-timestamp']</li>
<li><b>examples:</b> ['2024-09-09T08:30:00Z']</li></td>
</tr>
<tr>
<td> order_total</td>
<td>long</td>
<td><i>Total amount the smallest monetary unit (e.g., cents).</i>
<li><code>required</code></li>
<li><b>examples:</b> [9999]</li></td>
</tr>
<tr>
<td> customer_id</td>
<td>text</td>
<td><i>Unique identifier for the customer.</i>
<li><b>minLength:</b> 10</li>
<li><b>maxLength:</b> 20</li></td>
</tr>
<tr>
<td> customer_email_address</td>
<td>text</td>
<td><i>The email address, as entered by the customer.</i>
<li><b>format:</b> email</li>
<li><code>required</code></li>
<li><code>pii</code></li>
<li><b>classification:</b> sensitive</li>
<li><b>quality:</b> [{'type': 'text', 'description': 'The email address is not verified and may be invalid.'}]</li>
<li><b>lineage:</b> {'inputFields': [{'namespace': 'com.example.service.checkout', 'name': 'checkout_db.orders', 'field': 'email_address'}]}</li></td>
</tr>
<tr>
<td> processed_timestamp</td>
<td>timestamp</td>
<td><i>The timestamp when the record was processed by the data platform.</i>
<li><code>required</code></li>
<li><b>config:</b> {'jsonType': 'string', 'jsonFormat': 'date-time'}</li></td>
</tr>
</table>

<table>
<tr>
<th colspan=3>LINE_ITEMS<br/>
<i>A single article that is part of an order.</i></th>
</tr>
<tr>
<td> line_item_id</td>
<td>text</td>
<td><i>Primary key of the lines_item_id table</i>
<li><code>required</code></li></td>
</tr>
<tr>
<td> order_id</td>
<td>None</td>
<td><i>No description.</i>
<li><b>ref:</b> #/definitions/order_id</li>
<li><b>references:</b> orders.order_id</li></td>
</tr>
<tr>
<td> sku</td>
<td>None</td>
<td><i>The purchased article number</i>
<li><b>ref:</b> #/definitions/sku</li></td>
</tr>
</table>


## Definitions
<table>
<tr>
<th>Name</th>
<th>Type</th>
<th>Domain</th>
<th>Attributes</th>
</tr>
<tr>
<td>order_id</td>
<td>text</td>
<td></td>
<td>
<i>An internal ID that identifies an order in the online shop.</i>
<li><b>title:</b> Order ID</li>
<li><b>format:</b> uuid</li>
<li><code>pii</code></li>
<li><b>classification:</b> restricted</li>
<li><b>tags:</b> ['orders']</li>
<li><b>examples:</b> ['243c25e5-a081-43a9-aeab-6d5d5b6cb5e2']</li>
</td>
</tr>
<tr>
<td>sku</td>
<td>text</td>
<td></td>
<td>
<i>A Stock Keeping Unit (SKU) is an internal unique identifier for an article. 
It is typically associated with an article's barcode, such as the EAN/GTIN.
</i>
<li><b>title:</b> Stock Keeping Unit</li>
<li><b>pattern:</b> ^[A-Za-z0-9]{8,14}$</li>
<li><b>tags:</b> ['inventory']</li>
<li><b>links:</b> {'wikipedia': 'https://en.wikipedia.org/wiki/Stock_keeping_unit'}</li>
<li><b>examples:</b> ['96385074']</li>
</td>
</tr>
</table>

## Service levels

### Availability
<i>The server is available during support hours</i>
<li><b>percentage:</b> 99.9%</li>

### Retention
<i>Data is retained for one year</i>
<li><b>period:</b> P1Y</li>

### Latency
<i>Data is available within 25 hours after the order was placed</i>
<li><b>threshold:</b> 25h</li>
<li><b>sourceTimestampField:</b> orders.order_timestamp</li>
<li><b>processedTimestampField:</b> orders.processed_timestamp</li>

### Freshness
<i>The age of the youngest row in a table.</i>
<li><b>threshold:</b> 25h</li>
<li><b>timestampField:</b> orders.order_timestamp</li>

### Frequency
<i>Data is delivered once a day</i>
<li><b>type:</b> batch</li>
<li><b>interval:</b> daily</li>
<li><b>cron:</b> 0 0 * * *</li>

### Support
<i>The data is available during typical business hours at headquarters</i>
<li><b>time:</b> 9am to 5pm in EST on business days</li>
<li><b>responseTime:</b> 1h</li>

### Backup
<i>Data is backed up once a week, every Sunday at 0:00 UTC.</i>
<li><b>interval:</b> weekly</li>
<li><b>cron:</b> 0 0 * * 0</li>
<li><b>recoveryTime:</b> 24 hours</li>
<li><b>recoveryPoint:</b> 1 week</li>
