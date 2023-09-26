# Examples

## datacontract diff

```bash
$ datacontract diff --file my-data-contract-id_v0.0.1.yaml --with https://raw.githubusercontent.com/datacontract/cli/main/examples/my-data-contract-id_v0.0.2.yaml
Found 2 differences between the data contracts!

🔴 Difference 1:
Description:  field 'my_table.my_column' was removed
Type:         field-removed
Severity:     breaking
Level:        field
Model:        my_table
Field:        my_column

🟡 Difference 2:
Description:  field 'my_table.my_column2' was added
Type:         field-added
Severity:     info
Level:        field
Model:        my_table
Field:        my_column2
```

## datacontract breaking

```
$ datacontract breaking --file my-data-contract-id_v0.0.1.yaml --with https://raw.githubusercontent.com/datacontract/cli/main/examples/my-data-contract-id_v0.0.2.yaml
Found 1 differences between the data contracts!

🔴 Difference 1:
Description:  field 'my_table.my_column' was removed
Type:         field-removed
Severity:     breaking
Level:        field
Model:        my_table
Field:        my_column
Exiting application with error: found breaking differences between the data contracts
```
