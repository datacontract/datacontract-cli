---
sidebar_position: 5
title: "Import: AWS Glue"
description: "Create a data contract from the AWS Glue Data Catalog."
---

<img className="page-icon" src="/img/icons/glue.svg" alt="" />

# Import: AWS Glue

Creates a data contract from the AWS Glue Data Catalog.

```bash
# Import specific tables from a Glue database
datacontract import glue --source my_database --table orders --table line_items

# Import all tables in the database
datacontract import glue --source my_database
```

AWS credentials are resolved from the standard AWS environment / configuration (e.g. `AWS_PROFILE`, `AWS_REGION`).
