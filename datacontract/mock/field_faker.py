"""Generates fake values for ODCS schema properties, backed by mimesis.

The mapping is best effort: it looks at the property name for common
semantic hints (email, phone, city, ...), then falls back to the
`logicalType`/`physicalType` (same normalization as
`export/pandas_type_converter.py`). `logicalTypeOptions` (`minimum`,
`maximum`, `minLength`, `maxLength`, `pattern`) and an `enum` custom
property constrain the generated value where practical. `locale` selects
the language/region used for names, addresses, etc.; see `LOCALE_CODES`
for the supported codes.
"""

import random
import re
from typing import Any, Optional

from mimesis import Field
from mimesis.locales import Locale
from open_data_contract_standard.model import SchemaProperty

# Checked in order against the lowercased property name; the first
# substring match wins. Keys are `provider.method` names resolved through
# mimesis' `Field`.
_NAME_HINTS: list[tuple[str, str]] = [
    ("email", "person.email"),
    ("phone", "person.phone_number"),
    ("first_name", "person.first_name"),
    ("firstname", "person.first_name"),
    ("last_name", "person.last_name"),
    ("lastname", "person.last_name"),
    ("surname", "person.last_name"),
    ("username", "person.username"),
    ("full_name", "person.full_name"),
    ("postal", "address.postal_code"),
    ("zip", "address.postal_code"),
    ("city", "address.city"),
    ("country", "address.country"),
    ("address", "address.address"),
    ("company", "finance.company"),
    ("url", "internet.url"),
    ("ip_address", "internet.ip_v4"),
    ("uuid", "cryptographic.uuid"),
    ("description", "text.sentence"),
    ("comment", "text.sentence"),
    # `name` is intentionally last: it would otherwise shadow `first_name`, `username`, etc.
    ("name", "person.full_name"),
]

# `^<literal-prefix>[0-9]+$`-shaped patterns (e.g. the `order_id` example in
# ODCS docs: `^B[0-9]+$`) are common enough for identifiers to synthesize a
# matching value instead of falling back to plain words.
_PREFIXED_DIGITS_PATTERN = re.compile(r"^\^(?P<prefix>[A-Za-z0-9_-]*)\[0-9\]\+\$$")

_STRING_TYPES = {"string", "varchar", "text", "char"}
_INTEGER_TYPES = {"integer", "int", "long", "short", "smallint", "bigint", "tinyint"}
_FLOAT_TYPES = {"number", "float", "decimal", "numeric", "double", "real"}
_BOOLEAN_TYPES = {"boolean", "bool"}
_DATE_TYPES = {"date"}
_DATETIME_TYPES = {"timestamp", "timestamp_tz", "timestamp_ntz", "datetime"}


# `--locale` codes accepted by the `mock` command, mapped to the mimesis locale
# they resolve to: FR (français), EN (English, default), ES (Español), DE
# (Deutsch), NL (Nederlands/Dutch), IT (Italiano), PT (Português), ZH (中文/Chinese).
LOCALE_CODES: dict[str, Locale] = {
    "FR": Locale.FR,
    "EN": Locale.EN,
    "ES": Locale.ES,
    "DE": Locale.DE,
    "NL": Locale.NL,
    "IT": Locale.IT,
    "PT": Locale.PT,
    "ZH": Locale.ZH,
}


class FieldFaker:
    """Generates one fake value at a time for a given schema property and row index."""

    def __init__(self, locale: str = "EN", seed: Optional[int] = None):
        resolved_locale = LOCALE_CODES.get(locale.strip().upper())
        if resolved_locale is None:
            available = ", ".join(sorted(LOCALE_CODES))
            raise RuntimeError(f"Unsupported mock locale '{locale}'. Available locales: {available}")
        self._field = Field(locale=resolved_locale, seed=seed)
        self._random = random.Random(seed)

    def value_for(self, prop: SchemaProperty, row_index: int) -> Any:
        enum_values = _get_enum_values(prop)
        if enum_values:
            return self._random.choice(enum_values)

        field_type = _normalized_type(prop)
        options = prop.logicalTypeOptions or {}

        if prop.primaryKey:
            return self._primary_key_value(prop, field_type, options, row_index)

        hint = _name_hint(prop.name)
        if hint is not None and field_type not in (_DATE_TYPES | _DATETIME_TYPES | _BOOLEAN_TYPES):
            return self._field(hint)

        return self._by_type(field_type, options)

    def fk_value(self, pool: list) -> Any:
        """Pick an existing value to preserve a `relationships` foreign key reference."""
        return self._random.choice(pool)

    def _primary_key_value(self, prop: SchemaProperty, field_type: str, options: dict, row_index: int) -> Any:
        if field_type in _INTEGER_TYPES:
            start = int(options.get("minimum", 1))
            return start + row_index
        pattern = options.get("pattern")
        prefixed = _PREFIXED_DIGITS_PATTERN.match(pattern) if isinstance(pattern, str) else None
        if prefixed is not None:
            return _pad_prefixed_digits(prefixed.group("prefix"), row_index, options)
        # No usable pattern: fall back to a unique, human-readable id.
        base = prop.name or "id"
        return f"{base}-{row_index + 1}"

    def _by_type(self, field_type: str, options: dict) -> Any:
        if field_type in _INTEGER_TYPES:
            start = int(options.get("minimum", -1000))
            end = int(options.get("maximum", 1000))
            return self._field("numeric.integer_number", start=start, end=end)
        if field_type in _FLOAT_TYPES:
            start = float(options.get("minimum", -1000.0))
            end = float(options.get("maximum", 1000.0))
            return self._field("numeric.float_number", start=start, end=end)
        if field_type in _BOOLEAN_TYPES:
            return self._field("development.boolean")
        if field_type in _DATE_TYPES:
            return self._field("datetime.date")
        if field_type in _DATETIME_TYPES:
            return self._field("datetime.datetime")
        if field_type in ("object", "array", "bytes"):
            # Nested/binary values are not synthesized; callers render these as null.
            return None
        # Default: free-form string, constrained to minLength/maxLength if given.
        value = str(self._field("text.word"))
        return _fit_length(value, options)


def _normalized_type(prop: SchemaProperty) -> str:
    field_type = prop.logicalType or prop.physicalType or "string"
    return field_type.lower()


def is_identity_column(prop: SchemaProperty) -> bool:
    """Whether `prop` looks like a database-generated identity/auto-increment column.

    Matches the same primary-key-plus-integer-type shape that `_primary_key_value`
    generates sequential values for; used by `mock_generator` to decide whether the
    rendered SQL `INSERT` statements need dialect-specific directives (e.g. T-SQL's
    `SET IDENTITY_INSERT`) to allow supplying explicit values for such a column.
    """
    return bool(prop.primaryKey) and _normalized_type(prop) in _INTEGER_TYPES


def _name_hint(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    lowered = name.lower()
    for keyword, provider_key in _NAME_HINTS:
        if keyword in lowered:
            return provider_key
    return None


def _get_enum_values(prop: SchemaProperty) -> Optional[list]:
    for custom_property in prop.customProperties or []:
        if custom_property.property == "enum" and isinstance(custom_property.value, list):
            return custom_property.value
    return None


def _fit_length(value: str, options: dict) -> str:
    min_length = options.get("minLength")
    max_length = options.get("maxLength")
    if max_length is not None:
        value = value[: int(max_length)]
    if min_length is not None and len(value) < int(min_length):
        value = (value * (int(min_length) // max(len(value), 1) + 1))[: int(min_length)]
    return value


def _pad_prefixed_digits(prefix: str, row_index: int, options: dict) -> str:
    digits = str(row_index + 1)
    min_length = options.get("minLength")
    if min_length is not None:
        digits = digits.zfill(max(int(min_length) - len(prefix), len(digits)))
    max_length = options.get("maxLength")
    value = f"{prefix}{digits}"
    if max_length is not None and len(value) > int(max_length):
        value = value[: int(max_length)]
    return value
