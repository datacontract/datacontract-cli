---
sidebar_position: 14
title: "MySQL"
description: "Test data in MySQL and MySQL-compatible databases."
---

# MySQL

Test data in MySQL or MySQL-compatible databases (e.g. MariaDB).

## Example

```yaml
servers:
  mysql:
    type: mysql
    host: localhost
    port: 3306
    database: mydb
models:
  my_table_1:
    type: table
    fields:
      my_column_1:
        type: varchar
```

## Environment variables

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_MYSQL_USERNAME` | `root` | Username |
| `DATACONTRACT_MYSQL_PASSWORD` | `mysecretpassword` | Password |

Requires the `mysql` extra.
