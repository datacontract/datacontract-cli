---
sidebar_position: 12
title: "Export: RDF"
description: "Export a data contract to an RDF representation."
---

<img className="page-icon" src="/img/icons/generic.svg" alt="" />

# Export: RDF

Converts the data contract into an RDF representation. You can add a base URL used as the default prefix to resolve relative IRIs inside the document.

```bash
datacontract export rdf --base https://www.example.com/ datacontract.yaml
```

The contract is mapped onto concepts of a Data Contract Ontology (`DataContract`, `Server`, `Model`). Having the contract as an RDF graph enables interoperability with other formats, storage in a knowledge graph, semantic search, linking to established ontologies, OWL reasoning, and graph algorithms across multiple contracts.
