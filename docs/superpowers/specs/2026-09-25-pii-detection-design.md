# PII Detection (`datacontract/ai`) — Design

## Context

`datacontract import postgres` and `datacontract import databricks` (Unity
Catalog) build a data contract from live schema introspection, but never
populate the ODCS `classification` (`str | None`) or `criticalDataElement`
(`bool | None`) fields on `SchemaProperty`. Today the only importer that ever
sets these fields is `excel_importer.py`, and only because the source Excel
sheet has explicit "classification" / "critical data element status"
columns — there is no PII-detection logic anywhere in the codebase.

The goal: add a small, pluggable PII-detection capability under a new
`datacontract/ai` package, usable as an **opt-in** post-processing step so
importing a live Postgres or Databricks schema can automatically mark
likely-PII columns with `classification: PII` and `criticalDataElement: true`,
without changing default import behavior for anyone who doesn't ask for it.

## Non-goals

- No enum/taxonomy is introduced for `classification` — ODCS defines it as a
  free-form string, and this feature always writes the literal `"PII"`.
- No live-data sampling. Detection works off column names only.
- No wiring into importers beyond Postgres and Databricks in this pass (the
  detector itself is import-agnostic, so extending to MySQL/SQL
  Server/Oracle/Redshift later is a small follow-up, not a redesign).

## Package layout

```
datacontract/ai/
  __init__.py
  pii_detector.py             # PiiDetector ABC
  rule_based_pii_detector.py  # RuleBasedPiiDetector
  anthropic_pii_detector.py   # AnthropicPiiDetector (direct Anthropic API)
  databricks_pii_detector.py  # DatabricksPiiDetector (Databricks Model Serving)
  pii_detector_factory.py     # PiiDetectionMethod enum + PiiDetectorFactory
  annotate.py                 # mark_pii_columns()
```

This mirrors the existing `datacontract/imports/importer.py` +
`importer_factory.py` idiom: an `ABC` base class with one abstract method, a
string enum of supported methods, and a factory singleton that lazily
imports each concrete class so an unused optional dependency (`anthropic`)
is never imported unless requested.

## Core interface

```python
# datacontract/ai/pii_detector.py
from abc import ABC, abstractmethod


class PiiDetector(ABC):
    @abstractmethod
    def detect(self, column_names: list[str]) -> dict[str, bool]:
        """Return {column_name: is_pii} for a batch of column names from one table."""
```

The interface takes a **batch** of column names (all columns of one table in
a single call), not one name at a time — this lets the LLM-based detector
classify a whole table in one prompt/API call instead of one call per column.
`RuleBasedPiiDetector` just loops internally; the batching costs it nothing.

### `RuleBasedPiiDetector`

Normalizes each column name (lowercase; `_`/`-`/space treated as word
separators) and checks it against a fixed dictionary of PII-indicating terms,
matched as whole words/segments rather than raw substrings — e.g. `ssn`
matches the segment `ssn` in `user_ssn`, but does not match inside an
unrelated identifier that merely contains those three letters in sequence.
Initial term list (extend later without any interface change):

`email`, `e_mail`, `ssn`, `social_security`, `phone`, `mobile`, `address`,
`street`, `city`, `zip`, `postal`, `dob`, `birth_date`, `date_of_birth`,
`first_name`, `last_name`, `full_name`, `firstname`, `lastname`, `passport`,
`credit_card`, `card_number`, `iban`, `tax_id`, `national_id`, `driver_license`.

Pure function of the name; no config, no network, no external dependency.

### `AnthropicPiiDetector`

```python
class AnthropicPiiDetector(PiiDetector):
    def __init__(self, config: Config | None = None): ...
    def detect(self, column_names: list[str]) -> dict[str, bool]: ...
```

- Reads the API key via `Config.get_anthropic_api_key(required=True)` (see
  Config section below).
- Imports `anthropic` lazily inside `__init__`, raising `DataContractException`
  with a clear "install the extra `datacontract-cli[ai]`" message on
  `ImportError` — same pattern as `postgres_importer.postgres_connection()`'s
  handling of the missing `psycopg` extra.
- Sends one message listing all `column_names` for the current table, asking
  for a JSON object mapping each name to `true`/`false` (is this column
  likely to contain personally identifiable information based on its name).
  Uses a small/cheap model (e.g. Claude Haiku). Parses the JSON response;
  any parse failure or API error raises `DataContractException` (fails the
  import loudly rather than silently skipping detection).

### `DatabricksPiiDetector`

For teams running Claude behind a self-hosted **Databricks Model Serving**
endpoint (Foundation Model APIs / external model) rather than calling
Anthropic directly:

```python
class DatabricksPiiDetector(PiiDetector):
    def __init__(self, config: Config | None = None): ...
    def detect(self, column_names: list[str]) -> dict[str, bool]: ...
```

- Builds a `databricks.sdk.WorkspaceClient` exactly like
  `unity_importer.import_unity_from_api()` already does —
  `WorkspaceClient(profile=profile)` if
  `Config.get_databricks_profile()` is set, else
  `WorkspaceClient(host=..., token=...)` from
  `get_databricks_server_hostname()` / `get_databricks_token()`. No new
  Databricks credentials are introduced; this reuses the same config anyone
  running `import databricks` already has.
- Calls the SDK's native
  `workspace_client.serving_endpoints.query(name=endpoint, messages=[ChatMessage(role=ChatMessageRole.USER, content=prompt)])`
  (`databricks.sdk.service.serving.ServingEndpointsAPI.query`) — **not** the
  deprecated `get_open_ai_client()` wrapper, and no new dependency, since
  `databricks-sdk` is already required by the `databricks` extra that
  `import databricks` itself needs.
- `endpoint` is a new required config value (see Config section) — there is
  no sensible default, since the endpoint name is specific to each
  workspace's deployment.
- The Databricks `query()` API has no `response_format`/JSON-mode
  parameter (confirmed against `databricks/sdk/service/serving.py`), so the
  prompt asks for a JSON object in the same way `AnthropicPiiDetector` does,
  and the response text is extracted from `QueryEndpointResponse.choices`
  and parsed the same way. Any missing endpoint config, API error, or parse
  failure raises `DataContractException`.

### `PiiDetectorFactory`

```python
# datacontract/ai/pii_detector_factory.py
class PiiDetectionMethod(str, Enum):
    rule = "rule"
    anthropic = "anthropic"
    databricks = "databricks"

class PiiDetectorFactory:
    def register_lazy_detector(self, name: str, module_path: str, class_name: str) -> None: ...
    def create(self, name: str, config: Config | None = None) -> PiiDetector: ...

pii_detector_factory = PiiDetectorFactory()
pii_detector_factory.register_lazy_detector(PiiDetectionMethod.rule, "datacontract.ai.rule_based_pii_detector", "RuleBasedPiiDetector")
pii_detector_factory.register_lazy_detector(PiiDetectionMethod.anthropic, "datacontract.ai.anthropic_pii_detector", "AnthropicPiiDetector")
pii_detector_factory.register_lazy_detector(PiiDetectionMethod.databricks, "datacontract.ai.databricks_pii_detector", "DatabricksPiiDetector")
```

## Integration: post-processing pass

`mark_pii_columns()` runs after an importer has already built the full
`OpenDataContractStandard`, exactly where `report_unmapped_types(odcs)`
already runs today in `postgres_importer.py`:

```python
# datacontract/ai/annotate.py
def mark_pii_columns(odcs: OpenDataContractStandard, detector: PiiDetector) -> None:
    for schema_obj in odcs.schema_ or []:
        properties = list(walk_properties(schema_obj.properties))
        candidates = [p for p in properties if p.classification is None]
        if not candidates:
            continue
        results = detector.detect([p.name for p in candidates])
        for prop in candidates:
            if results.get(prop.name):
                prop.classification = "PII"
                prop.criticalDataElement = True
```

- Never overwrites a `classification` an importer already set (e.g. a future
  Excel-imported contract re-processed through this — though that's not a
  current call site, the guard is cheap and correct).
- Batches per schema object (table), matching the LLM detector's
  one-call-per-table design.
- `walk_properties()` is extracted from the existing recursive walker inside
  `datacontract/imports/odcs_helper.py:report_unmapped_types()` into a shared
  generator (`def walk_properties(props: List[SchemaProperty] | None) -> Iterator[SchemaProperty]`),
  since it now has two real callers — satisfies this repo's own
  "abstract only with 2+ callers" convention (AGENTS.md). `report_unmapped_types`
  is refactored to use it; behavior unchanged.

## CLI wiring

Two new options on `datacontract import postgres` and
`datacontract import databricks`:

- `--detect-pii` (flag, default `False`): opt-in; when unset, behavior and
  output are byte-for-byte identical to today.
- `--pii-detector rule|anthropic|databricks` (default `rule`): which detector
  to use. `rule` needs no credentials or extra dependency; `anthropic`
  requires the Anthropic API key; `databricks` requires the existing
  Databricks credentials plus a serving endpoint name.

Both flow through the existing `import_args` dict (already how e.g.
`--schema`/`--table` reach `import_postgres_from_connector`), and, only when
`detect_pii` is true, the importer calls:

```python
mark_pii_columns(odcs, pii_detector_factory.create(pii_detector, config))
```

right alongside the existing `report_unmapped_types(odcs)` call, before
returning.

## Config

`datacontract/config/settings.py` gains one field, following the exact
convention used for `postgres_password` etc.:

```python
anthropic_api_key: SecretStr | None = None      # env: DATACONTRACT_ANTHROPIC_API_KEY
databricks_pii_endpoint: str | None = None      # env: DATACONTRACT_DATABRICKS_PII_ENDPOINT
```

with `get_anthropic_api_key(required: bool = False)` and
`get_databricks_pii_endpoint(required: bool = False)` accessors alongside the
other `get_*` methods. `DatabricksPiiDetector` otherwise reuses the *existing*
`databricks_profile` / `databricks_server_hostname` / `databricks_token`
fields and accessors already used by `import databricks` — no duplicate
credential config for the same workspace.

## Dependencies

`pyproject.toml` gains an `ai` extra for the direct-Anthropic-API detector:

```toml
ai = ["anthropic>=0.40"]
```

Installed via `pip install -e '.[ai]'`, only needed for
`--pii-detector anthropic`. `--pii-detector rule` (the default) needs none of
this. `--pii-detector databricks` needs no *new* dependency either — it reuses
`databricks-sdk`, which the `databricks` extra already installs for
`import databricks` itself.

## Testing

- `tests/test_ai_pii_detector.py`:
  - `RuleBasedPiiDetector` on a table of known-PII names (`email`,
    `customer_email`, `ssn`, `phone_number`, `first_name`, `home_address`)
    and known-non-PII names (`order_id`, `quantity`, `created_at`,
    `is_active`) — assert exact true/false per name.
  - `mark_pii_columns()` with a stub `PiiDetector` — assert matched columns
    get `classification="PII"` + `criticalDataElement=True`, unmatched
    columns are untouched, and a column with a pre-existing `classification`
    is never overwritten even if the stub would flag it.
  - `PiiDetectorFactory` — `create("rule")` returns a working detector
    without importing `anthropic`; `create("anthropic")` raises a clear
    `DataContractException` if `anthropic` isn't installed.
  - `AnthropicPiiDetector` — with `anthropic.Anthropic` mocked via
    `unittest.mock.patch`, assert the request contains the expected column
    names and the response JSON is parsed into the right `dict[str, bool]`.
    No real network calls anywhere in the suite.
  - `DatabricksPiiDetector` — with `WorkspaceClient.serving_endpoints.query`
    mocked, assert it's called with the configured endpoint name and the
    expected messages, and that a `QueryEndpointResponse`-shaped mock is
    parsed into the right `dict[str, bool]`; assert a clear
    `DataContractException` when `DATACONTRACT_DATABRICKS_PII_ENDPOINT` is
    unset. No real network/API calls anywhere in the suite.
- `tests/test_import_postgres.py`: add a `customer_email` column to the
  `orders` fixture table; existing tests updated to expect it present but
  unclassified (flag defaults off); new test
  `test_import_postgres_detects_pii_with_rule_based_detector` passes
  `detect_pii=True` and asserts `customer_email` comes back
  `classification: PII`, `criticalDataElement: true`, while `order_id` etc.
  do not.
- `tests/test_import_unity_file.py`: same pattern — add an `email` column to
  the Unity fixture, assert `--detect-pii` marks it correctly via
  `import databricks --detect-pii`.

## Docs

One sentence each added to `docs/docs/imports/postgres.md` and
`docs/docs/imports/databricks.md` describing the new flags. The CLI
`--help` reference pages are auto-generated from the Typer options (see
`update_command_docs.py`), so no manual command-docs edits are needed.

## Verification

- `pytest tests/test_ai_pii_detector.py tests/test_import_postgres.py tests/test_import_unity_file.py -v`
  (Postgres tests need Docker running for the `testcontainers` container).
- `ruff check` / `ruff format --diff` on all new/changed files.
- Manual: `datacontract import postgres --source localhost --database ... --detect-pii` against a schema with an obvious PII column (e.g. `email`) and inspect the output YAML for `classification: PII` / `criticalDataElement: true`.
