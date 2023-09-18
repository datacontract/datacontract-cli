# datacontract.sh

## Commands

✅ = implemented
❌ = not implemented

### Standard Commands
- ✅ datacontract init # creates a datacontract.yaml with minimal required fields, and all options commented out, loaded from datacontract.com/datacontract.init.yaml
  - ✅ never overwrite 
  - ❌ name file
  - ❌ ask for basic values:
  ```
  dataContractSpecification: 0.9.0
  id: my-data-contract-id
  info:
    title: My Data Contract
    version: 0.0.1
  ```
- ✅ datacontract open # uploads datacontract.yaml to studio via HTTP POST and shows the view section in the browser

- ✅ datacontract validate # checks the validity of the datacontract.yaml using JSON Schema, loaded from datacontract.com
  - ❌ validate schema objects

- help
