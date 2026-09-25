# PII Detection (`datacontract/ai`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a pluggable `datacontract/ai` package that detects likely-PII columns by name and marks them `classification: PII` / `criticalDataElement: true`, wired in as an opt-in `--detect-pii` flag on `datacontract import postgres` and `datacontract import databricks`.

**Architecture:** A `PiiDetector` ABC with three implementations (`RuleBasedPiiDetector`, `AnthropicPiiDetector`, `DatabricksPiiDetector`) registered in a lazy-loading `PiiDetectorFactory`, mirroring the existing `ImporterFactory` idiom. A single post-processing function, `mark_pii_columns()`, walks the already-built `OpenDataContractStandard` and calls the chosen detector once per table — the same place `report_unmapped_types()` already runs today.

**Tech Stack:** Python, Pydantic (`open_data_contract_standard.model`), Typer (CLI), `anthropic` SDK (new optional dependency), `databricks-sdk` (already a dependency of the `databricks` extra), pytest, `testcontainers` (existing Postgres integration tests).

**Spec:** `docs/superpowers/specs/2026-09-25-pii-detection-design.md`

## Global Constraints

- `--detect-pii` defaults to `False` on every wired command; existing import behavior/output is unchanged unless a caller opts in.
- `--pii-detector` accepts exactly `rule` (default), `anthropic`, `databricks` — no other values.
- The `classification` field is always written as the literal string `"PII"` — no new enum/taxonomy.
- Detection only ever looks at column names — no live-data sampling, no reading actual row values.
- `mark_pii_columns()` never overwrites a `SchemaProperty` that already has a non-`None` `classification`.
- `mark_pii_columns()` batches per schema object (table): one `detector.detect(...)` call per table, not per column, and it is skipped entirely for a table where every column is already classified.
- New Config fields: `anthropic_api_key: SecretStr | None` (env `DATACONTRACT_ANTHROPIC_API_KEY`), `databricks_pii_endpoint: str | None` (env `DATACONTRACT_DATABRICKS_PII_ENDPOINT`). `DatabricksPiiDetector` otherwise reuses the existing `databricks_profile` / `databricks_server_hostname` / `databricks_token` fields — no duplicate Databricks credentials.
- New `pyproject.toml` extra: `ai = ["anthropic>=0.40.0,<1.0.0"]`, included in the `all` meta-extra. `DatabricksPiiDetector` needs no new dependency (reuses `databricks-sdk` from the existing `databricks` extra).
- `DatabricksPiiDetector` calls the SDK's native `workspace_client.serving_endpoints.query(...)` — never the deprecated `get_open_ai_client()` wrapper.

## Review Focus

- Mixed-case / punctuated column names (`Email`, `SSN_NUMBER`, `phone-number`) must still match after the rule detector normalizes them, and a column that merely *contains* a PII substring without it being a whole segment (`telephone_book_id`) must **not** false-positive on `phone`. Covered in Task 1.
- A property that already has a `classification` set (e.g. from a future Excel-derived contract passed back through `mark_pii_columns`, or a nested struct field) must never be overwritten, even when the detector would otherwise flag it. Covered in Task 2.
- A table where every column is already classified must skip the detector call entirely — no wasted/costly API call for `anthropic`/`databricks`. Covered in Task 2.
- Choosing `--pii-detector anthropic` or `--pii-detector databricks` without the required credentials (API key, or Databricks endpoint/host/token) must fail with a clear `DataContractException` naming the missing env var, not a generic stack trace or a silently-empty result. Covered in Tasks 5 and 6.
- A malformed/unparseable JSON response from the Anthropic API or the Databricks serving endpoint must raise a clear `DataContractException`, not crash with an uncaught `json.JSONDecodeError` or silently mark zero columns. Covered in Tasks 5 and 6.

---

## File Structure

Create:
- `datacontract/ai/__init__.py` — empty, marks the package.
- `datacontract/ai/pii_detector.py` — `PiiDetector` ABC.
- `datacontract/ai/rule_based_pii_detector.py` — `RuleBasedPiiDetector`.
- `datacontract/ai/anthropic_pii_detector.py` — `AnthropicPiiDetector`.
- `datacontract/ai/databricks_pii_detector.py` — `DatabricksPiiDetector`.
- `datacontract/ai/pii_detector_factory.py` — `PiiDetectionMethod` enum + `PiiDetectorFactory` + module-level `pii_detector_factory` singleton.
- `datacontract/ai/annotate.py` — `mark_pii_columns()`.
- `tests/test_ai_pii_detector.py` — unit tests for everything above.

Modify:
- `datacontract/imports/odcs_helper.py` — extract `walk_properties()` from `report_unmapped_types()`.
- `datacontract/config/settings.py` — add `anthropic_api_key`, `databricks_pii_endpoint` fields + accessors.
- `tests/test_config.py` — accessor tests for the two new fields.
- `datacontract/imports/postgres_importer.py` — wire `detect_pii`/`pii_detector` through.
- `datacontract/imports/unity_importer.py` — wire `detect_pii`/`pii_detector` through.
- `datacontract/command_import.py` — add `--detect-pii`/`--pii-detector` to `import_postgres`, `import_databricks`, `import_unity`.
- `tests/fixtures/postgres/data/import.sql`, `tests/test_import_postgres.py` — PII fixture column + tests.
- `tests/fixtures/databricks-unity/import/unity_table_schema.json`, `tests/fixtures/databricks-unity/import/datacontract.yaml`, `tests/test_import_unity_file.py` — PII fixture column + tests.
- `pyproject.toml` — new `ai` extra, added to `all`.
- `docs/docs/imports/postgres.md`, `docs/docs/imports/databricks.md` — one line each.
- `CHANGELOG.md` — one line.

---

### Task 1: `PiiDetector` ABC + `RuleBasedPiiDetector`

**Files:**
- Create: `datacontract/ai/__init__.py` (empty file)
- Create: `datacontract/ai/pii_detector.py`
- Create: `datacontract/ai/rule_based_pii_detector.py`
- Test: `tests/test_ai_pii_detector.py`

**Interfaces:**
- Produces: `PiiDetector` (ABC, `datacontract/ai/pii_detector.py`) with `__init__(self, config: "Config | None" = None)` storing `self.config`, and abstract method `detect(self, column_names: list[str]) -> dict[str, bool]`.
- Produces: `RuleBasedPiiDetector(PiiDetector)` (`datacontract/ai/rule_based_pii_detector.py`), no additional constructor.

- [ ] **Step 1: Write the failing test**

Create `tests/test_ai_pii_detector.py`:

```python
from datacontract.ai.rule_based_pii_detector import RuleBasedPiiDetector


def test_rule_based_detector_matches_known_pii_column_names():
    detector = RuleBasedPiiDetector()

    result = detector.detect(
        ["email", "customer_email", "SSN", "user_ssn", "phone_number", "first_name", "home_address", "date_of_birth"]
    )

    assert result == {
        "email": True,
        "customer_email": True,
        "SSN": True,
        "user_ssn": True,
        "phone_number": True,
        "first_name": True,
        "home_address": True,
        "date_of_birth": True,
    }


def test_rule_based_detector_does_not_match_non_pii_column_names():
    detector = RuleBasedPiiDetector()

    result = detector.detect(["order_id", "quantity", "created_at", "is_active", "telephone_book_id"])

    assert result == {
        "order_id": False,
        "quantity": False,
        "created_at": False,
        "is_active": False,
        "telephone_book_id": False,
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ai_pii_detector.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'datacontract.ai'`

- [ ] **Step 3: Write minimal implementation**

Create `datacontract/ai/__init__.py` (empty).

Create `datacontract/ai/pii_detector.py`:

```python
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datacontract.config import Config


class PiiDetector(ABC):
    """Decides whether column names are likely to contain personally identifiable information."""

    def __init__(self, config: "Config | None" = None) -> None:
        self.config = config

    @abstractmethod
    def detect(self, column_names: list[str]) -> dict[str, bool]:
        """Return {column_name: is_pii} for a batch of column names from one table."""
```

Create `datacontract/ai/rule_based_pii_detector.py`:

```python
import re

from datacontract.ai.pii_detector import PiiDetector

_PII_TERMS = [
    "email",
    "e_mail",
    "ssn",
    "social_security",
    "phone",
    "mobile",
    "address",
    "street",
    "city",
    "zip",
    "postal",
    "dob",
    "birth_date",
    "date_of_birth",
    "first_name",
    "last_name",
    "full_name",
    "firstname",
    "lastname",
    "passport",
    "credit_card",
    "card_number",
    "iban",
    "tax_id",
    "national_id",
    "driver_license",
]
_PII_TERM_SEGMENTS = [term.split("_") for term in _PII_TERMS]


class RuleBasedPiiDetector(PiiDetector):
    """Matches column names against a fixed dictionary of PII-indicating terms. No config, no network."""

    def detect(self, column_names: list[str]) -> dict[str, bool]:
        return {name: self._is_pii(name) for name in column_names}

    @staticmethod
    def _is_pii(column_name: str) -> bool:
        segments = re.sub(r"[^a-z0-9]+", "_", column_name.lower()).strip("_").split("_")
        return any(_contains_subsequence(segments, term_segments) for term_segments in _PII_TERM_SEGMENTS)


def _contains_subsequence(segments: list[str], term_segments: list[str]) -> bool:
    n = len(term_segments)
    return any(segments[i : i + n] == term_segments for i in range(len(segments) - n + 1))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ai_pii_detector.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add datacontract/ai/__init__.py datacontract/ai/pii_detector.py datacontract/ai/rule_based_pii_detector.py tests/test_ai_pii_detector.py
git commit -m "feat: add PiiDetector interface and rule-based PII detector"
```

---

### Task 2: `walk_properties()` + `mark_pii_columns()`

**Files:**
- Modify: `datacontract/imports/odcs_helper.py` (the `report_unmapped_types` function, currently defined with an inner `walk()` closure)
- Create: `datacontract/ai/annotate.py`
- Test: `tests/test_ai_pii_detector.py`
- Test (regression): `tests/test_import_unmapped_types.py` (must keep passing unmodified)

**Interfaces:**
- Consumes: `PiiDetector` from Task 1 (`datacontract/ai/pii_detector.py`).
- Produces: `walk_properties(props: List[SchemaProperty] | None, prefix: str = "") -> Iterator[Tuple[str, SchemaProperty]]` in `datacontract/imports/odcs_helper.py`, yielding every property recursively (struct `properties`, array `items`, map `key`/`value`) paired with its dotted path.
- Produces: `mark_pii_columns(odcs: OpenDataContractStandard, detector: PiiDetector) -> None` in `datacontract/ai/annotate.py`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_ai_pii_detector.py`:

```python
from open_data_contract_standard.model import OpenDataContractStandard

from datacontract.ai.annotate import mark_pii_columns
from datacontract.ai.pii_detector import PiiDetector
from datacontract.imports.odcs_helper import create_odcs, create_property, create_schema_object


class _StubDetector(PiiDetector):
    def __init__(self, matches: set):
        super().__init__(config=None)
        self.matches = matches
        self.calls: list = []

    def detect(self, column_names: list[str]) -> dict[str, bool]:
        self.calls.append(list(column_names))
        return {name: name in self.matches for name in column_names}


def _odcs_with_properties(properties):
    schema_obj = create_schema_object(name="orders", properties=properties)
    odcs = create_odcs()
    odcs.schema_ = [schema_obj]
    return odcs, schema_obj


def test_mark_pii_columns_sets_classification_and_critical_flag():
    email = create_property(name="email", logical_type="string")
    order_id = create_property(name="order_id", logical_type="string")
    odcs, _ = _odcs_with_properties([email, order_id])
    detector = _StubDetector(matches={"email"})

    mark_pii_columns(odcs, detector)

    assert email.classification == "PII"
    assert email.criticalDataElement is True
    assert order_id.classification is None
    assert order_id.criticalDataElement is None


def test_mark_pii_columns_never_overwrites_existing_classification():
    email = create_property(name="email", logical_type="string", classification="public")
    odcs, _ = _odcs_with_properties([email])
    detector = _StubDetector(matches={"email"})

    mark_pii_columns(odcs, detector)

    assert email.classification == "public"


def test_mark_pii_columns_skips_detector_call_when_all_columns_classified():
    email = create_property(name="email", logical_type="string", classification="public")
    odcs, _ = _odcs_with_properties([email])
    detector = _StubDetector(matches={"email"})

    mark_pii_columns(odcs, detector)

    assert detector.calls == []


def test_mark_pii_columns_recurses_into_struct_properties():
    nested_email = create_property(name="email", logical_type="string")
    contact = create_property(name="contact", logical_type="object", properties=[nested_email])
    odcs, _ = _odcs_with_properties([contact])
    detector = _StubDetector(matches={"email"})

    mark_pii_columns(odcs, detector)

    assert nested_email.classification == "PII"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ai_pii_detector.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'datacontract.ai.annotate'`

- [ ] **Step 3: Write minimal implementation**

In `datacontract/imports/odcs_helper.py`, change the `typing` import line from:

```python
from typing import Any, Dict, List
```

to:

```python
from typing import Any, Dict, Iterator, List, Tuple
```

Then replace the body of `report_unmapped_types` (the function starting `def report_unmapped_types(odcs: OpenDataContractStandard, fallback: str | None = None) -> None:`, currently containing an inner `def walk(props, prefix):` closure) with:

```python
def walk_properties(props: List[SchemaProperty] | None, prefix: str = "") -> Iterator[Tuple[str, SchemaProperty]]:
    """Yield (qualified_path, property) for every property, recursing into struct/array/map nesting."""
    for prop in props or []:
        path = f"{prefix}{prop.name}"
        yield path, prop
        yield from walk_properties(prop.properties, f"{path}.")
        if prop.items:
            yield from walk_properties([prop.items], f"{path}.")
        if prop.map:
            yield from walk_properties([side for side in (prop.map.key, prop.map.value) if side], f"{path}.")


def report_unmapped_types(odcs: OpenDataContractStandard, fallback: str | None = None) -> None:
    """Warn once about every property imported with ``logical_type=None``; ``fallback`` fills it in
    where a later ``datacontract test`` needs every property typed."""
    unmapped = []
    qualify = len(odcs.schema_ or []) > 1

    for schema_obj in odcs.schema_ or []:
        prefix = f"{schema_obj.name}." if qualify else ""
        for path, prop in walk_properties(schema_obj.properties, prefix):
            if prop.logicalType is None:
                unmapped.append((path, prop.physicalType))
                prop.logicalType = fallback

    if not unmapped:
        return
    imported_as = f"as {fallback}" if fallback else "without a logicalType"
    listed = ", ".join(f"{name} ({physical_type})" if physical_type else name for name, physical_type in unmapped[:5])
    if len(unmapped) > 5:
        listed += f" and {len(unmapped) - 5} others."
    count = f"{len(unmapped)} columns have" if len(unmapped) > 1 else "1 column has"
    logger.warning(
        f"{count} no defined mapping to logicalType and will be imported {imported_as}:\n{listed}\n"
        "You may propose an updated mapping on GitHub: https://github.com/datacontract/datacontract-cli/issues"
    )
```

Create `datacontract/ai/annotate.py`:

```python
from typing import List

from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty

from datacontract.ai.pii_detector import PiiDetector
from datacontract.imports.odcs_helper import walk_properties


def mark_pii_columns(odcs: OpenDataContractStandard, detector: PiiDetector) -> None:
    """Mark likely-PII columns with classification="PII" and criticalDataElement=True.

    Never overwrites a property that already has a classification, and never calls
    the detector for a table where every column is already classified.
    """
    for schema_obj in odcs.schema_ or []:
        properties: List[SchemaProperty] = [prop for _, prop in walk_properties(schema_obj.properties)]
        candidates = [prop for prop in properties if prop.classification is None]
        if not candidates:
            continue
        results = detector.detect([prop.name for prop in candidates])
        for prop in candidates:
            if results.get(prop.name):
                prop.classification = "PII"
                prop.criticalDataElement = True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ai_pii_detector.py tests/test_import_unmapped_types.py -v`
Expected: PASS (all tests, including the pre-existing `test_import_unmapped_types.py` regression suite)

- [ ] **Step 5: Commit**

```bash
git add datacontract/imports/odcs_helper.py datacontract/ai/annotate.py tests/test_ai_pii_detector.py
git commit -m "feat: add mark_pii_columns post-processing pass over imported schemas"
```

---

### Task 3: `PiiDetectorFactory`

**Files:**
- Create: `datacontract/ai/pii_detector_factory.py`
- Test: `tests/test_ai_pii_detector.py`

**Interfaces:**
- Consumes: `RuleBasedPiiDetector` from Task 1.
- Produces: `PiiDetectionMethod(str, Enum)` with values `rule`, `anthropic`, `databricks`; `PiiDetectorFactory` with `register_lazy_detector(name, module_path, class_name)` and `create(name, config=None) -> PiiDetector`; module-level singleton `pii_detector_factory`, pre-registered with `rule` → `RuleBasedPiiDetector` (the `anthropic`/`databricks` registrations are added in Tasks 5 and 6).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_ai_pii_detector.py`:

```python
import pytest

from datacontract.ai.pii_detector_factory import pii_detector_factory
from datacontract.ai.rule_based_pii_detector import RuleBasedPiiDetector


def test_factory_creates_rule_based_detector():
    detector = pii_detector_factory.create("rule")

    assert isinstance(detector, RuleBasedPiiDetector)


def test_factory_raises_for_unknown_detector_name():
    with pytest.raises(ValueError, match="not supported"):
        pii_detector_factory.create("does-not-exist")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ai_pii_detector.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'datacontract.ai.pii_detector_factory'`

- [ ] **Step 3: Write minimal implementation**

Create `datacontract/ai/pii_detector_factory.py`:

```python
import importlib
import typing
from enum import Enum

from datacontract.ai.pii_detector import PiiDetector

if typing.TYPE_CHECKING:
    from datacontract.config import Config


class PiiDetectionMethod(str, Enum):
    rule = "rule"
    anthropic = "anthropic"
    databricks = "databricks"


class PiiDetectorFactory:
    def __init__(self) -> None:
        self._lazy_detectors: dict[str, tuple[str, str]] = {}

    def register_lazy_detector(self, name: str, module_path: str, class_name: str) -> None:
        self._lazy_detectors[name] = (module_path, class_name)

    def create(self, name: str, config: "Config | None" = None) -> PiiDetector:
        if name not in self._lazy_detectors:
            raise ValueError(f"The '{name}' PII detector is not supported.")
        module_path, class_name = self._lazy_detectors[name]
        module = importlib.import_module(module_path)
        detector_class = getattr(module, class_name)
        return detector_class(config)


pii_detector_factory = PiiDetectorFactory()
pii_detector_factory.register_lazy_detector(
    PiiDetectionMethod.rule, "datacontract.ai.rule_based_pii_detector", "RuleBasedPiiDetector"
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ai_pii_detector.py -v`
Expected: PASS (all tests so far)

- [ ] **Step 5: Commit**

```bash
git add datacontract/ai/pii_detector_factory.py tests/test_ai_pii_detector.py
git commit -m "feat: add PiiDetectorFactory with lazy detector registration"
```

---

### Task 4: Config fields for Anthropic and Databricks PII detection

**Files:**
- Modify: `datacontract/config/settings.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `Config.anthropic_api_key: SecretStr | None`, `Config.databricks_pii_endpoint: str | None`, `Config.get_anthropic_api_key(required: bool = False) -> str | None`, `Config.get_databricks_pii_endpoint(required: bool = False) -> str | None`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_config.py` (near the other `get_*` accessor tests, e.g. next to `test_accessors_unwrap_secrets`):

```python
def test_anthropic_api_key_accessor():
    assert Config(anthropic_api_key="secret").get_anthropic_api_key() == "secret"


def test_anthropic_api_key_required_raises_when_missing(monkeypatch):
    monkeypatch.delenv("DATACONTRACT_ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(DataContractException, match="DATACONTRACT_ANTHROPIC_API_KEY"):
        Config.model_construct().get_anthropic_api_key(required=True)


def test_databricks_pii_endpoint_accessor():
    assert Config(databricks_pii_endpoint="my-endpoint").get_databricks_pii_endpoint() == "my-endpoint"


def test_databricks_pii_endpoint_required_raises_when_missing(monkeypatch):
    monkeypatch.delenv("DATACONTRACT_DATABRICKS_PII_ENDPOINT", raising=False)

    with pytest.raises(DataContractException, match="DATACONTRACT_DATABRICKS_PII_ENDPOINT"):
        Config.model_construct().get_databricks_pii_endpoint(required=True)
```

If `DataContractException` is not already imported at the top of `tests/test_config.py`, add `from datacontract.model.exceptions import DataContractException` there (check first — the existing `test_required_accessor_raises_for_missing_values` test imports it locally inside the test function; either match that local-import style or hoist it, whichever the file already does consistently).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v -k "anthropic or databricks_pii"`
Expected: FAIL with `pydantic_core._pydantic_core.ValidationError` (unknown field `anthropic_api_key`/`databricks_pii_endpoint`) or `AttributeError: 'Config' object has no attribute 'get_anthropic_api_key'`

- [ ] **Step 3: Write minimal implementation**

In `datacontract/config/settings.py`, add a new field section right before the `# athena` comment (the section currently starting `# athena (credentials come from the s3_* options)`):

```python
    # anthropic (used by --pii-detector anthropic)
    anthropic_api_key: SecretStr | None = None

```

In the same file, in the existing `# databricks` field section, add one field after `databricks_profile: str | None = None`:

```python
    databricks_profile: str | None = None
    databricks_pii_endpoint: str | None = None  # used by --pii-detector databricks
```

In the accessors section, add a new `# --- anthropic ---` block right before the existing `# --- athena ---` accessors block:

```python
    # --- anthropic ---
    def get_anthropic_api_key(self, required: bool = False) -> str | None:
        return self._str_option("anthropic_api_key", required)

```

And in the existing `# --- databricks ---` accessors block, add one accessor after `get_databricks_profile`:

```python
    def get_databricks_profile(self, required: bool = False) -> str | None:
        return self._str_option("databricks_profile", required)

    def get_databricks_pii_endpoint(self, required: bool = False) -> str | None:
        return self._str_option("databricks_pii_endpoint", required)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (all tests, including the new ones)

- [ ] **Step 5: Commit**

```bash
git add datacontract/config/settings.py tests/test_config.py
git commit -m "feat: add anthropic_api_key and databricks_pii_endpoint config options"
```

---

### Task 5: `AnthropicPiiDetector`

**Files:**
- Modify: `pyproject.toml` (new `ai` extra)
- Modify: `datacontract/ai/pii_detector_factory.py` (register `anthropic`)
- Create: `datacontract/ai/anthropic_pii_detector.py`
- Test: `tests/test_ai_pii_detector.py`

**Interfaces:**
- Consumes: `PiiDetector` (Task 1), `Config.get_anthropic_api_key` (Task 4), `DataContractException` (`datacontract/model/exceptions.py`, signature `DataContractException(type, name, reason, engine="datacontract-cli", original_exception=None)`).
- Produces: `AnthropicPiiDetector(PiiDetector)` in `datacontract/ai/anthropic_pii_detector.py`; `pii_detector_factory` now also resolves `"anthropic"`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_ai_pii_detector.py`:

```python
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

from datacontract.config import Config
from datacontract.model.exceptions import DataContractException


def test_anthropic_detector_parses_response(monkeypatch):
    from datacontract.ai.anthropic_pii_detector import AnthropicPiiDetector

    fake_response = SimpleNamespace(content=[SimpleNamespace(text='{"email": true, "order_id": false}')])
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response
    fake_anthropic_module = SimpleNamespace(Anthropic=MagicMock(return_value=fake_client))
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic_module)

    detector = AnthropicPiiDetector(Config(anthropic_api_key="key"))
    result = detector.detect(["email", "order_id"])

    assert result == {"email": True, "order_id": False}
    call_kwargs = fake_client.messages.create.call_args.kwargs
    assert "email" in call_kwargs["messages"][0]["content"]
    assert "order_id" in call_kwargs["messages"][0]["content"]


def test_anthropic_detector_requires_api_key(monkeypatch):
    from datacontract.ai.anthropic_pii_detector import AnthropicPiiDetector

    monkeypatch.delenv("DATACONTRACT_ANTHROPIC_API_KEY", raising=False)
    detector = AnthropicPiiDetector(Config.model_construct())

    with pytest.raises(DataContractException, match="DATACONTRACT_ANTHROPIC_API_KEY"):
        detector.detect(["email"])


def test_anthropic_detector_raises_when_package_missing(monkeypatch):
    from datacontract.ai.anthropic_pii_detector import AnthropicPiiDetector

    monkeypatch.setitem(sys.modules, "anthropic", None)
    detector = AnthropicPiiDetector(Config(anthropic_api_key="key"))

    with pytest.raises(DataContractException, match=r"datacontract-cli\[ai\]"):
        detector.detect(["email"])


def test_anthropic_detector_raises_on_malformed_response(monkeypatch):
    from datacontract.ai.anthropic_pii_detector import AnthropicPiiDetector

    fake_response = SimpleNamespace(content=[SimpleNamespace(text="not json")])
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response
    fake_anthropic_module = SimpleNamespace(Anthropic=MagicMock(return_value=fake_client))
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic_module)

    detector = AnthropicPiiDetector(Config(anthropic_api_key="key"))

    with pytest.raises(DataContractException, match="Could not classify columns"):
        detector.detect(["email"])
```

Add `import pytest` at the top of `tests/test_ai_pii_detector.py` if not already present from an earlier task.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ai_pii_detector.py -v -k anthropic`
Expected: FAIL with `ModuleNotFoundError: No module named 'datacontract.ai.anthropic_pii_detector'`

- [ ] **Step 3: Write minimal implementation**

In `pyproject.toml`, add a new extra right after the `protobuf` extra (before the `all` meta-extra comment block):

```toml
ai = [
  "anthropic>=0.40.0,<1.0.0",
]

```

And update the `all` extra to include it:

```toml
all = [
  "datacontract-cli[avro,kafka,bigquery,csv,excel,snowflake,postgres,redshift,mysql,dataframe,databricks,sqlserver,s3,gcs,azure,athena,trino,exasol,impala,dbml,duckdb,iceberg,parquet,rdf,api,protobuf,oracle,ai]"
]
```

Create `datacontract/ai/anthropic_pii_detector.py`:

```python
import json

from datacontract.ai.pii_detector import PiiDetector
from datacontract.model.exceptions import DataContractException

_MODEL = "claude-haiku-4-5-20251001"

_PROMPT_TEMPLATE = (
    "For each of the following database column names, decide whether it is likely to contain "
    "personally identifiable information (PII) such as names, emails, phone numbers, addresses, "
    "government IDs, or other data that identifies an individual person. "
    "Respond with ONLY a JSON object mapping each column name to true or false, no other text.\n\n"
    "Column names: {column_names}"
)


class AnthropicPiiDetector(PiiDetector):
    """Classifies column names as PII by calling the Anthropic API directly."""

    def detect(self, column_names: list[str]) -> dict[str, bool]:
        try:
            import anthropic
        except ImportError as e:
            raise DataContractException(
                type="anthropic-connection",
                name="anthropic extra missing",
                reason="Install the extra datacontract-cli[ai] to use --pii-detector anthropic",
                engine="datacontract-cli",
                original_exception=e,
            )

        api_key = self.config.get_anthropic_api_key(required=True)
        client = anthropic.Anthropic(api_key=api_key)
        prompt = _PROMPT_TEMPLATE.format(column_names=json.dumps(column_names))
        try:
            response = client.messages.create(
                model=_MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            result = json.loads(response.content[0].text)
        except Exception as e:
            raise DataContractException(
                type="anthropic-connection",
                name="anthropic pii detection failed",
                reason=f"Could not classify columns via the Anthropic API: {e}",
                engine="datacontract-cli",
                original_exception=e,
            )
        return {name: bool(result.get(name, False)) for name in column_names}
```

In `datacontract/ai/pii_detector_factory.py`, add one more registration line after the existing `rule` registration:

```python
pii_detector_factory.register_lazy_detector(
    PiiDetectionMethod.anthropic, "datacontract.ai.anthropic_pii_detector", "AnthropicPiiDetector"
)
```

- [ ] **Step 4: Install the new extra and run tests to verify they pass**

Run: `uv pip install -e '.[ai]'` (or `pip install -e '.[ai]'`), then `pytest tests/test_ai_pii_detector.py -v -k anthropic`
Expected: PASS (all 4 anthropic tests)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml datacontract/ai/anthropic_pii_detector.py datacontract/ai/pii_detector_factory.py tests/test_ai_pii_detector.py
git commit -m "feat: add AnthropicPiiDetector calling the Anthropic API directly"
```

---

### Task 6: `DatabricksPiiDetector`

**Files:**
- Modify: `datacontract/ai/pii_detector_factory.py` (register `databricks`)
- Create: `datacontract/ai/databricks_pii_detector.py`
- Test: `tests/test_ai_pii_detector.py`

**Interfaces:**
- Consumes: `PiiDetector` (Task 1), `Config.get_databricks_pii_endpoint` / `get_databricks_profile` / `get_databricks_server_hostname` / `get_databricks_token` (Task 4 + existing), `databricks.sdk.WorkspaceClient`, `databricks.sdk.service.serving.ChatMessage`/`ChatMessageRole` (already available via the `databricks` extra, same as `datacontract/imports/unity_importer.py`).
- Produces: `DatabricksPiiDetector(PiiDetector)` in `datacontract/ai/databricks_pii_detector.py`; `pii_detector_factory` now also resolves `"databricks"`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_ai_pii_detector.py`:

```python
def test_databricks_detector_queries_serving_endpoint(monkeypatch):
    from datacontract.ai.databricks_pii_detector import DatabricksPiiDetector

    fake_message = SimpleNamespace(content='{"email": true, "order_id": false}')
    fake_choice = SimpleNamespace(message=fake_message)
    fake_response = SimpleNamespace(choices=[fake_choice])
    fake_serving_endpoints = MagicMock()
    fake_serving_endpoints.query.return_value = fake_response
    fake_workspace_client = MagicMock(serving_endpoints=fake_serving_endpoints)
    monkeypatch.setattr(
        "datacontract.ai.databricks_pii_detector.WorkspaceClient",
        MagicMock(return_value=fake_workspace_client),
    )

    config = Config(databricks_pii_endpoint="pii-endpoint", databricks_profile="DEFAULT")
    detector = DatabricksPiiDetector(config)
    result = detector.detect(["email", "order_id"])

    assert result == {"email": True, "order_id": False}
    call_kwargs = fake_serving_endpoints.query.call_args.kwargs
    assert call_kwargs["name"] == "pii-endpoint"


def test_databricks_detector_requires_endpoint(monkeypatch):
    from datacontract.ai.databricks_pii_detector import DatabricksPiiDetector

    monkeypatch.delenv("DATACONTRACT_DATABRICKS_PII_ENDPOINT", raising=False)
    config = Config(databricks_profile="DEFAULT")
    detector = DatabricksPiiDetector(config)

    with pytest.raises(DataContractException, match="DATACONTRACT_DATABRICKS_PII_ENDPOINT"):
        detector.detect(["email"])


def test_databricks_detector_raises_on_malformed_response(monkeypatch):
    from datacontract.ai.databricks_pii_detector import DatabricksPiiDetector

    fake_message = SimpleNamespace(content="not json")
    fake_choice = SimpleNamespace(message=fake_message)
    fake_response = SimpleNamespace(choices=[fake_choice])
    fake_serving_endpoints = MagicMock()
    fake_serving_endpoints.query.return_value = fake_response
    fake_workspace_client = MagicMock(serving_endpoints=fake_serving_endpoints)
    monkeypatch.setattr(
        "datacontract.ai.databricks_pii_detector.WorkspaceClient",
        MagicMock(return_value=fake_workspace_client),
    )

    config = Config(databricks_pii_endpoint="pii-endpoint", databricks_profile="DEFAULT")
    detector = DatabricksPiiDetector(config)

    with pytest.raises(DataContractException, match="Could not classify columns"):
        detector.detect(["email"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ai_pii_detector.py -v -k databricks`
Expected: FAIL with `ModuleNotFoundError: No module named 'datacontract.ai.databricks_pii_detector'`

- [ ] **Step 3: Write minimal implementation**

Create `datacontract/ai/databricks_pii_detector.py`:

```python
import json

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

from datacontract.ai.pii_detector import PiiDetector
from datacontract.model.exceptions import DataContractException

_PROMPT_TEMPLATE = (
    "For each of the following database column names, decide whether it is likely to contain "
    "personally identifiable information (PII) such as names, emails, phone numbers, addresses, "
    "government IDs, or other data that identifies an individual person. "
    "Respond with ONLY a JSON object mapping each column name to true or false, no other text.\n\n"
    "Column names: {column_names}"
)


class DatabricksPiiDetector(PiiDetector):
    """Classifies column names as PII by calling a self-hosted Claude model behind a Databricks
    Model Serving endpoint, using the same workspace credentials as `import databricks`."""

    def detect(self, column_names: list[str]) -> dict[str, bool]:
        endpoint = self.config.get_databricks_pii_endpoint(required=True)
        profile = self.config.get_databricks_profile()
        if profile:
            workspace_client = WorkspaceClient(profile=profile)
        else:
            workspace_client = WorkspaceClient(
                host=self.config.get_databricks_server_hostname(required=True),
                token=self.config.get_databricks_token(required=True),
            )

        prompt = _PROMPT_TEMPLATE.format(column_names=json.dumps(column_names))
        try:
            response = workspace_client.serving_endpoints.query(
                name=endpoint,
                messages=[ChatMessage(role=ChatMessageRole.USER, content=prompt)],
            )
            result = json.loads(response.choices[0].message.content)
        except DataContractException:
            raise
        except Exception as e:
            raise DataContractException(
                type="databricks-connection",
                name="databricks pii detection failed",
                reason=f"Could not classify columns via the Databricks serving endpoint '{endpoint}': {e}",
                engine="datacontract-cli",
                original_exception=e,
            )
        return {name: bool(result.get(name, False)) for name in column_names}
```

In `datacontract/ai/pii_detector_factory.py`, add one more registration line after the `anthropic` registration:

```python
pii_detector_factory.register_lazy_detector(
    PiiDetectionMethod.databricks, "datacontract.ai.databricks_pii_detector", "DatabricksPiiDetector"
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ai_pii_detector.py -v`
Expected: PASS (every test added so far in `tests/test_ai_pii_detector.py`)

- [ ] **Step 5: Commit**

```bash
git add datacontract/ai/databricks_pii_detector.py datacontract/ai/pii_detector_factory.py tests/test_ai_pii_detector.py
git commit -m "feat: add DatabricksPiiDetector calling a Databricks Model Serving endpoint"
```

---

### Task 7: Wire `--detect-pii` into `datacontract import postgres`

**Files:**
- Modify: `datacontract/imports/postgres_importer.py`
- Modify: `datacontract/command_import.py`
- Modify: `tests/fixtures/postgres/data/import.sql`
- Modify: `tests/test_import_postgres.py`

**Interfaces:**
- Consumes: `mark_pii_columns` (Task 2), `pii_detector_factory` (Tasks 3/5/6).
- Produces: `import_postgres_from_connector(..., detect_pii: bool = False, pii_detector: str = "rule")`; `PostgresImporter.import_source` reads `import_args.get("detect_pii", False)` / `import_args.get("pii_detector", "rule")`; CLI `datacontract import postgres --detect-pii --pii-detector {rule,anthropic,databricks}`.

- [ ] **Step 1: Write the failing test**

Add a `customer_email` column to `tests/fixtures/postgres/data/import.sql`. Replace:

```sql
CREATE TABLE public.orders (
    order_id VARCHAR(36) PRIMARY KEY,
    order_total NUMERIC(10, 2),
    line_count INT NOT NULL,
    ordered_at TIMESTAMPTZ,
    payload JSONB
);

COMMENT ON TABLE public.orders IS 'All orders';
COMMENT ON COLUMN public.orders.order_id IS 'The order id';

INSERT INTO public.orders (order_id, order_total, line_count, ordered_at, payload) VALUES
    ('CX-263-DU', 50.00, 2, '2023-06-16 13:12:56', '{"channel": "web"}'),
    ('IK-894-MN', 47.50, 1, '2023-10-08 22:40:57', '{"channel": "app"}');
```

with:

```sql
CREATE TABLE public.orders (
    order_id VARCHAR(36) PRIMARY KEY,
    order_total NUMERIC(10, 2),
    line_count INT NOT NULL,
    ordered_at TIMESTAMPTZ,
    payload JSONB,
    customer_email VARCHAR(255)
);

COMMENT ON TABLE public.orders IS 'All orders';
COMMENT ON COLUMN public.orders.order_id IS 'The order id';

INSERT INTO public.orders (order_id, order_total, line_count, ordered_at, payload, customer_email) VALUES
    ('CX-263-DU', 50.00, 2, '2023-06-16 13:12:56', '{"channel": "web"}', 'cx263@example.com'),
    ('IK-894-MN', 47.50, 1, '2023-10-08 22:40:57', '{"channel": "app"}', 'ik894@example.com');
```

(Leave the `open_orders` view and `order_items` table below unchanged.)

In `tests/test_import_postgres.py`, add `customer_email` to the expected YAML in `test_import_postgres` — insert this block right after the `payload` property and before the closing `"""`:

```yaml
      - name: customer_email
        logicalType: string
        logicalTypeOptions:
          maxLength: 255
        physicalType: character varying(255)
```

Then add a new test function (near the other `_import(...)`-based tests):

```python
def test_import_postgres_detects_pii_with_rule_based_detector():
    result = _import(schema="public", postgres_table=["orders"], detect_pii=True)

    orders = result.schema_[0]
    customer_email = next(p for p in orders.properties if p.name == "customer_email")
    order_id = next(p for p in orders.properties if p.name == "order_id")

    assert customer_email.classification == "PII"
    assert customer_email.criticalDataElement is True
    assert order_id.classification is None


def test_cli_detect_pii_option_is_passed_through():
    with patch("datacontract.imports.postgres_importer.import_postgres_from_connector") as mock_import:
        mock_import.return_value = OpenDataContractStandard(id="test", kind="DataContract", apiVersion="v3.1.0")
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "import",
                "postgres",
                "--source",
                "localhost",
                "--database",
                "postgres",
                "--detect-pii",
                "--pii-detector",
                "anthropic",
            ],
        )

    assert result.exit_code == 0
    assert mock_import.call_args.kwargs["detect_pii"] is True
    assert mock_import.call_args.kwargs["pii_detector"] == "anthropic"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_import_postgres.py -v` (requires Docker running for the `testcontainers` Postgres container)
Expected: FAIL — `test_import_postgres` fails on the YAML diff (missing `customer_email`), `test_import_postgres_detects_pii_with_rule_based_detector` fails with `TypeError: import_postgres_from_connector() got an unexpected keyword argument 'detect_pii'`, `test_cli_detect_pii_option_is_passed_through` fails with a Typer "no such option" error.

- [ ] **Step 3: Write minimal implementation**

In `datacontract/imports/postgres_importer.py`, add the import:

```python
from datacontract.ai.annotate import mark_pii_columns
from datacontract.ai.pii_detector_factory import pii_detector_factory
```

Change `PostgresImporter.import_source`'s call to `import_postgres_from_connector` from:

```python
        return import_postgres_from_connector(
            host=source,
            port=import_args.get("port"),
            database=import_args.get("database"),
            schema=import_args.get("schema"),
            tables=import_args.get("postgres_table"),
            config=config,
        )
```

to:

```python
        return import_postgres_from_connector(
            host=source,
            port=import_args.get("port"),
            database=import_args.get("database"),
            schema=import_args.get("schema"),
            tables=import_args.get("postgres_table"),
            detect_pii=import_args.get("detect_pii", False),
            pii_detector=import_args.get("pii_detector", "rule"),
            config=config,
        )
```

Change `import_postgres_from_connector`'s signature from:

```python
def import_postgres_from_connector(
    host: str,
    database: Optional[str],
    schema: Optional[str] = None,
    port: Optional[int] = None,
    tables: Optional[List[str]] = None,
    config: Optional[Config] = None,
) -> OpenDataContractStandard:
```

to:

```python
def import_postgres_from_connector(
    host: str,
    database: Optional[str],
    schema: Optional[str] = None,
    port: Optional[int] = None,
    tables: Optional[List[str]] = None,
    detect_pii: bool = False,
    pii_detector: str = "rule",
    config: Optional[Config] = None,
) -> OpenDataContractStandard:
```

And change the end of `import_postgres_from_connector` from:

```python
    report_unmapped_types(odcs)
    return odcs
```

to:

```python
    if detect_pii:
        mark_pii_columns(odcs, pii_detector_factory.create(pii_detector, config))
    report_unmapped_types(odcs)
    return odcs
```

In `datacontract/command_import.py`, add two shared option aliases near the top, next to `owner_option`/`id_option`:

```python
detect_pii_option = Annotated[
    bool,
    typer.Option(help="Detect likely-PII columns and mark them classification=PII, criticalDataElement=true."),
]
pii_detector_option = Annotated[
    str,
    typer.Option(
        help="Detector to use with --detect-pii: rule (default, no credentials needed), anthropic, or databricks."
    ),
]
```

Then update `import_postgres`'s signature and body from:

```python
def import_postgres(
    source: Annotated[Optional[str], typer.Option(help="The host of the Postgres server.")] = None,
    port: Annotated[Optional[int], typer.Option(help="The Postgres port (default 5432).")] = None,
    database: database_option = None,
    schema: Annotated[
        Optional[str], typer.Option("--schema", help="The Postgres schema name (default public).")
    ] = None,
    table: Annotated[
        Optional[List[str]],
        typer.Option(help="Name of a table to import (repeat for multiple tables, omit for all tables in the schema)."),
    ] = None,
    output: output_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a Postgres schema."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(),
        format="postgres",
        source=source,
        port=port,
        database=database,
        schema=schema,
        postgres_table=table,
        owner=owner,
        id=id,
    )
    _write_result(result, output)
```

to:

```python
def import_postgres(
    source: Annotated[Optional[str], typer.Option(help="The host of the Postgres server.")] = None,
    port: Annotated[Optional[int], typer.Option(help="The Postgres port (default 5432).")] = None,
    database: database_option = None,
    schema: Annotated[
        Optional[str], typer.Option("--schema", help="The Postgres schema name (default public).")
    ] = None,
    table: Annotated[
        Optional[List[str]],
        typer.Option(help="Name of a table to import (repeat for multiple tables, omit for all tables in the schema)."),
    ] = None,
    detect_pii: detect_pii_option = False,
    pii_detector: pii_detector_option = "rule",
    output: output_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from a Postgres schema."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(),
        format="postgres",
        source=source,
        port=port,
        database=database,
        schema=schema,
        postgres_table=table,
        detect_pii=detect_pii,
        pii_detector=pii_detector,
        owner=owner,
        id=id,
    )
    _write_result(result, output)
```

In `tests/test_import_postgres.py`, add the necessary imports at the top if not already present (`from unittest.mock import patch`, `from open_data_contract_standard.model import OpenDataContractStandard`, `from typer.testing import CliRunner`, `from datacontract.cli import app` — check the existing `test_cli_schema_option_is_not_rewritten_to_json_schema` test at the bottom of the file; it already imports all of these, so no new imports should be needed).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_import_postgres.py -v` (Docker running)
Expected: PASS (all tests, including the 2 new ones)

- [ ] **Step 5: Commit**

```bash
git add datacontract/imports/postgres_importer.py datacontract/command_import.py tests/fixtures/postgres/data/import.sql tests/test_import_postgres.py
git commit -m "feat: add --detect-pii/--pii-detector to datacontract import postgres"
```

---

### Task 8: Wire `--detect-pii` into `datacontract import databricks`

**Files:**
- Modify: `datacontract/imports/unity_importer.py`
- Modify: `datacontract/command_import.py`
- Modify: `tests/fixtures/databricks-unity/import/unity_table_schema.json`
- Modify: `tests/fixtures/databricks-unity/import/datacontract.yaml`
- Modify: `tests/test_import_unity_file.py`

**Interfaces:**
- Consumes: `mark_pii_columns` (Task 2), `pii_detector_factory` (Tasks 3/5/6), `detect_pii_option`/`pii_detector_option` (Task 7, `datacontract/command_import.py`).
- Produces: `import_unity_from_json(source, config=None, detect_pii=False, pii_detector="rule")`, `import_unity_from_api(unity_table_full_name_list=None, config=None, detect_pii=False, pii_detector="rule")`; `UnityImporter.import_source` reads `import_args.get("detect_pii", False)` / `import_args.get("pii_detector", "rule")`; CLI `datacontract import databricks --detect-pii --pii-detector {rule,anthropic,databricks}` (and the hidden `unity` alias).

- [ ] **Step 1: Write the failing test**

Add an `email` column to `tests/fixtures/databricks-unity/import/unity_table_schema.json`. In the `"columns"` array, after the `is_active` column entry (`"position": 6`), add:

```json
    {
      "name": "email",
      "type_text": "string",
      "type_name": "STRING",
      "position": 7,
      "type_precision": 0,
      "type_scale": 0,
      "type_json": "{\"name\":\"email\",\"type\":\"string\",\"nullable\":true,\"metadata\":{}}",
      "nullable": true
    }
```

(Make sure the preceding `is_active` entry's closing `}` is followed by a comma before this new entry, and this new entry's closing `}` is followed by the `]` that closes `"columns"`.)

In `tests/fixtures/databricks-unity/import/datacontract.yaml`, add a matching property after `is_active` and before `storage_location`'s effects (i.e. after the last property in the `properties:` list):

```yaml
  - name: email
    physicalType: string
    logicalType: string
```

In `tests/test_import_unity_file.py`, add a new test:

```python
def test_import_databricks_detects_pii_with_rule_based_detector():
    result = DataContract.import_from_source(
        "databricks", "fixtures/databricks-unity/import/unity_table_schema.json", detect_pii=True
    )

    schema_obj = result.schema_[0]
    email = next(p for p in schema_obj.properties if p.name == "email")
    name = next(p for p in schema_obj.properties if p.name == "name")

    assert email.classification == "PII"
    assert email.criticalDataElement is True
    assert name.classification is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_import_unity_file.py -v`
Expected: FAIL — every test comparing against the full `datacontract.yaml` fixture fails (missing `email` property in the actual output), and `test_import_databricks_detects_pii_with_rule_based_detector` fails with `TypeError: import_from_source() got an unexpected keyword argument 'detect_pii'`.

- [ ] **Step 3: Write minimal implementation**

In `datacontract/imports/unity_importer.py`, add the import:

```python
from datacontract.ai.annotate import mark_pii_columns
from datacontract.ai.pii_detector_factory import pii_detector_factory
```

Change `UnityImporter.import_source` from:

```python
    def import_source(
        self,
        source: str,
        import_args: dict,
        config: "Config | None" = None,
    ) -> OpenDataContractStandard:
        """Import data contract specification from a source."""
        if source is not None:
            return import_unity_from_json(source)
        else:
            unity_table_full_name_list = import_args.get("unity_table_full_name")
            return import_unity_from_api(unity_table_full_name_list, config)
```

to:

```python
    def import_source(
        self,
        source: str,
        import_args: dict,
        config: "Config | None" = None,
    ) -> OpenDataContractStandard:
        """Import data contract specification from a source."""
        detect_pii = import_args.get("detect_pii", False)
        pii_detector = import_args.get("pii_detector", "rule")
        if source is not None:
            return import_unity_from_json(source, config=config, detect_pii=detect_pii, pii_detector=pii_detector)
        else:
            unity_table_full_name_list = import_args.get("unity_table_full_name")
            return import_unity_from_api(
                unity_table_full_name_list, config, detect_pii=detect_pii, pii_detector=pii_detector
            )
```

Change `import_unity_from_json` from:

```python
def import_unity_from_json(source: str) -> OpenDataContractStandard:
    """Import data contract specification from a JSON file."""
    try:
        with open(source, "r", encoding="utf-8") as file:
            json_contents = json.loads(file.read())
            unity_schema = TableInfo.from_dict(json_contents)
    except json.JSONDecodeError as e:
        raise DataContractException(
            type="schema",
            name="Parse unity schema",
            reason=f"Failed to parse unity schema from {source}",
            engine="datacontract-cli",
            original_exception=e,
        )

    odcs = convert_unity_schema(create_odcs(), unity_schema)
    report_unmapped_types(odcs)
    return odcs
```

to:

```python
def import_unity_from_json(
    source: str,
    config: "Config | None" = None,
    detect_pii: bool = False,
    pii_detector: str = "rule",
) -> OpenDataContractStandard:
    """Import data contract specification from a JSON file."""
    try:
        with open(source, "r", encoding="utf-8") as file:
            json_contents = json.loads(file.read())
            unity_schema = TableInfo.from_dict(json_contents)
    except json.JSONDecodeError as e:
        raise DataContractException(
            type="schema",
            name="Parse unity schema",
            reason=f"Failed to parse unity schema from {source}",
            engine="datacontract-cli",
            original_exception=e,
        )

    odcs = convert_unity_schema(create_odcs(), unity_schema)
    if detect_pii:
        mark_pii_columns(odcs, pii_detector_factory.create(pii_detector, config))
    report_unmapped_types(odcs)
    return odcs
```

Change `import_unity_from_api`'s signature and the corresponding two lines near its end from:

```python
def import_unity_from_api(
    unity_table_full_name_list: List[str] = None, config: "Config | None" = None
) -> OpenDataContractStandard:
```

to:

```python
def import_unity_from_api(
    unity_table_full_name_list: List[str] = None,
    config: "Config | None" = None,
    detect_pii: bool = False,
    pii_detector: str = "rule",
) -> OpenDataContractStandard:
```

and from:

```python
        odcs = convert_unity_schema(odcs, unity_schema)

    report_unmapped_types(odcs)
    return odcs
```

to:

```python
        odcs = convert_unity_schema(odcs, unity_schema)

    if detect_pii:
        mark_pii_columns(odcs, pii_detector_factory.create(pii_detector, config))
    report_unmapped_types(odcs)
    return odcs
```

In `datacontract/command_import.py`, update `import_databricks` from:

```python
def import_databricks(
    source: databricks_source_option = None,
    table: databricks_table_option = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from Databricks Unity Catalog."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(),
        format="databricks",
        source=source,
        schema=schema,
        unity_table_full_name=table,
        owner=owner,
        id=id,
    )
    _write_result(result, output)
```

to:

```python
def import_databricks(
    source: databricks_source_option = None,
    table: databricks_table_option = None,
    detect_pii: detect_pii_option = False,
    pii_detector: pii_detector_option = "rule",
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from Databricks Unity Catalog."""
    enable_debug_logging(debug)
    result = DataContract.import_from_source(
        config=cli_config(),
        format="databricks",
        source=source,
        schema=schema,
        unity_table_full_name=table,
        detect_pii=detect_pii,
        pii_detector=pii_detector,
        owner=owner,
        id=id,
    )
    _write_result(result, output)
```

And update the `import_unity` alias from:

```python
def import_unity(
    source: databricks_source_option = None,
    table: databricks_table_option = None,
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from Databricks Unity Catalog (alias of `import databricks`)."""
    import_databricks(source=source, table=table, output=output, schema=schema, owner=owner, id=id, debug=debug)
```

to:

```python
def import_unity(
    source: databricks_source_option = None,
    table: databricks_table_option = None,
    detect_pii: detect_pii_option = False,
    pii_detector: pii_detector_option = "rule",
    output: output_option = None,
    schema: schema_option = None,
    owner: owner_option = None,
    id: id_option = None,
    debug: debug_option = None,
):
    """Import a data contract from Databricks Unity Catalog (alias of `import databricks`)."""
    import_databricks(
        source=source,
        table=table,
        detect_pii=detect_pii,
        pii_detector=pii_detector,
        output=output,
        schema=schema,
        owner=owner,
        id=id,
        debug=debug,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_import_unity_file.py -v`
Expected: PASS (all tests, including the new one)

- [ ] **Step 5: Commit**

```bash
git add datacontract/imports/unity_importer.py datacontract/command_import.py tests/fixtures/databricks-unity/import/unity_table_schema.json tests/fixtures/databricks-unity/import/datacontract.yaml tests/test_import_unity_file.py
git commit -m "feat: add --detect-pii/--pii-detector to datacontract import databricks"
```

---

### Task 9: Docs, CHANGELOG, and full verification

**Files:**
- Modify: `docs/docs/imports/postgres.md`
- Modify: `docs/docs/imports/databricks.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- None (documentation-only; no code interfaces produced or consumed).

- [ ] **Step 1: Update the Postgres import doc**

In `docs/docs/imports/postgres.md`, after the existing paragraph describing what the importer reads, add one sentence. Change:

```
Creates a data contract from a Postgres schema by reading table metadata from `information_schema` — including column types with length and precision, nullability, primary keys, foreign keys, and the comments stored in `pg_description`. Works with Postgres and Postgres-compatible databases (e.g. RisingWave).
```

to:

```
Creates a data contract from a Postgres schema by reading table metadata from `information_schema` — including column types with length and precision, nullability, primary keys, foreign keys, and the comments stored in `pg_description`. Works with Postgres and Postgres-compatible databases (e.g. RisingWave).

Add `--detect-pii` to automatically mark likely-PII columns with `classification: PII` and `criticalDataElement: true`, based on column name. `--pii-detector` selects how: `rule` (default, no credentials needed), `anthropic` (calls the Anthropic API directly), or `databricks` (calls a self-hosted Claude model behind a Databricks Model Serving endpoint).
```

- [ ] **Step 2: Update the Databricks import doc**

In `docs/docs/imports/databricks.md`, after the existing description paragraph, add the same sentence:

```
Add `--detect-pii` to automatically mark likely-PII columns with `classification: PII` and `criticalDataElement: true`, based on column name. `--pii-detector` selects how: `rule` (default, no credentials needed), `anthropic` (calls the Anthropic API directly), or `databricks` (calls a self-hosted Claude model behind a Databricks Model Serving endpoint).
```

- [ ] **Step 3: Add a CHANGELOG entry**

In `CHANGELOG.md`, under `## [Unreleased]` → `### Added`, add one line:

```
- `--detect-pii` on `datacontract import postgres`/`databricks`: marks likely-PII columns with `classification: PII` and `criticalDataElement: true`, using a rule-based, direct-Anthropic, or self-hosted-Databricks-Claude detector (`--pii-detector rule|anthropic|databricks`)
```

- [ ] **Step 4: Run the full relevant test suite**

Run: `pytest tests/test_ai_pii_detector.py tests/test_config.py tests/test_import_unmapped_types.py tests/test_import_postgres.py tests/test_import_unity_file.py tests/test_docs_ordering.py tests/test_docs_commands.py -v`
Expected: PASS (every test in every file listed; Postgres tests need Docker running)

- [ ] **Step 5: Lint and format**

Run: `ruff check .` then `ruff format --diff .`
Expected: `ruff check` reports no errors; `ruff format --diff` reports no diffs (or apply `ruff format .` if it does)

- [ ] **Step 6: Commit**

```bash
git add docs/docs/imports/postgres.md docs/docs/imports/databricks.md CHANGELOG.md
git commit -m "docs: document --detect-pii/--pii-detector for postgres and databricks imports"
```
