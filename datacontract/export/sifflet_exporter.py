"""Sifflet monitors-as-code generator for the ``sifflet`` export format.

Turns the quality rules of an ODCS data contract, plus monitors implied by the schema
(schema change, required, unique, primary key, format, pattern), into Sifflet monitor
YAML documents. ``sifflet.*`` custom properties on the contract, server, schema,
property, or rule tune the output. Nothing is sent to the Sifflet API.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum

import yaml
from open_data_contract_standard.model import (
    DataQuality,
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
)

from datacontract.export.exporter import Exporter

logger = logging.getLogger(__name__)

_SEVERITIES = ("Low", "Moderate", "High", "Critical")
_ODCS_SEVERITY = {"info": "Moderate", "warning": "High", "error": "Critical"}
_DEFAULT_SEVERITY = "Moderate"
# Sifflet alerts on any violation for these kinds when no threshold is given.
_ZERO_DEFAULT_KINDS = {"FieldInList", "FieldFormat", "FieldDuplicates"}
_PERCENT_UNITS = {"percent", "percentage", "%"}
_OPERATORS = {
    "mustBe": "eq",
    "mustBeGreaterThan": "gt",
    "mustBeGreaterOrEqualTo": "ge",
    "mustBeLessThan": "lt",
    "mustBeLessOrEqualTo": "le",
    "mustBeBetween": "between",
}


class _SiffletCustomProperty(str, Enum):
    """The ``sifflet.*`` custom properties the exporter reads."""

    ENABLED = "sifflet.enabled"
    IMPLICIT_MONITORS = "sifflet.implicitMonitors"
    FRIENDLY_ID = "sifflet.friendlyId"
    NAME = "sifflet.name"
    SEVERITY = "sifflet.severity"
    SCHEDULE = "sifflet.schedule"
    INCIDENT_MESSAGE = "sifflet.incidentMessage"
    CREATE_ON_FAILURE = "sifflet.createOnFailure"
    NOTIFICATIONS = "sifflet.notifications"
    TAGS = "sifflet.tags"
    THRESHOLD = "sifflet.threshold"
    PARAMETERS = "sifflet.parameters"
    DATASET_ID = "sifflet.datasetId"
    DATASOURCE_ID = "sifflet.datasourceId"
    DATASOURCE = "sifflet.datasource"


_KNOWN_PROPERTIES = set(_SiffletCustomProperty)
_QUALITY_ONLY = {_SiffletCustomProperty.FRIENDLY_ID, _SiffletCustomProperty.NAME}
_SCHEMA_ONLY = {_SiffletCustomProperty.DATASET_ID}
_SERVER_OR_CONTRACT = {_SiffletCustomProperty.DATASOURCE, _SiffletCustomProperty.DATASOURCE_ID}
_STRUCTURED = {
    _SiffletCustomProperty.NOTIFICATIONS,
    _SiffletCustomProperty.TAGS,
    _SiffletCustomProperty.THRESHOLD,
    _SiffletCustomProperty.PARAMETERS,
}
_BOOLEANS = {
    _SiffletCustomProperty.ENABLED,
    _SiffletCustomProperty.IMPLICIT_MONITORS,
    _SiffletCustomProperty.CREATE_ON_FAILURE,
}
_LIST_KEYS = {_SiffletCustomProperty.NOTIFICATIONS, _SiffletCustomProperty.TAGS}
_OBJECT_KEYS = {_SiffletCustomProperty.THRESHOLD, _SiffletCustomProperty.PARAMETERS}
_FORMATS = {"email": ("Email", "valid email"), "uuid": ("UUID", "valid UUID")}
_BACKTICK_DIALECTS = {"databricks", "bigquery", "mysql", "impala", "dataframe", "kafka"}
_ANSI_QUOTING_DIALECTS = {
    "postgres",
    "redshift",
    "sqlserver",
    "mssql",
    "snowflake",
    "azure",
    "s3",
    "gcs",
    "local",
    "hana",
}


class SkipRule(Exception):
    """A quality rule that cannot become a monitor. The caller logs the reason and drops the rule."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class _MonitorDraft:
    """A monitor document with what the collision and deduplication passes need to know about it.

    ``override`` is set when the friendlyId was given by the user (custom property, rule
    ``id`` or ``name``), so a collision is an error rather than a skipped rule.
    ``implicit`` marks monitors derived from the schema (schema change and property
    constraints) instead of from a quality rule.
    """

    friendly_id: str
    override: bool
    implicit: bool
    document: dict


@dataclass
class _SchemaContext:
    """What every monitor of one schema shares."""

    schema: SchemaObject
    server: Server
    dataset: dict
    contract_id: str
    version: str


def to_snake_case(value: str) -> str:
    """Token used inside a friendlyId.

    Splits camelCase, lowercases, turns every run of characters outside
    ``[a-z0-9]`` into one underscore, then drops leading and trailing underscores.
    ``café`` becomes ``caf``.
    """
    camel_case_pattern = re.compile(r"([a-z0-9])([A-Z])")
    text = camel_case_pattern.sub(r"\1_\2", str(value)).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def map_threshold(quality: DataQuality) -> dict | None:
    """Map ODCS operators to a Sifflet static threshold.

    Returns None when the rule sets no supported operator. Raises SkipRule when an
    operator is unsupported or the bounds contradict each other.
    """
    if quality.mustNotBe is not None or quality.mustNotBeBetween is not None:
        raise SkipRule("operator mustNotBe is not supported")
    if not any(getattr(quality, name) is not None for name in _OPERATORS):
        return None
    if quality.mustBeBetween is not None and len(quality.mustBeBetween) != 2:
        raise SkipRule("mustBeBetween must have exactly 2 values")

    # Each bound is (value, is_inclusive). An exact value bounds both sides.
    # Getting the candidate bounds from the ODCS operators.
    lower_bounds = [(quality.mustBeGreaterThan, False), (quality.mustBeGreaterOrEqualTo, True)]
    upper_bounds = [(quality.mustBeLessThan, False), (quality.mustBeLessOrEqualTo, True)]
    if quality.mustBeBetween is not None:
        lower_bounds.append((quality.mustBeBetween[0], True))
        upper_bounds.append((quality.mustBeBetween[1], True))
    if quality.mustBe is not None:
        lower_bounds.append((quality.mustBe, True))
        upper_bounds.append((quality.mustBe, True))

    # Dropping bounds that are not set.
    lower_bounds = [(value, is_inclusive) for value, is_inclusive in lower_bounds if value is not None]
    upper_bounds = [(value, is_inclusive) for value, is_inclusive in upper_bounds if value is not None]

    try:
        # The tightest bound wins. At the same value, a non-inclusive bound is tighter.
        lower_bound = max(lower_bounds, key=lambda bound: (bound[0], not bound[1]), default=None)
        upper_bound = min(upper_bounds, key=lambda bound: (bound[0], bound[1]), default=None)
        if lower_bound is not None and upper_bound is not None:
            (lower_value, lower_is_inclusive), (upper_value, upper_is_inclusive) = lower_bound, upper_bound
            no_value_left = lower_value > upper_value or (
                lower_value == upper_value and not (lower_is_inclusive and upper_is_inclusive)
            )
            if no_value_left:
                raise SkipRule("threshold operators conflict")
    # Bounds of incomparable types, such as a number and a string.
    except TypeError:
        raise SkipRule("threshold operators conflict") from None

    threshold = {"kind": "Static"}
    if lower_bound is not None:
        threshold["min"], threshold["isMinInclusive"] = lower_bound
    if upper_bound is not None:
        threshold["max"], threshold["isMaxInclusive"] = upper_bound
    return threshold


def _require_severity(value) -> str:
    if value not in _SEVERITIES:
        raise RuntimeError(f"sifflet.severity '{value}' is not one of Low, Moderate, High, Critical.")
    return value


def map_severity(quality: DataQuality | None, quality_props: dict, inherited: list[dict], friendly_id: str) -> str:
    """Resolve the incident severity.

    Precedence: the rule's ``sifflet.severity``, then its ODCS ``severity`` (info, warning,
    error map to Moderate, High, Critical; any other value gives Moderate with a warning),
    then ``sifflet.severity`` inherited from the property, schema, or contract, then
    Moderate. Raises on a ``sifflet.severity`` that is not a Sifflet severity.
    """
    if quality is not None and _SiffletCustomProperty.SEVERITY in quality_props:
        return _require_severity(quality_props[_SiffletCustomProperty.SEVERITY])
    if quality is not None and quality.severity:
        mapped = _ODCS_SEVERITY.get(str(quality.severity).lower())
        if mapped:
            return mapped
        logger.warning(
            f"Rule {friendly_id}: severity '{quality.severity}' is not info, warning, or error; using Moderate."
        )
        return _DEFAULT_SEVERITY
    for sifflet_props in inherited:
        if _SiffletCustomProperty.SEVERITY in sifflet_props:
            return _require_severity(sifflet_props[_SiffletCustomProperty.SEVERITY])
    return _DEFAULT_SEVERITY


def map_schedule(
    quality: DataQuality | None, quality_props: dict, inherited: list[dict], friendly_id: str
) -> str | None:
    """Return the cron expression to write, or None when the schedule key is omitted.

    Precedence: the rule's ``sifflet.schedule``, then its ODCS ``schedule``, then
    ``sifflet.schedule`` inherited from the property, schema, or contract. An ODCS schedule
    with a scheduler other than cron gives no schedule, without falling back to inherited ones.
    """
    if _SiffletCustomProperty.SCHEDULE in quality_props:
        return _validate_cron(quality_props[_SiffletCustomProperty.SCHEDULE], friendly_id)
    if quality is not None and quality.schedule:
        scheduler = quality.scheduler or "cron"
        if str(scheduler).lower() != "cron":
            logger.warning(
                f"Rule {friendly_id}: scheduler '{scheduler}' is not supported by Sifflet; "
                "monitor exported without schedule."
            )
            return None
        return _validate_cron(quality.schedule, friendly_id)
    for sifflet_props in inherited:
        if _SiffletCustomProperty.SCHEDULE in sifflet_props:
            return _validate_cron(sifflet_props[_SiffletCustomProperty.SCHEDULE], friendly_id)
    return None


def prepare_query(query: str, table_name: str, field_name: str | None, server: Server) -> str:
    """Replace ODCS placeholders with identifiers quoted for the server's dialect.

    Quotes written around a replaced placeholder are dropped; unknown placeholders, and
    field placeholders on a table-level rule, are left as written. ``${object}`` becomes the fully
    qualified table name built from the server's catalog, database or project and its
    schema or dataset; ``${model}`` and ``${table}`` stay the bare table name.
    """
    if not query:
        return query

    def quote(identifier: str) -> str:
        if server.type in _ANSI_QUOTING_DIALECTS:
            return f'"{identifier}"'
        if server.type in _BACKTICK_DIALECTS:
            return f"`{identifier}`"
        return identifier

    def first(*keys: str) -> str | None:
        return next((getattr(server, key) for key in keys if getattr(server, key, None)), None)

    table = quote(table_name)
    qualified = [first("project", "catalog", "database"), first("dataset", "schema_"), table_name]
    names = {"model": table, "table": table, "object": ".".join(quote(part) for part in qualified if part)}
    names["schema"] = quote(server.schema_) if server.schema_ else table
    for key in ("dataset", "project", "catalog", "database"):
        value = getattr(server, key, None)
        names[key] = quote(value) if value else table
    if field_name is not None:
        for key in ("field", "column", "property"):
            names[key] = quote(field_name)

    def replace(match: re.Match) -> str:
        key = match.group(1)
        if key not in names:
            return match.group(0)
        return str(names[key])

    # ``${name}`` or ``{name}``. A quote directly before or after belongs to the match.
    # Replacing a known name removes that quote; an unknown name is left as written.
    query_placeholder_pattern = re.compile(r"['\"]?\$?\{([A-Za-z_]\w*)\}['\"]?", re.ASCII)

    return query_placeholder_pattern.sub(replace, query)


def select_server(data_contract: OpenDataContractStandard, server_name: str | None) -> Server:
    """Return the named server, or the first one when no name is given."""
    servers = data_contract.servers or []
    if not servers:
        raise RuntimeError("Export to sifflet requires a server in the data contract.")
    if server_name is None:
        return servers[0]
    found = next((server for server in servers if server.server == server_name), None)
    if found is None:
        names = [server.server for server in servers]
        raise RuntimeError(f"Server '{server_name}' not found in the data contract. Available servers: {names}")
    return found


def select_schemas(data_contract: OpenDataContractStandard, schema_name: str) -> list[SchemaObject]:
    """Return every schema for ``all``, otherwise the one with that name."""
    schemas = list(data_contract.schema_ or [])
    if not schemas:
        raise RuntimeError("Export to sifflet requires schema in the data contract.")
    if schema_name == "all":
        return schemas
    found = next((schema for schema in schemas if schema.name == schema_name), None)
    if found is None:
        names = [schema.name for schema in schemas]
        raise RuntimeError(f"Schema '{schema_name}' not found in the data contract. Available schemas: {names}")
    return [found]


class SiffletExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> str:
        """Render one YAML document per monitor.

        Implicit monitors are dropped when an explicit rule already monitors the same thing.
        """
        contract_id = data_contract.id or "unknown"
        version = data_contract.version or "unknown"
        selected_server = select_server(data_contract, server)
        contract_sifflet_props = _read_sifflet_custom_properties(data_contract, "contract")
        server_sifflet_props = _read_sifflet_custom_properties(selected_server, "server")
        monitor_drafts = []
        for schema in select_schemas(data_contract, schema_name or "all"):
            schema_monitor_drafts = _build_schema_monitors(
                schema, selected_server, contract_sifflet_props, server_sifflet_props, contract_id, version
            )
            monitor_drafts.extend(schema_monitor_drafts)
        monitor_drafts = _resolve_collisions(monitor_drafts)
        # What the explicit rules already monitor (kind, field, format, values, whatever the threshold),
        # so that the implicit monitors duplicating them can be dropped below.
        explicit_monitor_signatures = {
            _monitor_signature(draft.document["parameters"]) for draft in monitor_drafts if not draft.implicit
        }
        # Keep every explicit monitor, and an implicit one only when no explicit monitor checks the same thing.
        monitors_to_export = [
            draft.document
            for draft in monitor_drafts
            if not draft.implicit or _monitor_signature(draft.document["parameters"]) not in explicit_monitor_signatures
        ]
        header = (
            f"# Generated by datacontract-cli `export sifflet` from {contract_id} v{version}.\n"
            "# Do not edit by hand – edit the data contract and re-export.\n"
        )
        if not monitors_to_export:
            return header
        return header + yaml.dump_all(monitors_to_export, sort_keys=False, allow_unicode=True, default_flow_style=False)


def _implicit_monitors_enabled(levels: list[dict]) -> bool:
    return _lookup(levels, _SiffletCustomProperty.ENABLED, True) and _lookup(
        levels, _SiffletCustomProperty.IMPLICIT_MONITORS, True
    )


def _build_schema_monitors(schema, server, contract_props, server_props, contract_id, version) -> list[_MonitorDraft]:
    """Build the drafts of one schema: its implicit monitors, then its quality rules and its properties'.

    ``sifflet.*`` custom properties are looked up across levels ordered from the most specific level to the
    contract; the datasource is read from the server first, then the contract.
    """
    schema_sifflet_props = _read_sifflet_custom_properties(schema, "schema")
    schema_levels = [schema_sifflet_props, contract_props]
    datasource_levels = [server_props, contract_props]
    datasource = {"name": _lookup(datasource_levels, _SiffletCustomProperty.DATASOURCE) or server.server}
    datasource_id = _lookup(datasource_levels, _SiffletCustomProperty.DATASOURCE_ID)
    if datasource_id:
        datasource["id"] = datasource_id
    dataset = {"name": _physical_name(schema)}
    if _SiffletCustomProperty.DATASET_ID in schema_sifflet_props:
        dataset["id"] = schema_sifflet_props[_SiffletCustomProperty.DATASET_ID]
    dataset["datasource"] = datasource
    context = _SchemaContext(schema, server, dataset, contract_id, version)
    columns = [column for column in schema.properties or [] if column.name]
    for column in columns:
        if column.properties or column.items:
            logger.warning(
                f"Nested properties are not exported to Sifflet: schema[{schema.name}].properties[{column.name}]"
            )
    monitor_drafts = []
    primary_keys = [column for column in columns if column.primaryKey]
    # A composite primary key is monitored at schema level; a single-column one is that column's unique monitor.
    has_composite_primary_key = len(primary_keys) > 1
    if _implicit_monitors_enabled(schema_levels):
        monitors_to_build = [("schema_change", "schema change", {"kind": "SchemaChange"})]
        if has_composite_primary_key:
            fields = [_physical_name(column) for column in primary_keys]
            monitors_to_build.append(("primary_key", "primary key", {"kind": "FieldDuplicates", "field": fields}))
        monitor_drafts.extend(
            _build_implicit_monitor(context, None, suffix, label, parameters, schema_levels)
            for suffix, label, parameters in monitors_to_build
        )
    for index, quality in enumerate(schema.quality or []):
        quality_monitor_draft = _build_quality_monitor(context, quality, None, index, schema_levels)
        if quality_monitor_draft:
            monitor_drafts.append(quality_monitor_draft)
    for column in columns:
        column_sifflet_props = _read_sifflet_custom_properties(column, "property")
        column_levels = [column_sifflet_props, *schema_levels]
        if _implicit_monitors_enabled(column_levels):
            is_unique = column.unique or (column.primaryKey and not has_composite_primary_key)
            property_monitor_drafts = _build_property_implicit_monitors(context, column, is_unique, column_levels)
            monitor_drafts.extend(property_monitor_drafts)
        for index, quality in enumerate(column.quality or []):
            quality_monitor_draft = _build_quality_monitor(context, quality, column, index, column_levels)
            if quality_monitor_draft:
                monitor_drafts.append(quality_monitor_draft)
    return monitor_drafts


def _build_property_implicit_monitors(
    context: _SchemaContext, prop: SchemaProperty, is_unique: bool, levels: list[dict]
) -> list[_MonitorDraft]:
    """Monitors implied by a property: not null, unique, email or UUID format, and pattern."""
    field = _physical_name(prop)
    options = prop.logicalTypeOptions if isinstance(prop.logicalTypeOptions, dict) else {}
    format_name = options.get("format")
    pattern = options.get("pattern")

    implicit_monitors_to_build = []
    if prop.required:
        implicit_monitors_to_build.append(
            ("required", "not null", {"kind": "FieldNulls", "field": field, "valueMode": "Count"})
        )
    if is_unique:
        implicit_monitors_to_build.append(("unique", "unique", {"kind": "FieldDuplicates", "field": field}))
    if format_name:
        normalized = str(format_name).lower()
        if normalized in _FORMATS:
            format_kind, label = _FORMATS[normalized]
            format_parameters = {"kind": "FieldFormat", "field": field, "format": {"kind": format_kind}}
            implicit_monitors_to_build.append((f"format_{normalized}", label, format_parameters))
        else:
            logger.warning(
                f"Rule at schema[{context.schema.name}].properties[{prop.name}]: format '{format_name}' is not "
                "supported for an implicit Sifflet monitor; skipped."
            )
    if pattern:
        pattern_parameters = {"kind": "FieldFormat", "field": field, "format": {"kind": "Regex", "regex": pattern}}
        implicit_monitors_to_build.append(("format_regex", "matches pattern", pattern_parameters))

    implicit_monitor_drafts = [
        _build_implicit_monitor(context, prop, suffix, label, parameters, levels)
        for suffix, label, parameters in implicit_monitors_to_build
    ]
    return implicit_monitor_drafts


def _build_implicit_monitor(
    context: _SchemaContext,
    prop: SchemaProperty | None,
    suffix: str,
    label: str,
    parameters: dict,
    levels: list[dict],
) -> _MonitorDraft:
    schema_name = context.schema.name
    friendly_id = _join_id(schema_name, prop.name if prop else None, suffix)
    return _MonitorDraft(
        friendly_id=friendly_id,
        override=False,
        implicit=True,
        document=_document(
            friendly_id=friendly_id,
            name=_monitor_name(schema_name, prop.name if prop else None, label),
            description=_description(None, context.contract_id, context.version),
            schedule=map_schedule(None, {}, levels, friendly_id),
            severity=map_severity(None, {}, levels, friendly_id),
            message=_lookup(levels, _SiffletCustomProperty.INCIDENT_MESSAGE),
            create_on_failure=_lookup(levels, _SiffletCustomProperty.CREATE_ON_FAILURE),
            notifications=_lookup(levels, _SiffletCustomProperty.NOTIFICATIONS),
            tags=_lookup(levels, _SiffletCustomProperty.TAGS),
            dataset=context.dataset,
            parameters=parameters,
        ),
    )


def _build_quality_monitor(
    context: _SchemaContext,
    quality: DataQuality,
    prop: SchemaProperty | None,
    index: int,
    parent_levels: list[dict],
) -> _MonitorDraft | None:
    """Build the draft of one library or SQL quality rule, or return None when the rule is skipped.

    A SQL rule with no ``sifflet.friendlyId``, ``id``, or ``name`` is skipped.
    """
    schema_name = context.schema.name
    column_name = prop.name if prop else None
    if column_name:
        path = f"schema[{schema_name}].properties[{column_name}].quality[{index}]"
    else:
        path = f"schema[{schema_name}].quality[{index}]"
    quality_sifflet_props = _read_sifflet_custom_properties(quality, "quality")
    levels = [quality_sifflet_props, *parent_levels]
    if not _lookup(levels, _SiffletCustomProperty.ENABLED, True):
        return None
    kind = _quality_kind(quality)
    if kind in ("custom", "text"):
        logger.debug(f"Rule at {path}: type {kind} is not exported.")
        return None
    if kind not in ("sql", "library"):
        logger.warning(f"Rule at {path}: type '{quality.type}' is not supported; rule skipped.")
        return None

    metric = _metric_name(quality)
    if kind == "library" and not metric:
        logger.warning(f"Rule at {path}: library rule has no metric; rule skipped.")
        return None
    if kind == "sql" and not (
        _SiffletCustomProperty.FRIENDLY_ID in quality_sifflet_props or quality.id or quality.name
    ):
        logger.warning(
            f"Rule at {path}: 'id' or 'name' is required for SQL quality rules in the Sifflet export; rule skipped."
        )
        return None
    friendly_id, override = _quality_friendly_id(quality, quality_sifflet_props, schema_name, column_name, metric)

    inherited = levels[1:]
    try:
        if kind == "sql":
            field = _physical_name(prop) if prop is not None else None
            parameters = {
                "kind": "CustomMetrics",
                "sql": prepare_query(quality.query or "", context.dataset["name"], field, context.server),
            }
        else:
            parameters = _library_parameters(quality, prop, friendly_id)
        _attach_threshold(parameters, quality, quality_sifflet_props, friendly_id, kind == "sql")
    except SkipRule as error:
        logger.warning(f"Rule {friendly_id}: {error.reason}; rule skipped.")
        return None
    # sifflet.parameters completes the built parameters. kind is already set from the metric or the SQL rule.
    extra_parameters = quality_sifflet_props.get(_SiffletCustomProperty.PARAMETERS)
    if isinstance(extra_parameters, dict):
        extra_parameters = dict(extra_parameters)
        if "kind" in extra_parameters:
            logger.warning(f"Rule {friendly_id}: sifflet.parameters cannot change kind; kind ignored.")
            del extra_parameters["kind"]
        parameters = _deep_merge(parameters, extra_parameters)

    name = quality_sifflet_props.get(_SiffletCustomProperty.NAME)
    if name is None:
        label = _label(quality, metric)
        name = _monitor_name(schema_name, column_name, label)
    else:
        name = str(name)
    return _MonitorDraft(
        friendly_id=friendly_id,
        override=override,
        implicit=False,
        document=_document(
            friendly_id=friendly_id,
            name=name,
            description=_description(quality, context.contract_id, context.version),
            schedule=map_schedule(quality, quality_sifflet_props, inherited, friendly_id),
            severity=map_severity(quality, quality_sifflet_props, inherited, friendly_id),
            message=_lookup(levels, _SiffletCustomProperty.INCIDENT_MESSAGE) or quality.description or None,
            create_on_failure=_lookup(levels, _SiffletCustomProperty.CREATE_ON_FAILURE),
            notifications=_lookup(levels, _SiffletCustomProperty.NOTIFICATIONS),
            tags=_lookup(levels, _SiffletCustomProperty.TAGS),
            dataset=context.dataset,
            parameters=parameters,
        ),
    )


def _quality_friendly_id(
    quality: DataQuality,
    quality_sifflet_props: dict,
    schema_name: str,
    column_name: str | None,
    metric: str | None,
) -> tuple[str, bool]:
    """The rule's friendlyId, and whether the user gave it.

    The id is ``sifflet.friendlyId``, else ``id``, else ``name`` in snake case. With none
    of these it is computed from the schema, property, metric, and operator, and the
    second value is False so a later collision skips the rule instead of failing.
    """
    if _SiffletCustomProperty.FRIENDLY_ID in quality_sifflet_props:
        return str(quality_sifflet_props[_SiffletCustomProperty.FRIENDLY_ID]), True
    if quality.id:
        return str(quality.id), True
    if quality.name:
        return to_snake_case(quality.name), True

    parts = [schema_name, column_name, "library", metric]
    for operator, token in _OPERATORS.items():
        value = getattr(quality, operator)
        if value is not None:
            parts.append(token)
            bounds = value if operator == "mustBeBetween" else [value]
            parts.extend(_num(bound) for bound in bounds)
    return _join_id(*parts), False


def _library_parameters(quality, prop, friendly_id) -> dict:
    """Map an ODCS library metric to Sifflet monitor parameters, without the threshold.

    Raises SkipRule for a metric that has no Sifflet equivalent at the rule's level, and
    for an invalidValues rule that needs exactly one of a ``validValues`` list or a ``pattern``.
    """
    metric = _metric_name(quality)
    arguments = quality.arguments if isinstance(quality.arguments, dict) else {}
    level = "property" if prop is not None else "table"
    if level == "property":
        field = _physical_name(prop)
        if metric == "nullValues":
            return _field_nulls(quality, field)
        if metric == "missingValues":
            ignored = [value for value in arguments.get("missingValues") or [] if value is not None]
            if ignored:
                listed = ", ".join(repr(value) for value in ignored)
                logger.warning(f"Rule {friendly_id}: only NULL values are monitored; {listed} ignored.")
            return _field_nulls(quality, field)
        if metric == "invalidValues":
            has_values = arguments.get("validValues") is not None
            has_pattern = bool(arguments.get("pattern"))
            if has_values and has_pattern:
                raise SkipRule("invalidValues has both validValues and pattern")
            if has_values:
                if not isinstance(arguments["validValues"], list):
                    raise SkipRule("invalidValues validValues must be a list")
                return {"kind": "FieldInList", "field": field, "values": list(arguments["validValues"])}
            if has_pattern:
                return {
                    "kind": "FieldFormat",
                    "field": field,
                    "format": {"kind": "Regex", "regex": arguments["pattern"]},
                }
            raise SkipRule("invalidValues needs validValues or pattern")
        if metric == "duplicateValues":
            if arguments.get("properties"):
                logger.warning(
                    f"Rule {friendly_id}: arguments.properties is ignored for a property-level duplicateValues rule."
                )
            return {"kind": "FieldDuplicates", "field": field}
    else:
        if metric == "duplicateValues":
            columns = arguments.get("properties")
            if isinstance(columns, list) and columns:
                return {"kind": "FieldDuplicates", "field": list(columns)}
            return {"kind": "RowDuplicates"}
        if metric == "rowCount":
            if _is_percent(quality):
                logger.warning(
                    f"Rule {friendly_id}: unit 'percent' is ignored for rowCount; threshold exported as a row count."
                )
            return {"kind": "Volume"}
    raise SkipRule(f"metric '{metric}' is not supported at {level} level")


def _field_nulls(quality, field) -> dict:
    mode = "Percentage" if _is_percent(quality) else "Count"
    return {"kind": "FieldNulls", "field": field, "valueMode": mode}


def _attach_threshold(parameters, quality, quality_props, friendly_id, is_sql: bool):
    """Add the threshold to ``parameters`` in place.

    ``sifflet.threshold`` is used as is. Otherwise the threshold comes from the ODCS
    operators. It is left out for the zero-default kinds when there is no operator or the
    operators mean exactly zero, and for a SQL rule without an operator, which then gets
    Sifflet's dynamic threshold. Raises SkipRule when any other rule has no operator, or
    when ``map_threshold`` rejects the operators.
    """
    if _SiffletCustomProperty.THRESHOLD in quality_props:
        parameters["threshold"] = quality_props[_SiffletCustomProperty.THRESHOLD]
        return
    operator_threshold = map_threshold(quality)
    kind = parameters["kind"]
    if operator_threshold is None and kind in _ZERO_DEFAULT_KINDS:
        return
    if operator_threshold is None and is_sql:
        logger.warning(
            f"Rule {friendly_id}: no operator given; monitor exported without threshold, "
            "Sifflet's default dynamic threshold applies."
        )
        return
    if operator_threshold is None:
        raise SkipRule("no operator given")
    exact_zero = {"kind": "Static", "min": 0, "isMinInclusive": True, "max": 0, "isMaxInclusive": True}
    if kind in _ZERO_DEFAULT_KINDS and operator_threshold == exact_zero:
        return
    parameters["threshold"] = operator_threshold


def _document(
    friendly_id,
    name,
    description,
    schedule,
    severity,
    message,
    create_on_failure,
    notifications,
    tags,
    dataset,
    parameters,
) -> dict:
    """One Sifflet monitor document.

    ``message``, ``schedule``, ``notifications``, and ``tags`` are omitted when empty.
    ``createOnFailure`` is omitted only when it is None, so an explicit false is kept.
    """
    incident = {"severity": severity}
    if message:
        incident["message"] = message
    if create_on_failure is not None:
        incident["createOnFailure"] = create_on_failure
    document = {
        "kind": "Monitor",
        "version": 2,
        "friendlyId": friendly_id,
        "name": name,
        "description": description,
    }
    if schedule:
        document["schedule"] = schedule
    document["incident"] = incident
    if notifications:
        document["notifications"] = notifications
    if tags:
        document["tags"] = tags
    document["datasets"] = [dataset]
    document["parameters"] = parameters
    return document


def _label(quality, metric) -> str:
    """Human-readable part of the monitor name: the rule's name, or a phrase built from its metric."""
    if quality.name:
        return quality.name
    phrase = _operator_phrase(quality)
    prefixes = {"nullValues": "null values", "missingValues": "missing values", "rowCount": "row count"}
    if metric in prefixes and phrase:
        return f"{prefixes[metric]} {phrase}"
    if metric == "invalidValues":
        arguments = quality.arguments if isinstance(quality.arguments, dict) else {}
        if arguments.get("pattern") and not arguments.get("validValues"):
            return "matches pattern"
        return "values in list"
    if metric == "duplicateValues":
        return "no duplicates"
    return metric or "quality"


def _operator_phrase(quality) -> str | None:
    parts = []
    if quality.mustBeGreaterThan is not None:
        parts.append(f"> {_num(quality.mustBeGreaterThan)}")
    if quality.mustBeGreaterOrEqualTo is not None:
        parts.append(f">= {_num(quality.mustBeGreaterOrEqualTo)}")
    if quality.mustBeLessThan is not None:
        parts.append(f"< {_num(quality.mustBeLessThan)}")
    if quality.mustBeLessOrEqualTo is not None:
        parts.append(f"<= {_num(quality.mustBeLessOrEqualTo)}")
    if quality.mustBeBetween is not None and len(quality.mustBeBetween) == 2:
        parts.append(f"between {_num(quality.mustBeBetween[0])} and {_num(quality.mustBeBetween[1])}")
    if quality.mustBe is not None:
        parts.append(f"= {_num(quality.mustBe)}")
    return " and ".join(parts) if parts else None


def _description(quality, contract_id, version) -> str:
    source = f"Source: data contract {contract_id} v{version}"
    if quality is not None and quality.description:
        return f"{quality.description} — {source}"
    return source


def _monitor_name(table, column, label) -> str:
    subject = f"{table}.{column}" if column else table
    return f"{subject} – {label}"


def _join_id(*parts) -> str:
    """Join non-empty parts with underscores, snake-casing the ones that are not already lowercase tokens."""
    tokens = []
    for part in parts:
        if part is None or part == "":
            continue
        is_token = isinstance(part, str) and part.replace("_", "").isalnum() and part == part.lower()
        token = part if is_token else to_snake_case(part)
        if token:
            tokens.append(token)
    return "_".join(tokens)


def _quality_kind(quality) -> str:
    """Classify a rule as custom, text, sql, library, or other.

    custom, text, and sql come from ``type``. Any other or missing type is library when
    ``type`` is library or a metric is set, else sql when a query is set, else other.
    """
    if quality.type in ("custom", "text", "sql"):
        return quality.type
    if quality.type == "library" or _metric_name(quality):
        return "library"
    if quality.query:
        return "sql"
    return "other"


def _metric_name(quality) -> str | None:
    """The library metric, read from ``metric`` or from ``rule``, its name in ODCS v3.0."""
    metric = quality.metric or getattr(quality, "rule", None)
    if metric is None:
        return None
    value = getattr(metric, "value", metric)
    text = str(value).strip()
    return text or None


def _physical_name(element) -> str:
    return element.physicalName or element.name


def _is_percent(quality) -> bool:
    unit = getattr(quality, "unit", None)
    return unit is not None and str(unit).strip().lower() in _PERCENT_UNITS


def _validate_cron(value, friendly_id) -> str | None:
    """Return the trimmed schedule, or None when empty. A value that does not look like cron is kept, with a warning."""
    text = str(value).strip()
    if not text:
        return None
    if not (text.startswith("@") or len(text.split()) == 5):
        logger.warning(
            f"Rule {friendly_id}: schedule '{text}' is not a 5-field cron or a @ macro; value passed through."
        )
    return text


def _read_sifflet_custom_properties(element, level: str) -> dict:
    """Collect the ``sifflet.*`` custom properties of a contract element.

    ``level`` is the kind of element (contract, server, schema, property, or quality).
    Unknown keys, keys set at a level that does not read them, and values of the wrong
    type are dropped with a warning; structured values and booleans are parsed.
    """
    found = {}
    for entry in getattr(element, "customProperties", None) or []:
        key = getattr(entry, "property", None)
        if not key or not str(key).startswith("sifflet."):
            continue
        if key not in _KNOWN_PROPERTIES:
            logger.warning(f"Unknown Sifflet custom property '{key}'.")
            continue
        if key in _QUALITY_ONLY and level != "quality":
            logger.warning(f"{key} is only read on a quality rule; ignored.")
            continue
        if key in _SCHEMA_ONLY and level != "schema":
            logger.warning(f"{key} is only read on a schema object; ignored.")
            continue
        if key in _SERVER_OR_CONTRACT and level not in ("server", "contract"):
            logger.warning(f"{key} is only read on a server or the contract; ignored.")
            continue
        if level == "server" and key not in _SERVER_OR_CONTRACT:
            logger.warning(f"{key} is not read on a server; ignored.")
            continue
        value = entry.value
        if key in _STRUCTURED:
            value = _parse_yaml_list_or_object(key, value)
            if value is None:
                continue
        if key in _BOOLEANS:
            if isinstance(value, str) and value.lower() in ("true", "false"):
                value = value.lower() == "true"
            elif not isinstance(value, bool):
                logger.warning(f"{key} value {value!r} is not a boolean; ignored.")
                continue
        found[key] = value
    return found


def _parse_yaml_list_or_object(key: str, value: object) -> list | dict | None:
    """Parse a list or object value, which may be written as a YAML string. Returns None when invalid."""
    if isinstance(value, str):
        try:
            value = yaml.safe_load(value)
        except yaml.YAMLError:
            logger.warning(f"{key} value {value!r} is not valid YAML; ignored.")
            return None
    if key in _LIST_KEYS and isinstance(value, tuple):
        value = list(value)
    if key in _LIST_KEYS and not isinstance(value, list):
        logger.warning(f"{key} value must be a list; ignored.")
        return None
    if key in _OBJECT_KEYS and not isinstance(value, dict):
        logger.warning(f"{key} value must be an object; ignored.")
        return None
    return value


def _lookup(levels: list[dict[str, object]], key: str, default: object = None) -> object:
    """Value of ``key`` in the first level that sets it.

    ``levels`` lists the ``sifflet.*`` custom properties of each level, as read by
    ``_read_sifflet_custom_properties``, from the most specific level (quality rule, column) to the contract.
    """
    for sifflet_props in levels:
        if key in sifflet_props:
            return sifflet_props[key]
    return default


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge nested dicts key by key; any other value in ``override`` replaces the one in ``base``."""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _resolve_collisions(drafts: list[_MonitorDraft]) -> list[_MonitorDraft]:
    """Keep one draft per friendlyId.

    Raises when a user-given friendlyId is shared; when only computed ones are, the
    first draft wins and the others are skipped with a warning.
    """
    groups: dict[str, list[_MonitorDraft]] = {}
    for draft in drafts:
        groups.setdefault(draft.friendly_id, []).append(draft)
    colliding = [
        friendly_id for friendly_id, group in groups.items() if len(group) > 1 and any(d.override for d in group)
    ]
    if colliding:
        listed = ", ".join(colliding)
        raise RuntimeError(f"Colliding friendlyId: {listed}. Give each rule a distinct id or name.")
    skipped = set()
    for friendly_id, group in groups.items():
        if len(group) < 2:
            continue
        for draft in group[1:]:
            skipped.add(id(draft))
            logger.warning(f"Rule {friendly_id}: duplicate friendlyId; later rule skipped. Give the rule an id.")
    return [draft for draft in drafts if id(draft) not in skipped]


def _monitor_signature(parameters: dict) -> tuple:
    """Signature of what a monitor checks: kind, field, format, and allowed values.

    The threshold is left out, so two monitors match when they check the same thing.
    """
    field = parameters.get("field")
    field_key = tuple(field) if isinstance(field, list) else field
    fmt = parameters.get("format") if isinstance(parameters.get("format"), dict) else {}
    values = parameters.get("values")
    values_key = tuple(values) if isinstance(values, list) else values
    return (parameters.get("kind"), field_key, fmt.get("kind"), fmt.get("regex"), values_key)


def _num(value) -> str:
    """Format a bound for names and IDs, dropping the ``.0`` of whole floats."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
