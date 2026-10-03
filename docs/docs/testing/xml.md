---
sidebar_position: 26
title: "XML files"
description: "Test XML documents against a data contract, starting from their XML Schema."
---

# <img className="page-icon" src="/img/icons/custom.svg" alt="" /> XML files

Test XML documents against a data contract: every record is checked for required values, types, enumerations, patterns, ranges, and your quality SQL, the same as rows of a table. The quickest contract comes from the XML Schema (XSD) the documents follow.

The files of this walkthrough are in [`examples/testing/xml`](https://github.com/datacontract/datacontract-cli/tree/main/examples/testing/xml).

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[duckdb,xml]'
```

`duckdb` reads the documents, `xml` imports the XML Schema. The CLI reads XML through the [webbed](https://duckdb.org/community_extensions/extensions/webbed) DuckDB community extension, which it downloads on the first test run, so that run needs network access.

## 2. Create a contract from the XML Schema

Given this `orders.xsd`, with one `order` per document:

```xml
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="order">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="order_id" type="xs:string"/>
        <xs:element name="placed_at" type="xs:dateTime"/>
        <xs:element name="status">
          <xs:simpleType>
            <xs:restriction base="xs:string">
              <xs:enumeration value="pending"/>
              <xs:enumeration value="shipped"/>
            </xs:restriction>
          </xs:simpleType>
        </xs:element>
        <xs:element name="line_item" maxOccurs="unbounded">
          <xs:complexType>
            <xs:sequence>
              <xs:element name="sku" type="xs:string"/>
              <xs:element name="price">
                <xs:complexType>
                  <xs:simpleContent>
                    <xs:extension base="xs:decimal">
                      <xs:attribute name="currency" type="xs:string" use="required"/>
                    </xs:extension>
                  </xs:simpleContent>
                </xs:complexType>
              </xs:element>
            </xs:sequence>
          </xs:complexType>
        </xs:element>
      </xs:sequence>
      <xs:attribute name="version" type="xs:positiveInteger" use="required"/>
    </xs:complexType>
  </xs:element>
</xs:schema>
```

Then import it:

```bash
datacontract import xsd --source orders.xsd --output orders.odcs.yaml
```

and point a server at the documents, here `orders/order-1001.xml`, `orders/order-1002.xml`, and so on:

```yaml
servers:
- server: local
  type: local
  path: orders/*.xml
  format: xml
```

## 3. Test the documents

```bash
datacontract test orders.odcs.yaml
```

```
Server: local (type=local, format=xml, path=orders/*.xml)
╭────────┬──────────────────────────────────────────────────┬────────────────────────────┬─────────╮
│ Result │ Check                                            │ Field                      │ Details │
├────────┼──────────────────────────────────────────────────┼────────────────────────────┼─────────┤
│ passed │ Check that the documents have order elements     │                            │         │
│ passed │ Check that field 'line_item' is present          │ line_item                  │         │
│ passed │ Check that field line_item[].price.currency has  │ line_item[].price.currency │         │
│        │ no missing values                                │                            │         │
│  ...   │                                                  │                            │         │
│ passed │ Check that field status only contains enum       │ status                     │         │
│        │ values ['pending', 'shipped']                    │                            │         │
│ passed │ Check that field version has no missing values   │ version                    │         │
╰────────┴──────────────────────────────────────────────────┴────────────────────────────┴─────────╯
🟢 Data contract is valid. Run 16 checks. Took 0.35 seconds.
```

## 4. Let it catch a violation

Add a document with an unknown status, no `version`, and a price without its currency:

```xml
<order>
  <order_id>ORD-1003</order_id>
  <placed_at>2026-09-03T12:00:00</placed_at>
  <status>cancelled</status>
  <line_item>
    <sku>ABC-1</sku>
    <price>49.95</price>
  </line_item>
</order>
```

```
🔴 Data contract is invalid, found the following errors:
1) status Check that field status only contains enum values ['pending', 'shipped']: Actual
invalid_count(status) was 1, expected = 0
2) line_item[].price.currency Check that field line_item[].price.currency has no missing values:
Actual missing_count(line_item[].price.currency) was 1, expected = 0
3) version Check that field version has no missing values: Actual missing_count(version) was 1,
expected = 0
```

The command exits with code `1`, so the same call works as a gate in [CI/CD pipelines](../scheduling/index.md).

## How documents become records

- **Records.** Every element named like the schema's `physicalName` (or its `name`, when there is none) is one record, wherever it is in the document: the root of a file with one record, or repeated inside a wrapper element such as `<orders><order>…</order><order>…</order></orders>`. All files the `path` matches are read together.
- **Properties.** Child elements and attributes are both properties of the record. A child element with children of its own is an `object`, and an element that repeats is an `array`; checks on their fields read `line_item[].sku`.
- **Text with attributes.** The text of an element that also has attributes, such as `<price currency="EUR">49.95</price>`, is read into the property with the custom property `xmlNode: text`. `datacontract import xsd` adds it as `value`; in a contract written by hand, add it yourself:

  ```yaml
  - name: price
    logicalType: object
    properties:
      - name: value
        logicalType: number
        customProperties:
          - property: xmlNode
            value: text
      - name: currency
        logicalType: string
  ```

- **Namespaces.** Elements are matched by their local name, so `<o:order xmlns:o="urn:example:orders">` is an `order` record.
- **Records.** A check fails when the documents contain no element named like the record element at all, so a misspelled `physicalName` never passes.
- **Presence.** An element or attribute that is not required may be absent from every document, so only the required properties of the record element are checked for presence. Required values further down are checked for missing values.
- **Attributes named like an element.** The import names such an attribute with an `@` prefix (`@id`), and the test reads it under that name. When an element and an attribute of the same element share a name, DuckDB's XML reader reads only the attribute, so the element's checks cannot run, with a warning.
- **Large files.** Files of any size are read, each one whole, so a file needs about its size in memory.
- **Types.** The documents are read as the contract's `logicalType`s, like [CSV files](../reference/local.md#data-types); `physicalType` is not checked.

## Reference

No environment variables are needed. The `path` supports glob patterns and a `{model}` placeholder, the same as for [local files](./local.md). The XSD import and its mapping: **[Import: XML Schema](../imports/xsd.md)**. To validate documents against the contract with XML tools instead, export it with **[`datacontract export xsd`](../exports/xsd.md)**.

## Troubleshooting

- **`Failed to install the 'webbed' DuckDB community extension`** — the first run downloads the extension. Run it once with network access; later runs use the installed copy.
- **`Check that the documents have … elements` fails** — no element in the documents is named like the schema's `physicalName`. Set `physicalName` to the element of one record, for example `order` rather than the wrapper `orders`.
- **`value '…' does not match column type …`** — a value cannot be read as its property's `logicalType`, such as `<quantity>many</quantity>` for an `integer`. The checks that need the value report the read error.
- **The text of an element is always missing** — the property for it needs the custom property `xmlNode: text` (see above).
