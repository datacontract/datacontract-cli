# PR #1043 Review: physicalType bypass for precision and scale conversion

**PR:** `fix/physicalType_byPass` by dmaresma
**Issue:** #1042 — physicalType like `DECIMAL(7,2)` is ignored by `convert_to_duckdb`
**Files changed:** `datacontract/export/sql_type_converter.py`, `tests/test_export_dbml.py`

---

## Summary

The PR aims to fix a problem where `convert_to_duckdb` doesn't handle `physicalType` values
that embed precision/scale (e.g., `DECIMAL(7,2)`). The root cause is that `_get_type()` returns
the full `physicalType` string `"DECIMAL(7,2)"`, but the converter uses exact equality
(`type_lower == "decimal"`), which doesn't match `"decimal(7,2)"`.

The fix changes to substring matching (`"decimal" in type_lower`) and adds a fallback to return
the raw type when precision/scale aren't found in `logicalTypeOptions` / `customProperties`.

---

## Issues Found

### 1. Bug: Substring matching creates false positives (High severity)

The change at `sql_type_converter.py:371`:

```python
# Before (exact match)
if type_lower == "decimal" or type_lower == "number" or type_lower == "numeric":

# After (substring containment)
if "decimal" in type_lower or "number" in type_lower or "numeric" in type_lower:
```

The `in` operator checks for substrings, not word boundaries. This means unrelated types would
incorrectly match:
- `"number" in "phonenumber"` → `True`
- `"number" in "numberofitems"` → `True`
- `"numeric" in "alphanumeric"` → `True`
- `"numeric" in "nonnumeric"` → `True`

A safer approach already exists in the codebase. `odcs_helper.py:map_sql_type_to_logical` (line 263)
uses `type_lower.split("(")[0].strip()` to extract the base type. The same pattern should be used here:

```python
base_type = type_lower.split("(")[0].strip()
if base_type in ("decimal", "number", "numeric"):
```

### 2. Bug: Test expects `number` as a DuckDB type (High severity)

The test update at `test_export_dbml.py:106` changes the expected output from:

```
STRUCT(amount STRUCT(sum DECIMAL(None,None), currency VARCHAR), ...)
```
to:
```
STRUCT(amount STRUCT(sum number, currency VARCHAR), ...)
```

While `DECIMAL(None,None)` was invalid, `number` is also **not a valid DuckDB type**. DuckDB does
not recognize `number` — it would fail at query time. The fixture has `physicalType: number` and
`logicalType: number` for the `sum` field, so the fallback `return type` returns the raw string
`"number"`.

The correct behavior should be to return `DECIMAL` with sensible defaults (as other converters in
this same file already do).

### 3. Inconsistency with sibling converters (Medium severity)

Other converters in the same file already handle missing precision/scale by defaulting:

| Converter | Behavior when precision/scale missing |
|---|---|
| `convert_to_dataframe` (line 238) | Defaults to `DECIMAL(38,0)` |
| `convert_to_databricks` (line 294) | Defaults to `DECIMAL(38,0)` |
| `convert_type_to_impala` (line 543) | Defaults to `DECIMAL(38,0)` |
| **`convert_to_duckdb` (this PR)** | **Returns raw type string as-is** |

The duckdb converter should follow the same convention. Returning the raw `physicalType` breaks the
contract that these functions return valid SQL types for their target database.

### 4. Missing: physicalType precision/scale parsing (Medium severity)

The `spark_exporter.py` already has `_parse_decimal_precision_scale` (line 123) that correctly
extracts precision and scale from strings like `"DECIMAL(7,2)"` using regex. The `_get_precision`
and `_get_scale` functions in `sql_type_converter.py` should be enhanced to also parse from
`physicalType` when `logicalTypeOptions` and `customProperties` are empty. This would fix the issue
at the right abstraction level and benefit all converters, not just duckdb.

### 5. Undocumented change: `nvarchar` mapping added (Low severity)

The PR silently adds `"nvarchar": "VARCHAR"` to the duckdb type mapping (line 343). This is an
unrelated change that isn't mentioned in the PR description or commit messages. It should either be
documented or split into a separate PR/commit.

### 6. Unrelated formatting changes mixed in (Low severity)

Several cosmetic changes are bundled in:
- Blank line added in `FieldLike` class (line 8)
- `convert_to_databricks` if-statement reformatted to single line (line 274)
- Blank line added before `convert_type_to_oracle` (line 582)
- Newline fix at end of file (line 612)

These should ideally be in a separate commit or excluded.

---

## Suggested Fix

Instead of the approach in this PR, a more robust fix would be:

```python
# In convert_to_duckdb, around line 371:
base_type = type_lower.split("(")[0].strip()
if base_type in ("decimal", "number", "numeric"):
    precision = _get_precision(field)
    scale = _get_scale(field)
    if precision is not None and scale is not None:
        return f"DECIMAL({precision},{scale})"
    # If physicalType already contains precision/scale, use it directly
    if "(" in type_lower:
        return type
    # Fall back to defaults like other converters
    return f"DECIMAL({precision if precision is not None else 18},{scale if scale is not None else 0})"
```

Or better yet, enhance `_get_precision` / `_get_scale` to parse from `physicalType` (reusing the
regex from `spark_exporter.py`), which would fix this for all converters at once.

---

## Verdict

**Request changes.** The PR addresses a real problem but the implementation introduces a
substring-matching bug, produces invalid DuckDB types in the fallback path, and is inconsistent
with how all sibling converters handle the same scenario. The core idea (handle physicalType
pass-through) is correct, but the mechanism needs revision.
