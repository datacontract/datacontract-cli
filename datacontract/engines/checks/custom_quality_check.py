"""Custom quality checks: SQL checks defined once, one YAML file per check, and used by their ID from a rule."""

from __future__ import annotations

import difflib
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Optional
from urllib.parse import quote, urlparse

import requests
import sqlglot
import yaml
from open_data_contract_standard.model import DataQuality
from pydantic import ValidationError
from sqlglot import exp
from sqlglot.dialects.dialect import Dialect
from sqlglot.tokens import TokenType

from datacontract.config import Config
from datacontract.config.variables import _ENUM_VALUES
from datacontract.engines.checks.sql_guard import _DIALECT_BY_SERVER_TYPE
from datacontract.integration.entropy_data import _get_api_key_or_none, _get_host
from datacontract.lint.resolve import _api_key_for, _SafeLoaderNoTimestamp

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
DEFAULT_QUERY = "default"

_KEYS = ("name", "description", "owner", "dimension", "arguments", "queries", *COMPARATORS)
_DIMENSIONS = _ENUM_VALUES[("DataQuality", "dimension")]
_DIALECTS = tuple(sorted(set(_DIALECT_BY_SERVER_TYPE.values())))
_DIALECT_NAME = re.compile(r"[a-z0-9_]+")
# the characters Entropy Data allows in every ID
_ID = re.compile(r"[^\s/\\%;#?]+")
_ARGUMENT_NAME = re.compile(r"[A-Za-z_]\w*")
_NUMBER = re.compile(r"-?[0-9]+(\.[0-9]+)?")
_REFERENCE = re.compile(r"\$\{([^}]*)\}|\{(arguments\.[^}]*)\}")
_CALL_DELIMITERS = (",", "(", ")", "=", "'", '"')
_MARKER = re.compile(r"__datacontract_reference_(\d+)__")
_LIST_OPENERS = (TokenType.L_PAREN, TokenType.L_BRACKET, TokenType.COMMA)
_LIST_CLOSERS = (TokenType.R_PAREN, TokenType.R_BRACKET, TokenType.COMMA)
# the prefix and quote a string token starts with: E'...', N'...', r'...', U&'...', "...", $$...$$, $tag$...$tag$
_STRING_OPENING = re.compile(r"(\w*&?)(\$\w*\$|'''|\"\"\"|['\"])")


def placeholder_pattern(names: tuple[str, ...] | list[str]) -> re.Pattern:
    """`{name}` / `${name}` placeholders, with the quotes around them."""
    return re.compile(rf"[\"'`]?\$?\{{({'|'.join(names)})\}}[\"'`]?")


def reference_pattern(names: tuple[str, ...] | list[str]) -> re.Pattern:
    """`{name}` / `${name}` placeholders and `{arguments.x}` / `${arguments.x}` references, with backticks around them.

    Groups: the backtick (or ""), the placeholder, the argument.
    """
    return re.compile(rf"(`?)(?:\$?\{{({'|'.join(names)})\}}|\$?\{{arguments\.(\w+)\}})\1")


class CustomQualityCheckError(Exception):
    """A custom quality check cannot be found or read."""


@dataclass
class Argument:
    type: str
    required: bool
    default: Any = None


@dataclass
class CustomQualityCheck:
    id: str
    description: Optional[str]
    dimension: Optional[str]
    arguments: dict[str, Argument]
    queries: dict[str, str]
    # The default expected result: at most one comparator key with its value.
    expected: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class CustomQualityChecks:
    """Where a test run finds its custom quality checks: the folder first, then Entropy Data."""

    def __init__(self, config: Config, untrusted_contract: bool = False):
        self.directory = config.get_custom_quality_checks()
        # An untrusted caller may set the host per request (API header); checks still come from the platform
        # as the environment sees it, or the request would choose where the server sends its GET.
        self.host = _get_host(None if untrusted_contract else config).rstrip("/")
        self.api_key = _api_key_for(self.host, config, untrusted_contract)
        # A key the request brought for its own host is not sent to the environment's host.
        self.ignored_request_host = (
            _get_host(config)
            if untrusted_contract and self.api_key is None and _get_api_key_or_none(config) is not None
            else None
        )
        # lowercased ID -> the check's YAML, or why Entropy Data could not provide it
        self._fetched: dict[str, str | CustomQualityCheckError] = {}

    def load(self, check_id: str) -> CustomQualityCheck:
        """The check with ``check_id``, regardless of case."""
        if self.directory is not None:
            folder = Path(self.directory)
            if not folder.is_dir():
                problem = "is a file, not a folder" if folder.exists() else "does not exist"
                raise CustomQualityCheckError(f"The custom quality checks folder {self.directory} {problem}.")
            # The ID comes from the contract, so it is looked up among the files, never joined into a path.
            files: dict[str, list[Path]] = {}
            for path in sorted(folder.iterdir()):
                if path.is_file() and path.suffix in (".yaml", ".yml"):
                    files.setdefault(path.stem.lower(), []).append(path)
            paths = files.get(check_id.lower(), [])
            if len(paths) > 1:
                raise CustomQualityCheckError(
                    f"The custom quality check '{check_id}' is defined twice: {', '.join(path.name for path in paths)}."
                )
            if paths:
                return _parse(check_id, paths[0].read_text(encoding="utf-8"))
            if self.api_key is None:
                ids = sorted(path.stem for group in files.values() for path in group)
                if len(ids) <= 7:
                    hint = f" Available: {', '.join(ids) or 'none'}."
                else:
                    similar = difflib.get_close_matches(check_id, ids, n=3)
                    hint = f" Did you mean {', '.join(similar)}?" if similar else ""
                raise CustomQualityCheckError(f"There is no custom quality check with the ID '{check_id}'.{hint}")

        key = check_id.lower()
        if key not in self._fetched:
            reason = None
            try:
                # Not following redirects keeps the API key from travelling to another host.
                response = requests.get(
                    f"{self.host}/api/custom-quality-checks/{quote(check_id, safe='')}/check.yaml",
                    headers={"x-api-key": self.api_key, "Accept": "application/yaml"},
                    timeout=10,
                    allow_redirects=False,
                )
            except requests.RequestException as e:
                reason = str(e)
            else:
                if response.status_code == 200:
                    self._fetched[key] = response.content.decode("utf-8")
                elif response.status_code == 404:
                    self._fetched[key] = CustomQualityCheckError(
                        f"Neither {self.directory} nor Entropy Data has the custom quality check '{check_id}'."
                        if self.directory is not None
                        else f"Entropy Data has no custom quality check '{check_id}'."
                    )
                elif response.is_redirect:
                    reason = (
                        f"HTTP {response.status_code} redirect to '{response.headers.get('Location')}' is not followed"
                    )
                elif response.status_code in (401, 403):
                    reason = f"the API key was rejected (HTTP {response.status_code})"
                else:
                    reason = f"HTTP {response.status_code} {response.reason}"
            if reason is not None:
                self._fetched[key] = CustomQualityCheckError(
                    f"Could not load the custom quality check '{check_id}' from "
                    f"{urlparse(self.host).netloc or self.host}: {reason}."
                )
        fetched = self._fetched[key]
        if isinstance(fetched, CustomQualityCheckError):
            raise fetched
        return _parse(check_id, fetched)


def _parse(check_id: str, text: str) -> CustomQualityCheck:
    def invalid(detail: str) -> CustomQualityCheckError:
        return CustomQualityCheckError(f"The custom quality check '{check_id}' is invalid: {detail}")

    try:
        document = yaml.load(text, Loader=_SafeLoaderNoTimestamp)
    except yaml.YAMLError as e:
        raise CustomQualityCheckError(f"The custom quality check '{check_id}' is not valid YAML: {e}")
    if not isinstance(document, dict):
        raise invalid("it must be a YAML mapping.")
    # Unknown keys only warn, so a file written for a newer version still runs.
    warnings = [f"Unknown key '{key}' is ignored." for key in document if key not in _KEYS]

    if document.get("name") is not None and not isinstance(document["name"], str):
        raise invalid("name must be a string.")
    description = document.get("description")
    if description is not None and not isinstance(description, str):
        raise invalid("description must be a string.")
    dimension = document.get("dimension")
    if dimension is not None and dimension not in _DIMENSIONS:
        raise invalid(f"dimension must be one of {', '.join(sorted(_DIMENSIONS))}.")

    declared = document.get("arguments")
    if declared is None:
        declared = {}
    if not isinstance(declared, dict):
        raise invalid("arguments must be a mapping of argument names to their type and default.")
    arguments = {}
    for argument, spec in declared.items():
        if not isinstance(argument, str) or not _ARGUMENT_NAME.fullmatch(argument):
            raise invalid(f"argument name {argument!r} must be a word (letters, digits, underscores).")
        spec = spec if spec is not None else {}
        if not isinstance(spec, dict):
            raise invalid(f"argument {argument} must be a mapping with a type and a default.")
        warnings += [
            f"Unknown key 'arguments.{argument}.{key}' is ignored." for key in spec if key not in ("type", "default")
        ]
        argument_type = spec.get("type", "any")
        if argument_type == "value":
            argument_type = "any"
        if argument_type not in ("any", "identifier", "number"):
            raise invalid(f"argument {argument} has the type {argument_type!r}; it must be any, identifier or number.")
        arguments[argument] = Argument(type=argument_type, required="default" not in spec, default=spec.get("default"))

    queries = document.get("queries")
    if not isinstance(queries, dict) or not queries:
        raise invalid(f"it needs queries with at least one entry, e.g. queries.{DEFAULT_QUERY}.")
    queries = {(DEFAULT_QUERY if dialect == "ansi" else str(dialect)): query for dialect, query in queries.items()}
    for dialect, query in queries.items():
        if not _DIALECT_NAME.fullmatch(dialect):
            raise invalid(
                f"queries.{dialect} is not a dialect name. "
                "Use lowercase letters, digits and underscores, such as queries.snowflake."
            )
        if not isinstance(query, str) or not query.strip():
            raise invalid(f"queries.{dialect} must be a non-empty SQL query.")
        if dialect != DEFAULT_QUERY and dialect not in _DIALECTS:
            warnings.append(
                f"The dialect '{dialect}' is not supported by datacontract-cli. Use one of: {', '.join(_DIALECTS)}."
            )

    for text in [description or "", *queries.values()]:
        for match in _REFERENCE.finditer(text):
            reference = match.group(1) if match.group(1) is not None else match.group(2)
            if reference in TABLE_PLACEHOLDERS + COLUMN_PLACEHOLDERS:
                continue
            if reference.startswith("arguments.") and reference.removeprefix("arguments.") in arguments:
                continue
            raise invalid(
                f"{match.group(0)} is neither a placeholder nor a declared argument. "
                f"Contract variables are not resolved in custom quality checks."
            )

    comparators = [key for key in COMPARATORS if key in document]
    if len(comparators) > 1:
        raise invalid(f"only one expected result is allowed, found {', '.join(comparators)}.")
    expected = {key: document[key] for key in comparators}
    try:
        DataQuality(**expected)
    except ValidationError as e:
        raise invalid(f"{comparators[0]} is not a valid expected result: {e.errors()[0]['msg']}.")

    return CustomQualityCheck(
        id=check_id,
        description=description,
        dimension=dimension,
        arguments=arguments,
        queries=queries,
        expected=expected,
        warnings=[f"Custom quality check '{check_id}': {warning}" for warning in warnings],
    )


class CustomQualityCheckUnusable(Exception):
    """A rule's use of a custom quality check that cannot be executed, reported as an error."""

    def __init__(self, reason: str, name: str, dimension: Optional[str], warnings: list[str]):
        super().__init__(reason)
        self.reason = reason
        self.name = name
        self.dimension = dimension
        self.warnings = warnings


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
    warnings: list[str]

    def render(self, dialect, names: Mapping[str, str], identifier: Callable[[str, bool], str]) -> str:
        """The query with each placeholder and argument substituted by where it stands in the query.

        ``names`` maps the placeholders to the names they stand for, and ``identifier(name, forced)``
        renders a name, ``forced`` when the author wrote backticks around it.
        """
        check = self.diagnostics["custom_quality_check"]
        where = f"queries.{self.diagnostics['query']}"

        def unusable(reason: str) -> CustomQualityCheckUnusable:
            return CustomQualityCheckUnusable(reason, self.name, self.quality.dimension, self.warnings)

        def invalid(detail: str) -> CustomQualityCheckUnusable:
            return unusable(f"The custom quality check '{check}' is invalid: {detail}")

        # (as written, is a value argument, the name or value it stands for, the backtick around it or "")
        references: list[tuple[str, bool, Any, str]] = []

        def mark(match: re.Match) -> str:
            written = match.group(0).strip("`")
            if match.group(2) is not None:
                references.append((written, False, names[match.group(2)], match.group(1)))
            else:
                is_identifier, value = self.arguments[match.group(3)]
                references.append((written, not is_identifier, value, match.group(1)))
            return f"__datacontract_reference_{len(references) - 1}__"

        # one pass, so a substituted name or value is not searched for placeholders again
        marked = reference_pattern(list(names)).sub(mark, self.query)
        try:
            tokens = Dialect.get_or_raise(dialect).tokenize(marked)
        except sqlglot.errors.SqlglotError as e:
            raise unusable(f"The query could not be read as SQL: {e}")

        def misplaced(index: int, token=None) -> CustomQualityCheckUnusable:
            """``token`` is the one the reference sits in, None for a comment."""
            written, is_value, _, backtick = references[index]
            if token is None:
                problem = "is in a comment. Remove it from the comment."
            elif is_value and backtick:
                problem = f"is in backticks, which SQL reads as a name. Use single quotes for a string: '{written}'."
            elif is_value and token.token_type == TokenType.IDENTIFIER:
                problem = (
                    f"is in double quotes, which SQL reads as a name. Use single quotes for a string: '{written}'."
                )
            elif is_value and token.token_type.name.endswith("STRING"):
                prefix, quote = _STRING_OPENING.match(marked[token.start : token.end + 1]).groups()
                problem = (
                    f"is inside a string written as {prefix}{quote}...{quote}. "
                    f"Only plain '...' strings can hold a value."
                )
            elif is_value:
                problem = "is joined to other text. Let it stand alone, or put it inside a '...' string."
            elif token.token_type.name.endswith("STRING"):
                problem = "is a column or table name, so it must stand alone, not inside a string."
                if "arguments." in written:
                    problem += " To use it as text, declare the argument without type: identifier."
            else:
                problem = (
                    "is a column or table name, so it must stand alone, not joined to other text. "
                    "To build a name, pass the whole name as an identifier argument."
                )
            return invalid(f"{written} in {where} {problem}")

        def substitute(at: int, span: str, indexes: list[int]) -> str:
            token = tokens[at]
            written, is_value, value, backtick = references[indexes[0]]
            alone = len(indexes) == 1 and _MARKER.fullmatch(span)
            if alone and is_value and backtick:
                raise misplaced(indexes[0], token)
            if alone:
                if is_value and isinstance(value, list):
                    before = tokens[at - 1].token_type if at > 0 else None
                    after = tokens[at + 1].token_type if at + 1 < len(tokens) else None
                    if before not in _LIST_OPENERS or after not in _LIST_CLOSERS:
                        raise unusable(
                            f"{written} is a list, but {where} uses it where one value goes. Pass a single value.",
                        )
                return sql_literal(value, dialect) if is_value else identifier(value, bool(backtick))
            quoted = len(indexes) == 1 and len(span) > 2 and span[0] == span[-1] and span[0] in "'\""
            if quoted and not is_value and _MARKER.fullmatch(span[1:-1]):
                return identifier(value, bool(backtick))
            if not (token.token_type == TokenType.STRING and span.startswith("'")):
                raise misplaced(indexes[0], token)
            for index in indexes:
                if not references[index][1]:
                    raise misplaced(index, token)
            texts = {}
            for index in indexes:
                written, _, value, backtick = references[index]
                if isinstance(value, list):
                    raise unusable(f"{written} is a list, but {where} uses it inside a string. Pass a single value.")
                if not isinstance(value, (str, int, float)):
                    raise unusable(f"{written} is null, but {where} uses it inside a string. Give it a value.")
                text = ("true" if value else "false") if isinstance(value, bool) else str(value)
                # the literal's quotes dropped, its escaping kept
                texts[index] = backtick + exp.convert(text).sql(dialect=dialect)[1:-1] + backtick
            string = _MARKER.sub(lambda match: texts[int(match.group(1))], span)
            # a backslash the author wrote right before a reference can turn the value's escaping into an end quote
            try:
                string_tokens = Dialect.get_or_raise(dialect).tokenize(string)
            except sqlglot.errors.SqlglotError:
                string_tokens = []
            if len(string_tokens) != 1 or string_tokens[0].token_type != TokenType.STRING:
                raise invalid(
                    f"the value of {references[indexes[0]][0]} in {where} would end its '...' string. "
                    f"Remove the backslash in front of it."
                )
            return string

        rendered, position, placed = [], 0, set()
        for at, token in enumerate(tokens):
            span = marked[token.start : token.end + 1]
            indexes = [int(index) for index in _MARKER.findall(span)]
            if indexes:
                rendered += [marked[position : token.start], substitute(at, span, indexes)]
                position = token.end + 1
                placed.update(indexes)
        # a reference in a comment is in no token
        unplaced = sorted(set(range(len(references))) - placed)
        if unplaced:
            raise misplaced(unplaced[0])
        return "".join(rendered) + marked[position:]


def instantiate(
    quality: DataQuality,
    model: str,
    field_name: Optional[str],
    dialect: Optional[str],
    custom_quality_checks: Optional[CustomQualityChecks],
) -> Instance:
    """The rule's custom quality check for a server whose rules are written in ``dialect``."""
    implementation = quality.implementation if isinstance(quality.implementation, dict) else {}
    check_id = implementation.get("check")
    fallback_name = quality.description or f"Custom quality check {check_id}"

    rule_warnings: list[str] = []

    def unusable(reason: str, check: Optional[CustomQualityCheck] = None, name: Optional[str] = None):
        dimension = quality.dimension or (check.dimension if check else None)
        warnings = rule_warnings + (check.warnings if check else [])
        return CustomQualityCheckUnusable(reason, name or fallback_name, dimension, warnings)

    if not isinstance(check_id, str) or not check_id:
        raise unusable("The rule needs implementation.check with the ID of a custom quality check.")
    if not _ID.fullmatch(check_id):
        raise unusable(
            f"The custom quality check ID '{check_id}' must not contain spaces, slashes, "
            "or any of the characters \\ % ; # ?"
        )
    if check_id in (".", ".."):
        raise unusable(f"The custom quality check ID '{check_id}' must not be . or ..")
    location = model if field_name is None else f"{model}.{field_name}"
    rule_warnings += [
        f"Custom quality check '{check_id}' on {location}: Unknown key 'implementation.{key}' is ignored."
        for key in implementation
        if key not in ("check", "arguments")
    ]
    given = implementation.get("arguments") or {}
    if not isinstance(given, dict):
        raise unusable("implementation.arguments must be a mapping of argument names to values.")

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

    fallback_name = (
        quality.description
        or f"{check_id}({', '.join(f'{argument}={value_text(value)}' for argument, value in given.items())})"
    )

    if custom_quality_checks is None or (
        custom_quality_checks.directory is None and custom_quality_checks.api_key is None
    ):
        if custom_quality_checks is not None and custom_quality_checks.ignored_request_host is not None:
            raise unusable(
                f"The rule uses the custom quality check '{check_id}', but the request's API key belongs to its "
                f"entropy-data-host '{custom_quality_checks.ignored_request_host}', so set ENTROPY_DATA_HOST to that "
                "host on the server running the API."
            )
        raise unusable(
            f"The rule uses the custom quality check '{check_id}', but neither a custom quality checks folder nor "
            f"an Entropy Data API key is configured. Pass --custom-quality-checks, or set "
            f"DATACONTRACT_CUSTOM_QUALITY_CHECKS or ENTROPY_DATA_API_KEY.",
        )
    try:
        check = custom_quality_checks.load(check_id)
    except CustomQualityCheckError as e:
        raise unusable(str(e))

    undeclared = [argument for argument in given if argument not in check.arguments]
    if undeclared:
        raise unusable(
            f"The custom quality check '{check.id}' has no argument {', '.join(map(str, undeclared))}. "
            f"Its arguments are {', '.join(check.arguments) or 'none'}.",
            check,
        )
    missing = [argument for argument, spec in check.arguments.items() if spec.required and argument not in given]
    if missing:
        raise unusable(
            f"The custom quality check '{check.id}' needs the argument{'s' if len(missing) > 1 else ''} "
            f"{', '.join(missing)}.",
            check,
        )
    arguments = {
        argument: (spec.type == "identifier", given[argument] if argument in given else spec.default)
        for argument, spec in check.arguments.items()
    }
    # a variable resolves to text, so a number argument is read from its text
    for argument, spec in check.arguments.items():
        if spec.type == "number":
            value = arguments[argument][1]
            numbers = [
                (float(item) if "." in item else int(item))
                if isinstance(item, str) and _NUMBER.fullmatch(item)
                else item
                for item in (value if isinstance(value, list) else [value])
            ]
            arguments[argument] = (False, numbers if isinstance(value, list) else numbers[0])
    if quality.description:
        name = quality.description
    elif check.description:
        names = dict.fromkeys(TABLE_PLACEHOLDERS, model)
        if field_name is not None:
            names |= dict.fromkeys(COLUMN_PLACEHOLDERS, field_name)

        def fill(match: re.Match) -> str:
            if match.group(3) is not None:
                value = arguments[match.group(3)][1]
                text = ", ".join(map(str, value)) if isinstance(value, list) else str(value)
            elif match.group(2) in names:
                text = names[match.group(2)]
            else:
                return match.group(0)
            return match.group(1) + text + match.group(1)

        name = reference_pattern(TABLE_PLACEHOLDERS + COLUMN_PLACEHOLDERS).sub(fill, check.description)
    else:
        name = f"{check.id}({', '.join(f'{name}={value_text(value)}' for name, (_, value) in arguments.items())})"

    for argument, (identifier, value) in arguments.items():
        if identifier and (not isinstance(value, str) or not value):
            if isinstance(value, list):
                given_as = "a list"
            elif value == "":
                given_as = "an empty value"
            elif value is None:
                given_as = "no value"
            else:
                given_as = str(value).lower() if isinstance(value, bool) else str(value)
            raise unusable(
                f"${{arguments.{argument}}} must be the name of one column or table, such as {field_name or model}, "
                f"but got {given_as}.",
                check,
                name,
            )
        scalars = value if isinstance(value, list) else [value]
        if not identifier and not all(item is None or isinstance(item, (str, int, float, bool)) for item in scalars):
            raise unusable(f"${{arguments.{argument}}} must be a single value or a list of values.", check, name)
        if value == []:
            raise unusable(f"${{arguments.{argument}}} is an empty list. Give it at least one value.", check, name)
        if check.arguments[argument].type == "number":
            for item in scalars:
                if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item):
                    given_as = (
                        "no value" if item is None else repr(item).lower() if isinstance(item, bool) else repr(item)
                    )
                    raise unusable(f"${{arguments.{argument}}} must be a number, but got {given_as}.", check, name)
    column = placeholder_pattern(COLUMN_PLACEHOLDERS)
    if field_name is None and any(column.search(query) for query in check.queries.values()):
        raise unusable(
            f"The custom quality check '{check.id}' refers to the column, so declare it on a property.",
            check,
            name,
        )

    rule_has_expected = any(getattr(quality, key) is not None for key in COMPARATORS)
    if not rule_has_expected and not check.expected:
        raise unusable(
            f"Neither the rule nor the custom quality check '{check.id}' sets an expected result, such as mustBe.",
            check,
            name,
        )
    query_dialect = dialect if dialect in check.queries else DEFAULT_QUERY
    if query_dialect not in check.queries:
        raise unusable(
            f"The custom quality check '{check.id}' has no query for {dialect or 'this server'} and no default query. "
            f"It has queries for {', '.join(check.queries)}.",
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
            "custom_quality_check": check.id,
            "query": query_dialect,
            "expected_result_from": "rule" if rule_has_expected else "check",
        },
        warnings=rule_warnings + check.warnings,
    )


def sql_literal(value, dialect=None) -> str:
    """A value argument as a SQL literal; a list as comma-separated literals."""
    if isinstance(value, list):
        return ", ".join(sql_literal(item, dialect) for item in value)
    if isinstance(value, bool) and dialect == "tsql":
        # T-SQL has no boolean literals; sqlglot's `(1 = 1)` is a condition, not a value
        return "1" if value else "0"
    literal = exp.convert(value).sql(dialect=dialect)
    # `- -1` must not become `--1`, a comment
    return f"({literal})" if literal.startswith("-") else literal
