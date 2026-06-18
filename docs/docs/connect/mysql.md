---
sidebar_position: 13
title: "MySQL"
description: "Test data in MySQL and MySQL-compatible databases."
---

<img className="page-icon" src="/img/icons/mysql.svg" alt="" />

# MySQL

:::info Required extra
This connection requires the `mysql` extra. See [Installation](../installation.md).
:::

Test data in MySQL or MySQL-compatible databases (e.g. MariaDB).

## Server

```yaml
servers:
  - server: mysql
    type: mysql
    host: localhost
    port: 3306
    database: mydb
```

## Environment variables

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_MYSQL_USERNAME` | `root` | Username |
| `DATACONTRACT_MYSQL_PASSWORD` | `mysecretpassword` | Password |

