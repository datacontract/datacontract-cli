# Big-Bang Migration Plan: DataContractSpecification → ODCS

## Overview

This plan outlines the complete migration of `datacontract-cli` from using `DataContractSpecification` (DCS) as the internal data model to `OpenDataContractStandard` (ODCS v3.x) as the sole internal representation.

**Approach**: Big-bang migration - all changes made together, no adapter layer, clean break.

## Scope Summary

| Category | Files | Action |
|----------|-------|--------|
| Core model | 1 | Replace DCS with ODCS |
| Main DataContract class | 1 | Rewrite for ODCS-only |
| Importers | 17 | Update to output ODCS |
| Exporters | 22 | Update to accept ODCS |
| Engines/Validation | 7 | Update to use ODCS |
| Breaking changes | 3 | **DELETE entirely** |
| CLI | 1 | Remove breaking/changelog/diff, update commands |
| Tests | ~50 | Update fixtures and assertions |
| **Total** | ~100 files | |

---

## Part 1: Deletions (Clean Up First)

### 1.1 Remove Breaking Changes Module

**Delete entirely:**
```
datacontract/breaking/
├── breaking.py          # DELETE
├── breaking_change.py   # DELETE
└── breaking_rules.py    # DELETE
```

**Update `datacontract/data_contract.py`:**
- Remove `breaking()` method
- Remove `changelog()` method
- Remove imports from `datacontract.breaking`

**Update `datacontract/cli.py`:**
- Remove `breaking` command
- Remove `changelog` command
- Remove `diff` command

**Delete tests:**
- `tests/test_breaking*.py`

### 1.2 Remove DCS-specific Code

**Delete or rename:**
- `datacontract/export/dcs_exporter.py` → Keep as legacy export option OR delete

---

## Part 2: Core Model Changes

### 2.1 Update Internal Model Definition

**File**: `datacontract/model/data_contract_specification/__init__.py`

**Current:**
```python
from datacontract_specification.model import *
```

**Change to:**
```python
# Re-export ODCS as the internal model
from open_data_contract_standard.model import *

# Backward compatibility aliases (optional, for gradual migration)
# DataContractSpecification = OpenDataContractStandard
```

**Consider renaming directory:**
```
datacontract/model/data_contract_specification/  →  datacontract/model/odcs/
```

### 2.2 Create Type Aliases (Optional)

**File**: `datacontract/model/types.py` (new)

```python
"""Type aliases for the internal data model."""
from open_data_contract_standard.model import (
    OpenDataContractStandard as DataContract,
    SchemaObject as Model,
    SchemaProperty as Field,
    DataQuality as Quality,
    Server,
    Description,
    Team,
    # ... other types
)
```

---

## Part 3: Main DataContract Class Rewrite

**File**: `datacontract/data_contract.py`

### 3.1 Update Imports

```python
# Remove
from datacontract.model.data_contract_specification import DataContractSpecification, Info

# Add
from open_data_contract_standard.model import OpenDataContractStandard
```

### 3.2 Update Class Signature

```python
class DataContract:
    def __init__(
        self,
        data_contract_file: str = None,
        data_contract_str: str = None,
        data_contract: OpenDataContractStandard = None,  # Changed type
        # ... rest unchanged
    ):
```

### 3.3 Remove Methods

```python
# DELETE these methods entirely:
def breaking(self, other: "DataContract") -> BreakingChanges: ...
def changelog(self, other: "DataContract", ...) -> BreakingChanges: ...
```

### 3.4 Update Methods

```python
# Rename and simplify
def get_data_contract_specification(self) -> DataContractSpecification:
# Becomes:
def get_odcs(self) -> OpenDataContractStandard:

# Keep wrapper for backward compatibility during transition:
def get_data_contract_specification(self) -> OpenDataContractStandard:
    """Deprecated: Use get_odcs() instead."""
    return self.get_odcs()
```

### 3.5 Simplify import_from_source

```python
@classmethod
def import_from_source(
    cls,
    format: str,
    source: typing.Optional[str] = None,
    template: typing.Optional[str] = None,
    **kwargs,
) -> OpenDataContractStandard:  # Always returns ODCS now
    # Remove Spec parameter - always ODCS
    # Remove conversion logic - importers output ODCS directly
```

---

## Part 4: Update Importers (17 files)

### 4.1 Update Base Importer

**File**: `datacontract/imports/importer.py`

```python
from open_data_contract_standard.model import OpenDataContractStandard

class Importer(ABC):
    @abstractmethod
    def import_source(
        self,
        source: str,
        import_args: dict,
    ) -> OpenDataContractStandard:  # Simplified signature
        pass

# Remove Spec enum - no longer needed
# class Spec(str, Enum): ... DELETE
```

### 4.2 Update Each Importer

**Pattern for each importer:**

```python
# Before (e.g., avro_importer.py)
from datacontract.model.data_contract_specification import DataContractSpecification, Field, Model

def import_avro(...) -> DataContractSpecification:
    data_contract_specification.models[name] = Model(fields=...)

# After
from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty

def import_avro(...) -> OpenDataContractStandard:
    odcs = OpenDataContractStandard(
        apiVersion="v3.1.0",
        kind="DataContract",
        id=...,
        name=...,
    )
    odcs.schema_ = [SchemaObject(
        name=name,
        properties=[...],
    )]
    return odcs
```

### 4.3 Importer Mapping Reference

| DCS Concept | ODCS Equivalent |
|-------------|-----------------|
| `DataContractSpecification()` | `OpenDataContractStandard(apiVersion="v3.1.0", kind="DataContract")` |
| `data_contract.id = ...` | `odcs.id = ...` |
| `data_contract.info.title = ...` | `odcs.name = ...` |
| `data_contract.info.version = ...` | `odcs.version = ...` |
| `data_contract.info.owner = ...` | `odcs.team = Team(name=...)` |
| `data_contract.info.description = ...` | `odcs.description = Description(purpose=...)` |
| `data_contract.models = {}` | `odcs.schema_ = []` |
| `Model(fields={...})` | `SchemaObject(name=..., properties=[...])` |
| `Field(type=..., description=...)` | `SchemaProperty(name=..., logicalType=..., description=...)` |
| `field.type = "string"` | `property.logicalType = "string"` |
| `field.primaryKey = True` | `property.primaryKey = True` |
| `field.required = True` | `property.required = True` |

### 4.4 Files to Update

```
datacontract/imports/
├── importer.py              # Base class
├── importer_factory.py      # Factory (minor changes)
├── avro_importer.py         # Full rewrite
├── bigquery_importer.py     # Full rewrite
├── csv_importer.py          # Full rewrite
├── dbml_importer.py         # Full rewrite
├── dbt_importer.py          # Full rewrite
├── excel_importer.py        # Full rewrite
├── glue_importer.py         # Full rewrite
├── iceberg_importer.py      # Full rewrite
├── json_importer.py         # Full rewrite
├── jsonschema_importer.py   # Full rewrite
├── odcs_importer.py         # Simplify (already ODCS)
├── odcs_v3_importer.py      # DELETE or keep for DCS→ODCS conversion
├── parquet_importer.py      # Full rewrite
├── protobuf_importer.py     # Full rewrite
├── spark_importer.py        # Full rewrite
├── sql_importer.py          # Full rewrite
└── unity_importer.py        # Full rewrite
```

---

## Part 5: Update Exporters (22 files)

### 5.1 Update Base Exporter

**File**: `datacontract/export/exporter.py`

```python
from open_data_contract_standard.model import OpenDataContractStandard

class Exporter(ABC):
    @abstractmethod
    def export(
        self,
        data_contract: OpenDataContractStandard,  # Changed type
        model: str,
        server: str,
        sql_server_type: str,
        export_args: dict
    ) -> dict | str:
        pass
```

### 5.2 Update Helper Functions

```python
# Before
def _check_models_for_export(data_contract: DataContractSpecification, ...):
    if data_contract.models is None:
        ...
    model_names = list(data_contract.models.keys())

# After
def _check_models_for_export(data_contract: OpenDataContractStandard, ...):
    if data_contract.schema_ is None:
        ...
    model_names = [schema.name for schema in data_contract.schema_]
```

### 5.3 Exporter Mapping Reference

| DCS Access | ODCS Access |
|------------|-------------|
| `data_contract.models` | `data_contract.schema_` |
| `data_contract.models.items()` | `[(s.name, s) for s in data_contract.schema_]` |
| `data_contract.models[name]` | `next(s for s in data_contract.schema_ if s.name == name)` |
| `model.fields` | `schema_obj.properties` |
| `model.fields.items()` | `[(p.name, p) for p in schema_obj.properties]` |
| `field.type` | `property.logicalType` |
| `field.description` | `property.description` |
| `data_contract.servers` | `data_contract.servers` (similar structure) |
| `data_contract.info.title` | `data_contract.name` |
| `data_contract.info.version` | `data_contract.version` |

### 5.4 Files to Update

```
datacontract/export/
├── exporter.py              # Base class
├── exporter_factory.py      # Factory (minor changes)
├── avro_converter.py        # Update
├── avro_idl_converter.py    # Update
├── bigquery_converter.py    # Update
├── custom_converter.py      # Update
├── data_caterer_converter.py # Update
├── dbml_converter.py        # Update
├── dbt_converter.py         # Update
├── dcs_exporter.py          # Keep for DCS export format
├── dqx_converter.py         # Update
├── excel_exporter.py        # Update
├── go_converter.py          # Update
├── great_expectations_converter.py # Update
├── html_exporter.py         # Update
├── iceberg_converter.py     # Update
├── jsonschema_converter.py  # Update
├── markdown_converter.py    # Update
├── mermaid_exporter.py      # Update
├── odcs_v3_exporter.py      # Simplify (already ODCS, becomes identity)
├── protobuf_converter.py    # Update
├── pydantic_converter.py    # Update
├── rdf_converter.py         # Update
├── sodacl_converter.py      # Update
├── spark_converter.py       # Update
├── sql_converter.py         # Update
├── sqlalchemy_converter.py  # Update
└── terraform_converter.py   # Update
```

---

## Part 6: Update Engines

### 6.1 Test Engine

**File**: `datacontract/engines/data_contract_test.py`

```python
# Update function signatures
def execute_data_contract_test(
    data_contract: OpenDataContractStandard,  # Changed
    run: Run,
    server_name: str,
    ...
):
    # Update model iteration
    for schema in data_contract.schema_:
        for prop in schema.properties:
            ...
```

### 6.2 Checks Creation

**File**: `datacontract/engines/data_contract_checks.py`

This is the largest file. Key changes:
- Update all `DataContractSpecification` references to `OpenDataContractStandard`
- Update field access patterns (`.models` → `.schema_`, `.fields` → `.properties`)

### 6.3 JSON Schema Validation

**File**: `datacontract/engines/fastjsonschema/check_jsonschema.py`

- Update to use ODCS schema structure

### 6.4 Soda Integration

**Files**: `datacontract/engines/soda/`

- Update quality rule extraction from ODCS `DataQuality` objects

---

## Part 7: Update Validation/Linting

### 7.1 Schema Resolution

**File**: `datacontract/lint/resolve.py`

```python
# Update return types
def resolve_data_contract(...) -> OpenDataContractStandard:
    ...

# Update schema validation to use ODCS schemas
# Located at: datacontract/schemas/odcs-3.1.0.schema.json
```

### 7.2 Use ODCS JSON Schema

Update schema paths:
- From: `datacontract/schemas/datacontract-1.2.*.schema.json`
- To: `datacontract/schemas/odcs-3.1.0.schema.json`

---

## Part 8: Update CLI

**File**: `datacontract/cli.py`

### 8.1 Remove Deprecated Commands

```python
# DELETE these command definitions entirely:
@app.command()
def breaking(...): ...

@app.command()
def changelog(...): ...

@app.command()
def diff(...): ...
```

### 8.2 Update Import Command

```python
@app.command(name="import")
def import_(
    format: str,
    source: str,
    # Remove --spec option - always outputs ODCS
):
```

### 8.3 Update Init Command

- Update default template to ODCS format

### 8.4 Update Help Text

- Remove references to Data Contract Specification
- Update to reference ODCS

---

## Part 9: Update Tests

### 9.1 Delete Breaking Change Tests

```
tests/test_breaking*.py  # DELETE all
```

### 9.2 Update Fixtures

Convert all DCS fixtures to ODCS format:

**Before** (`tests/fixtures/example.yaml`):
```yaml
dataContractSpecification: 1.0.0
id: my-contract
info:
  title: My Contract
  version: 1.0.0
  owner: team-a
models:
  users:
    type: table
    fields:
      id:
        type: string
        primaryKey: true
```

**After** (`tests/fixtures/example.yaml`):
```yaml
apiVersion: v3.1.0
kind: DataContract
id: my-contract
name: My Contract
version: 1.0.0
team:
  name: team-a
schema:
  - name: users
    physicalType: table
    properties:
      - name: id
        logicalType: string
        primaryKey: true
        primaryKeyPosition: 1
```

### 9.3 Update Test Assertions

```python
# Before
assert result.models["users"].fields["id"].type == "string"

# After
assert result.schema_[0].properties[0].logicalType == "string"
```

---

## Part 10: Update Dependencies

**File**: `pyproject.toml`

```toml
[project]
dependencies = [
    # Keep ODCS, consider removing DCS entirely or making optional
    "open-data-contract-standard>=3.1.0,<4.0.0",
    # Optional: keep for DCS import/export
    # "datacontract-specification>=1.2.3,<2.0.0",
    ...
]
```

---

## Part 11: Migration Order

Execute in this order to minimize broken state:

### Phase 1: Deletions
1. Delete `datacontract/breaking/` directory
2. Remove breaking/changelog/diff from CLI
3. Delete breaking change tests

### Phase 2: Core
4. Update `datacontract/model/data_contract_specification/__init__.py`
5. Update `datacontract/data_contract.py`
6. Update `datacontract/lint/resolve.py`

### Phase 3: Base Classes
7. Update `datacontract/imports/importer.py`
8. Update `datacontract/export/exporter.py`

### Phase 4: Importers (can parallelize)
9. Update all 17 importers

### Phase 5: Exporters (can parallelize)
10. Update all 22 exporters

### Phase 6: Engines
11. Update validation engines
12. Update test engines
13. Update Soda integration

### Phase 7: CLI & Tests
14. Update CLI commands
15. Update test fixtures
16. Update test assertions

### Phase 8: Cleanup
17. Update pyproject.toml
18. Update documentation
19. Update CHANGELOG

---

## Type Mapping Quick Reference

### Field Types: DCS → ODCS

| DCS `field.type` | ODCS `property.logicalType` |
|------------------|----------------------------|
| `string` | `string` |
| `int` | `integer` |
| `long` | `integer` |
| `float` | `number` |
| `double` | `number` |
| `decimal` | `number` |
| `boolean` | `boolean` |
| `date` | `date` |
| `timestamp` | `date` |
| `timestamp_tz` | `date` |
| `timestamp_ntz` | `date` |
| `time` | `string` |
| `object` | `object` |
| `array` | `array` |
| `bytes` | `array` |

### Structure Mapping

| DCS | ODCS |
|-----|------|
| `dataContractSpecification: "1.0.0"` | `apiVersion: "v3.1.0"` + `kind: "DataContract"` |
| `id` | `id` |
| `info.title` | `name` |
| `info.version` | `version` |
| `info.status` | `status` |
| `info.owner` | `team.name` |
| `info.contact.email` | `support[].url` (mailto:) |
| `info.description` | `description.purpose` |
| `terms.usage` | `description.usage` |
| `terms.limitations` | `description.limitations` |
| `terms.billing` | `price.priceAmount` + `price.priceCurrency` |
| `servicelevels.availability` | `slaProperties[property=generalAvailability]` |
| `servicelevels.retention` | `slaProperties[property=retention]` |
| `servers` | `servers` (similar) |
| `models` (dict) | `schema` (list of SchemaObject) |
| `models[name]` | `schema[].name` |
| `model.type` | `schemaObject.physicalType` |
| `model.fields` (dict) | `schemaObject.properties` (list) |
| `field.type` | `property.logicalType` |
| `field.config.postgresType` | `property.physicalType` |
| `field.primaryKey` | `property.primaryKey` + `property.primaryKeyPosition` |
| `field.required` | `property.required` |
| `field.unique` | `property.unique` |
| `field.description` | `property.description` |
| `field.classification` | `property.classification` |
| `field.tags` | `property.tags` |
| `field.examples` | `property.examples` |
| `field.quality` | `property.quality` |
| `tags` | `tags` |

---

## Verification Checklist

After migration, verify:

- [ ] `datacontract init` creates valid ODCS YAML
- [ ] `datacontract lint` validates against ODCS schema
- [ ] `datacontract import --format avro` outputs ODCS
- [ ] `datacontract import --format sql` outputs ODCS
- [ ] `datacontract import --format jsonschema` outputs ODCS
- [ ] `datacontract export --format jsonschema` works with ODCS input
- [ ] `datacontract export --format avro` works with ODCS input
- [ ] `datacontract export --format sql` works with ODCS input
- [ ] `datacontract export --format dcs` outputs old DCS format (for migration)
- [ ] `datacontract test` runs quality checks from ODCS
- [ ] All tests pass
- [ ] No references to `DataContractSpecification` remain (except DCS exporter)

---

## Version & Release

- Bump to version **1.0.0** or **2.0.0** (breaking change)
- Update CHANGELOG with migration notes
- Add migration guide for users
- Consider keeping `--format dcs` export for users who need old format