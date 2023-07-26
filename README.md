# datacontract.sh

## Commands

✅ = implemented
❌ = not implemented

### Standard Commands

- `datacontract init` ❌
  - Prompts for mandatory/important fields (provider-team, provider-dataproduct, provider-outputport, consumer-team, consumer-dataproduct, purpose)
  - Link to dataproduct-outputport-spec
  - Additional: flags
  - Defaults: startDate is today, override possible, status is draft, other fields set to empty, schema: none
  - Result: `./datacontract.yml`
  - Alternative: provide url to data contract, download contract from there
- `datacontract validate` ❌
  - Validate against JSON Schema (download based on used version)
  - Best Practices on filling out a data contract
  - Detect issues not part of the JSON Schema
- `datacontract schema` ❌
  - Prints schema
  - Flag: type -> convert 

### Automation

- `datacontract test` ❌
  - Compare with output schema definition (requires output port to be specified and locatable), only via DMM?

- `datacontract open` ❌ (in Viewer/Data Mesh Manager)

### Advanced Commands

- `datacontract compare <dataproduct-url/dmm-id>` ❌ (maybe as part of validate or test)

### Data Mesh Manager Commands

- `datacontract push` ❌ (to Data Mesh Manager)
  - send to PUT endpoint
- `datacontract pull` ❌ (from Data Mesh Manager)
  - get from DMM, overwrite
- `datacontract subscribe` ❌
  - get events from event feed for this contract

## Integrations

- GitHub Actions ❌
- VS Code Plugin ❌

## Other Approach

- `datacontract test` within pipeline
  - Reads schema/SLOs/SLAs, triggers/executes quality checks, reports status back to console or directly to DMM

## Who's using the tool for what

- Data Product Provider
  - Validate
  - Compare against output port, especially when I change my output port def
  - Test against actual data (is extra effort, but probably not because already tested via output port def)
  - Monitoring if subset is really used

- Data Product Consumer
  - Uses init to create the contract manually (using existing output port)
  - Edits the contract manually, subset + validation (compare against output port) meta-data-plane
  - Extend quality checks, test actual data against them (my own pipeline) real-world-plane
  - Push to DMM





