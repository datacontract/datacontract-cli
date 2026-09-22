`who-metadata.xml` was retrieved from
https://xmart-api-public-uat.who.int/refmart/$metadata on 2026-09-18.
The response declared `OData-Version: 4.0`. XML whitespace was formatted for readability.

`who-contract.yaml` describes the expected import of
https://xmart-api-public-uat.who.int/refmart/ref_country.
All network access is mocked in the tests.

`products.xml` and `products.json` are independently authored synthetic CSDL examples
of the same catalog model. Entity types and the service container live in separate
schemas and use an alias. They cover composite keys, ordered properties and facets;
they contain no data or schema from a private service.

`service-document.json` advertises Products and Orders from the synthetic model,
with relative and absolute addresses, plus other resource kinds to ignore.
ArchivedProducts shares the Product type but is available only through explicit selection.
