"""Custom quality checks: SQL checks defined once, one YAML file per check, and used by name from a rule."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import sqlglot
import yaml
from open_data_contract_standard.model import DataQuality
from pydantic import ValidationError
from sqlglot import exp

from datacontract.config.variables import _ENUM_VALUES
from datacontract.engines.checks.sql_guard import _DIALECT_BY_SERVER_TYPE
from datacontract.lint.resolve import _SafeLoaderNoTimestamp

ENGINE = "datacontract-cli"

TABLE_PLACEHOLDERS = ("model", "table", "object", "schema", "dataset", "project", "catalog", "database")
COLUMN_PLACEHOLDERS = ("field", "column", "property")

COMPARATORS = (
    "mustBe",
    "mustNotBe",
    "mustBeGreaterThan",
    "mustBeGreaterOrEqualTo",
    "mustBeLessThan",
    "mustBeLessOrEqualTo",
    "mustBeBetween",
    "mustNotBeBetween",
)
_KEYS = ("description", "owner", "dimension", "arguments", "queries", *COMPARATORS)
_DIMENSIONS = _ENUM_VALUES[("DataQuality", "dimension")]
_DIALECTS = ("ansi", *sorted(set(_DIALECT_BY_SERVER_TYPE.values())))
_ARGUMENT_NAME = re.compile(r"[A-Za-z_]\w*")
_REFERENCE = re.compile(r"\$\{([^}]*)\}")
_CALL_DELIMITERS = (",", "(", ")", "=", "'", '"')


def placeholder_pattern(names: tuple[str, ...] | list[str], with_arguments: bool) -> re.Pattern:
    """`{name}` / `${name}` placeholders and `${arguments.x}` references, with the quotes around them."""
    pattern = rf"[\"'`]?\$?\{{({'|'.join(names)})\}}[\"'`]?"
    if with_arguments:
        pattern += r"|[\"'`]?\$\{arguments\.(\w+)\}[\"'`]?"
    return re.compile(pattern)


class CustomQualityCheckError(Exception):
    """A custom quality check cannot be found or read."""


@dataclass
class Argument:
    identifier: bool
    required: bool
    default: Any = None


@dataclass
class CustomQualityCheck:
    name: str
    description: Optional[str]
    dimension: Optional[str]
    arguments: dict[str, Argument]
    queries: dict[str, str]
    # The default expected result: at most one comparator key with its value.
    expected: dict[str, Any] = field(default_factory=dict)


def load(directory: str, name: str) -> CustomQualityCheck:
    folder = Path(directory)
    if not folder.is_dir():
        raise CustomQualityCheckError(f"The custom quality checks folder {directory} does not exist.")
    # The name comes from the contract, so it is looked up among the files, never joined into a path.
    files: dict[str, list[Path]] = {}
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.suffix in (".yaml", ".yml"):
            files.setdefault(path.stem, []).append(path)
    if name not in files:
        available = ", ".join(sorted(files)) or "none"
        raise CustomQualityCheckError(f"There is no custom quality check named '{name}'. Available: {available}.")
    if len(files[name]) > 1:
        raise CustomQualityCheckError(
            f"The custom quality check '{name}' is defined twice: {', '.join(path.name for path in files[name])}."
        )
    try:
        document = yaml.load(files[name][0].read_text(encoding="utf-8"), Loader=_SafeLoaderNoTimestamp)
    except yaml.YAMLError as e:
        raise CustomQualityCheckError(f"The custom quality check '{name}' is not valid YAML: {e}")
    return _parse(name, document)


def _parse(name: str, document) -> CustomQualityCheck:
    def invalid(detail: str) -> CustomQualityCheckError:
        return CustomQualityCheckError(f"The custom quality check '{name}' is invalid: {detail}")

    if not isinstance(document, dict):
        raise invalid("it must be a YAML mapping.")
    unknown = [key for key in document if key not in _KEYS]
    if unknown:
        raise invalid(f"unknown key {', '.join(map(str, unknown))}. Allowed are {', '.join(_KEYS)}.")

    description = document.get("description")
    if description is not None and not isinstance(description, str):
        raise invalid("description must be a string.")
    dimension = document.get("dimension")
    if dimension is not None and dimension not in _DIMENSIONS:
        raise invalid(f"dimension must be one of {', '.join(sorted(_DIMENSIONS))}.")

    arguments = {}
    for argument, spec in (document.get("arguments") or {}).items():
        if not isinstance(argument, str) or not _ARGUMENT_NAME.fullmatch(argument):
            raise invalid(f"argument name {argument!r} must be a word (letters, digits, underscores).")
        spec = spec if spec is not None else {}
        if not isinstance(spec, dict) or any(key not in ("type", "default") for key in spec):
            raise invalid(f"argument {argument} may only declare a type and a default.")
        if spec.get("type", "value") not in ("value", "identifier"):
            raise invalid(f"argument {argument} has the type {spec['type']!r}; it must be value or identifier.")
        arguments[argument] = Argument(
            identifier=spec.get("type") == "identifier", required="default" not in spec, default=spec.get("default")
        )

    queries = document.get("queries")
    if not isinstance(queries, dict) or not queries:
        raise invalid("it needs queries with at least one entry, e.g. queries.ansi.")
    for dialect, query in queries.items():
        if dialect not in _DIALECTS:
            raise invalid(f"queries.{dialect} is not a known dialect. Use one of {', '.join(_DIALECTS)}.")
        if not isinstance(query, str) or not query.strip():
            raise invalid(f"queries.{dialect} must be a non-empty SQL query.")

    for text in [description or "", *queries.values()]:
        for reference in _REFERENCE.findall(text):
            if reference in TABLE_PLACEHOLDERS + COLUMN_PLACEHOLDERS:
                continue
            if reference.startswith("arguments.") and reference.removeprefix("arguments.") in arguments:
                continue
            raise invalid(
                f"${{{reference}}} is neither a placeholder nor a declared argument. "
                f"Contract variables are not resolved in custom quality checks."
            )

    if "ansi" in queries:
        # Parsed with names and values standing in for the placeholders and arguments.
        pattern = placeholder_pattern(TABLE_PLACEHOLDERS + COLUMN_PLACEHOLDERS, with_arguments=True)
        portable = pattern.sub(
            lambda m: "x" if m.group(1) is not None or arguments[m.group(2)].identifier else "0", queries["ansi"]
        )
        try:
            sqlglot.parse(portable)
        except sqlglot.errors.SqlglotError as e:
            raise invalid(f"queries.ansi is not portable SQL: {e}")

    comparators = [key for key in COMPARATORS if key in document]
    if len(comparators) > 1:
        raise invalid(f"only one expected result is allowed, found {', '.join(comparators)}.")
    expected = {key: document[key] for key in comparators}
    try:
        DataQuality(**expected)
    except ValidationError as e:
        raise invalid(f"{comparators[0]} is not a valid expected result: {e.errors()[0]['msg']}.")

    return CustomQualityCheck(
        name=name,
        description=description,
        dimension=dimension,
        arguments=arguments,
        queries=queries,
        expected=expected,
    )


class CustomQualityCheckUnusable(Exception):
    """A rule's use of a custom quality check that cannot be executed, with the result to report."""

    def __init__(self, result: str, reason: str, name: str, dimension: Optional[str]):
        super().__init__(reason)
        self.result = result
        self.reason = reason
        self.name = name
        self.dimension = dimension


@dataclass
class Instance:
    """A custom quality check as one rule uses it, ready for an engine to render."""

    query: str
    # Argument name -> (is identifier, value), in the check's declaration order, defaults applied.
    arguments: dict[str, tuple[bool, Any]]
    # The rule with the check's defaults filled in: expected result and dimension.
    quality: DataQuality
    name: str
    diagnostics: dict


def instantiate(
    quality: DataQuality,
    model: str,
    field_name: Optional[str],
    dialect: Optional[str],
    directory: Optional[str],
) -> Instance:
    """The rule's custom quality check for a server whose rules are written in ``dialect``."""
    implementation = quality.implementation if isinstance(quality.implementation, dict) else {}
    check_name = implementation.get("check")
    fallback_name = quality.description or f"Custom quality check {check_name}"

    def unusable(result: str, reason: str, check: Optional[CustomQualityCheck] = None, name: Optional[str] = None):
        dimension = quality.dimension or (check.dimension if check else None)
        return CustomQualityCheckUnusable(result, reason, name or fallback_name, dimension)

    if not isinstance(check_name, str) or not check_name:
        raise unusable("warning", "The rule needs implementation.check naming a custom quality check.")
    unknown = [key for key in implementation if key not in ("check", "arguments")]
    if unknown:
        raise unusable(
            "warning", f"implementation has the unknown key {', '.join(unknown)}. Allowed are check and arguments."
        )
    given = implementation.get("arguments") or {}
    if not isinstance(given, dict):
        raise unusable("warning", "implementation.arguments must be a mapping of argument names to values.")

    if directory is None:
        raise unusable(
            "error",
            f"The rule uses the custom quality check '{check_name}', but no custom quality checks folder is "
            f"configured. Pass --custom-quality-checks or set DATACONTRACT_CUSTOM_QUALITY_CHECKS.",
        )
    try:
        check = load(directory, check_name)
    except CustomQualityCheckError as e:
        raise unusable("error", str(e))

    undeclared = [argument for argument in given if argument not in check.arguments]
    if undeclared:
        raise unusable(
            "warning",
            f"The custom quality check '{check.name}' has no argument {', '.join(map(str, undeclared))}. "
            f"Its arguments are {', '.join(check.arguments) or 'none'}.",
            check,
        )
    missing = [argument for argument, spec in check.arguments.items() if spec.required and argument not in given]
    if missing:
        raise unusable(
            "warning", f"The custom quality check '{check.name}' needs the argument {', '.join(missing)}.", check
        )
    arguments = {
        argument: (spec.identifier, given[argument] if argument in given else spec.default)
        for argument, spec in check.arguments.items()
    }
    name = quality.description or _description(check, arguments, model, field_name) or _call_form(check, arguments)

    for argument, (identifier, value) in arguments.items():
        if identifier and (not isinstance(value, str) or not value):
            raise unusable(
                "warning", f"The argument {argument} names a column or table, so it must be a string.", check, name
            )
        scalars = value if isinstance(value, list) else [value]
        if not identifier and not all(item is None or isinstance(item, (str, int, float, bool)) for item in scalars):
            raise unusable(
                "warning", f"The argument {argument} must be a single value or a list of values.", check, name
            )
    column = placeholder_pattern(COLUMN_PLACEHOLDERS, with_arguments=False)
    if field_name is None and any(column.search(query) for query in check.queries.values()):
        raise unusable(
            "warning",
            f"The custom quality check '{check.name}' refers to the column, so declare it on a property.",
            check,
            name,
        )

    rule_has_expected = any(getattr(quality, key) is not None for key in COMPARATORS)
    if not rule_has_expected and not check.expected:
        raise unusable(
            "warning",
            f"Neither the rule nor the custom quality check '{check.name}' sets an expected result, such as mustBe.",
            check,
            name,
        )
    query_dialect = dialect if dialect in check.queries else "ansi"
    if query_dialect not in check.queries:
        raise unusable(
            "warning",
            f"The custom quality check '{check.name}' has no query for {dialect or 'this server'} and no ansi query.",
            check,
            name,
        )

    updates = {} if rule_has_expected else dict(check.expected)
    if quality.dimension is None:
        updates["dimension"] = check.dimension
    return Instance(
        query=check.queries[query_dialect],
        arguments=arguments,
        quality=quality.model_copy(update=updates),
        name=name,
        diagnostics={
            "custom_quality_check": check.name,
            "query": query_dialect,
            "expected_result_from": "rule" if rule_has_expected else "check",
        },
    )


def sql_literal(value, dialect=None) -> str:
    """A value argument as a SQL literal; a list as comma-separated literals."""
    if isinstance(value, list):
        return ", ".join(sql_literal(item, dialect) for item in value)
    return exp.convert(value).sql(dialect=dialect)


def _description(
    check: CustomQualityCheck, arguments: dict[str, tuple[bool, Any]], model: str, field_name: Optional[str]
) -> Optional[str]:
    if check.description is None:
        return None
    names = dict.fromkeys(TABLE_PLACEHOLDERS, model)
    if field_name is not None:
        names |= dict.fromkeys(COLUMN_PLACEHOLDERS, field_name)

    def fill(match: re.Match) -> str:
        if match.group(2) is not None:
            value = arguments[match.group(2)][1]
            return ", ".join(map(str, value)) if isinstance(value, list) else str(value)
        return names.get(match.group(1), match.group(0))

    return re.sub(
        rf"\$?\{{({'|'.join(TABLE_PLACEHOLDERS + COLUMN_PLACEHOLDERS)})\}}|\$\{{arguments\.(\w+)\}}",
        fill,
        check.description,
    )


def _call_form(check: CustomQualityCheck, arguments: dict[str, tuple[bool, Any]]) -> str:

    def value_text(value) -> str:
        if isinstance(value, list):
            return f"[{', '.join(value_text(item) for item in value)}]"
        if not isinstance(value, str):
            return yaml.safe_dump(value, default_flow_style=True).strip().removesuffix("...").strip()
        try:
            reads_back = yaml.safe_load(value) == value
        except yaml.YAMLError:
            reads_back = False
        if reads_back and value and value == value.strip() and not any(c in value for c in _CALL_DELIMITERS):
            return value
        return "'" + value.replace("'", "''") + "'"

    return f"{check.name}({', '.join(f'{name}={value_text(value)}' for name, (_, value) in arguments.items())})"
