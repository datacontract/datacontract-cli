---
sidebar_position: 12
title: "Export: RDF"
description: "Export a data contract to an RDF representation."
---

<img className="page-icon" src="/img/icons/rdf.svg" alt="" />

# Export: RDF

Converts the data contract into an RDF representation. You can add a base URL used as the default prefix to resolve relative IRIs inside the document.

```bash
datacontract export rdf orders.odcs.yaml --output orders.ttl
```

Running this against the [example `orders` contract](https://github.com/datacontract/datacontract-cli/blob/main/examples/orders/orders.odcs.yaml) produces (excerpt):

```turtle
@prefix odcs: <https://github.com/bitol-io/open-data-contract-standard/> .
@prefix odcsx: <https://github.com/bitol-io/open-data-contract-standard/extension/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<urn:datacontract:checkout:orders> a odcs:DataContract ;
    odcs:apiVersion "v3.1.0" ;
    odcs:id "urn:datacontract:checkout:orders" ;
    odcs:info [ a odcs:Info ;
            odcs:description "Tracks customer orders and their line items for analytics and reporting." ;
            odcs:name "Orders" ;
            odcs:version "1.0.0" ] ;
    odcs:kind "DataContract" ;
    odcs:schema_ <line_items>,
        <orders> ;
    odcs:server <bigquery>,
        <production> .

<bigquery> a odcs:Server ;
    odcsx:dataset "orders" ;
    odcsx:project "my-gcp-project" ;
    odcsx:server "bigquery" ;
    odcs:type "bigquery" .

<line_items> a odcs:Schema ;
    odcs:description "One row per line item within an order." ;
    odcs:property [ a odcs:Property ;
            odcs:description "Unique identifier of the line item." ;
            odcsx:primaryKey true ;
            odcs:logicalType "string" ;
            odcs:name "line_item_id" ;
# …
```

The contract is mapped onto concepts of a Data Contract Ontology (`DataContract`, `Server`, `Model`). Having the contract as an RDF graph enables interoperability with other formats, storage in a knowledge graph, semantic search, linking to established ontologies, OWL reasoning, and graph algorithms across multiple contracts.
