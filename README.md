# datacontract.sh

## Commands

✅ = implemented
❌ = not implemented

### Standard Commands

- `datacontract init` ❌
  - Prompts for mandatory/important fields (provider-team, provider-dataproduct, provider-outputport, consumer-team, consumer-dataproduct, purpose) ✅
  - Link to dataproduct-outputport-spec
  - Additional: flags
  - Defaults: startDate is today, override possible, status is draft, other fields set to empty, schema: none ✅
  - Result: `./datacontract.yml` ✅
  - Alternative: provide url to data contract, download contract from there
- `datacontract validate` ❌
  - Validate against JSON Schema (download based on used version)
  - Best Practices on filling out a data contract
  - Detect issues not part of the JSON Schema
- `datacontract schema` ❌
  - Prints schema

### Automation

- `datacontract test` ❌
  - Compare with output schema definition (requires output port to be specified and locatable)

### Repository Commands

Defaults to Data Mesh Manager

- `datacontract open` ❌
- `datacontract push` ❌
- `datacontract pull` ❌

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
