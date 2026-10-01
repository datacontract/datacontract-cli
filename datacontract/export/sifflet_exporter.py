import logging
import re
from dataclasses import dataclass

import yaml
from open_data_contract_standard.model import DataQuality, OpenDataContractStandard, SchemaObject, Server

from datacontract.export.exporter import Exporter

logger = logging.getLogger(__name__)

_SEVERITIES = ("Low", "Moderate", "High", "Critical")
_ODCS_SEVERITY = {"info": "Moderate", "warning": "High", "error": "Critical"}
_DEFAULT_SEVERITY = "Moderate"
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
_KNOWN_PROPERTIES = {
    "sifflet.enabled",
    "sifflet.implicitMonitors",
    "sifflet.friendlyId",
    "sifflet.name",
    "sifflet.severity",
    "sifflet.schedule",
    "sifflet.incidentMessage",
    "sifflet.createOnFailure",
    "sifflet.notifications",
    "sifflet.tags",
    "sifflet.threshold",
    "sifflet.parameters",
    "sifflet.datasetId",
    "sifflet.datasourceId",
    "sifflet.datasource",
}
_QUALITY_ONLY = {"sifflet.friendlyId", "sifflet.name"}
_SCHEMA_ONLY = {"sifflet.datasetId"}
_SERVER_OR_CONTRACT = {"sifflet.datasource", "sifflet.datasourceId"}
_STRUCTURED = {"sifflet.notifications", "sifflet.tags", "sifflet.threshold", "sifflet.parameters"}
_BOOLEANS = {"sifflet.enabled", "sifflet.implicitMonitors", "sifflet.createOnFailure"}
_LIST_KEYS = {"sifflet.notifications", "sifflet.tags"}
_OBJECT_KEYS = {"sifflet.threshold", "sifflet.parameters"}
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
_PLACEHOLDER = re.compile(r"""["']?\$?\{([A-Za-z_][A-Za-z0-9_]*)\}["']?""")
_CAMEL = re.compile(r"([a-z0-9])([A-Z])")


class SkipRule(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class _Draft:
    friendly_id: str
    override: bool
    implicit: bool
    document: dict


def snake(value: str) -> str:
    """Token used inside a friendlyId.

    Splits camelCase, lowercases, turns every run of characters outside
    ``[a-z0-9]`` into one underscore, then drops leading and trailing underscores.
    ``café`` becomes ``caf``.
    """
    text = _CAMEL.sub(r"\1_\2", str(value)).lower()
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

    lower = None
    lower_inclusive = None
    upper = None
    upper_inclusive = None

    def tighten_lower(value, inclusive: bool):
        nonlocal lower, lower_inclusive
        if lower is None or value > lower:
            lower, lower_inclusive = value, inclusive
        elif value == lower:
            lower_inclusive = bool(lower_inclusive and inclusive)

    def tighten_upper(value, inclusive: bool):
        nonlocal upper, upper_inclusive
        if upper is None or value < upper:
            upper, upper_inclusive = value, inclusive
        elif value == upper:
            upper_inclusive = bool(upper_inclusive and inclusive)

    try:
        if quality.mustBeGreaterThan is not None:
            tighten_lower(quality.mustBeGreaterThan, False)
        if quality.mustBeGreaterOrEqualTo is not None:
            tighten_lower(quality.mustBeGreaterOrEqualTo, True)
        if quality.mustBeLessThan is not None:
            tighten_upper(quality.mustBeLessThan, False)
        if quality.mustBeLessOrEqualTo is not None:
            tighten_upper(quality.mustBeLessOrEqualTo, True)
        if quality.mustBeBetween is not None:
            tighten_lower(quality.mustBeBetween[0], True)
            tighten_upper(quality.mustBeBetween[1], True)
        if quality.mustBe is not None:
            value = quality.mustBe
            if (lower is not None and (value < lower or (value == lower and not lower_inclusive))) or (
                upper is not None and (value > upper or (value == upper and not upper_inclusive))
            ):
                raise SkipRule("threshold operators conflict")
            lower = upper = value
            lower_inclusive = upper_inclusive = True
        if (
            lower is not None
            and upper is not None
            and (lower > upper or (lower == upper and not (lower_inclusive and upper_inclusive)))
        ):
            raise SkipRule("threshold operators conflict")
    except TypeError:
        raise SkipRule("threshold operators conflict") from None

    threshold = {"kind": "Static"}
    if lower is not None:
        threshold["min"] = lower
        threshold["isMinInclusive"] = lower_inclusive
    if upper is not None:
        threshold["max"] = upper
        threshold["isMaxInclusive"] = upper_inclusive
    return threshold


def map_severity(quality: DataQuality | None, quality_props: dict, inherited: list[dict], friendly_id: str) -> str:
    if quality is not None and "sifflet.severity" in quality_props:
        return _require_severity(quality_props["sifflet.severity"])
    if quality is not None and quality.severity:
        mapped = _ODCS_SEVERITY.get(str(quality.severity).lower())
        if mapped:
            return mapped
        logger.warning(
            f"Rule {friendly_id}: severity '{quality.severity}' is not info, warning, or error; using Moderate."
        )
        return _DEFAULT_SEVERITY
    for props in inherited:
        if "sifflet.severity" in props:
            return _require_severity(props["sifflet.severity"])
    return _DEFAULT_SEVERITY


def map_schedule(
    quality: DataQuality | None, quality_props: dict, inherited: list[dict], friendly_id: str
) -> str | None:
    """Return the cron expression to write, or None when the schedule key is omitted."""
    if "sifflet.schedule" in quality_props:
        return _validate_cron(quality_props["sifflet.schedule"], friendly_id)
    if quality is not None and quality.schedule:
        scheduler = quality.scheduler or "cron"
        if str(scheduler).lower() != "cron":
            logger.warning(
                f"Rule {friendly_id}: scheduler '{scheduler}' is not supported by Sifflet; "
                "monitor exported without schedule."
            )
            return None
        return _validate_cron(quality.schedule, friendly_id)
    for props in inherited:
        if "sifflet.schedule" in props:
            return _validate_cron(props["sifflet.schedule"], friendly_id)
    return None


def prepare_query(query: str, table_name: str, field_name: str | None, server: Server) -> str:
    """Replace ODCS placeholders with identifiers quoted for the server's dialect.

    Quotes written around a placeholder are dropped. ``${object}`` becomes the fully
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

    return _PLACEHOLDER.sub(replace, query)


def select_server(data_contract: OpenDataContractStandard, server_name: str | None) -> Server:
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
        contract_id = data_contract.id or "unknown"
        version = data_contract.version or "unknown"
        selected_server = select_server(data_contract, server)
        contract_props = _read_properties(data_contract, "contract")
        server_props = _read_properties(selected_server, "server")
        drafts = []
        for schema in select_schemas(data_contract, schema_name or "all"):
            drafts.extend(_schema_drafts(schema, selected_server, contract_props, server_props, contract_id, version))
        drafts = _resolve_collisions(drafts)
        explicit = {_identity(draft.document["parameters"]) for draft in drafts if not draft.implicit}
        monitors = [
            draft.document
            for draft in drafts
            if not draft.implicit or _identity(draft.document["parameters"]) not in explicit
        ]
        header = (
            f"# Generated by datacontract-cli `export sifflet` from {contract_id} v{version}.\n"
            "# Do not edit by hand – edit the data contract and re-export.\n"
        )
        if not monitors:
            return header
        return header + yaml.dump_all(monitors, sort_keys=False, allow_unicode=True, default_flow_style=False)


def _schema_drafts(schema, server, contract_props, server_props, contract_id, version) -> list[_Draft]:
    schema_props = _read_properties(schema, "schema")
    schema_chain = [schema_props, contract_props]
    datasource_chain = [server_props, contract_props]
    datasource = {"name": _lookup(datasource_chain, "sifflet.datasource") or server.server}
    datasource_id = _lookup(datasource_chain, "sifflet.datasourceId")
    if datasource_id:
        datasource["id"] = datasource_id
    dataset = {"name": _physical_name(schema)}
    if "sifflet.datasetId" in schema_props:
        dataset["id"] = schema_props["sifflet.datasetId"]
    dataset["datasource"] = datasource
    properties = [prop for prop in schema.properties or [] if prop.name]
    for prop in properties:
        if prop.properties or prop.items:
            logger.warning(
                f"Nested properties are not exported to Sifflet: schema[{schema.name}].properties[{prop.name}]"
            )
    drafts = []
    primary_keys = [prop for prop in properties if prop.primaryKey]
    if _lookup(schema_chain, "sifflet.enabled", True) and _lookup(schema_chain, "sifflet.implicitMonitors", True):
        drafts.append(
            _implicit_draft(
                schema,
                None,
                "schema_change",
                "schema change",
                {"kind": "SchemaChange"},
                schema_chain,
                dataset,
                contract_id,
                version,
            )
        )
        if len(primary_keys) >= 2:
            drafts.append(
                _implicit_draft(
                    schema,
                    None,
                    "primary_key",
                    "primary key",
                    {"kind": "FieldDuplicates", "field": [_physical_name(prop) for prop in primary_keys]},
                    schema_chain,
                    dataset,
                    contract_id,
                    version,
                )
            )
    for index, quality in enumerate(schema.quality or []):
        draft = _quality_draft(quality, schema, None, index, schema_chain, dataset, server, contract_id, version)
        if draft:
            drafts.append(draft)
    single_primary_key = primary_keys[0] if len(primary_keys) == 1 else None
    for prop in properties:
        prop_props = _read_properties(prop, "property")
        prop_chain = [prop_props, *schema_chain]
        if _lookup(prop_chain, "sifflet.enabled", True) and _lookup(prop_chain, "sifflet.implicitMonitors", True):
            drafts.extend(
                _property_implicits(schema, prop, single_primary_key, prop_chain, dataset, contract_id, version)
            )
        for index, quality in enumerate(prop.quality or []):
            draft = _quality_draft(quality, schema, prop, index, prop_chain, dataset, server, contract_id, version)
            if draft:
                drafts.append(draft)
    return drafts


def _property_implicits(schema, prop, single_primary_key, chain, dataset, contract_id, version) -> list[_Draft]:
    drafts = []
    field = _physical_name(prop)
    if prop.required:
        drafts.append(
            _implicit_draft(
                schema,
                prop,
                "required",
                "not null",
                {"kind": "FieldNulls", "field": field, "valueMode": "Count"},
                chain,
                dataset,
                contract_id,
                version,
            )
        )
    if prop.unique or prop is single_primary_key:
        drafts.append(
            _implicit_draft(
                schema,
                prop,
                "unique",
                "unique",
                {"kind": "FieldDuplicates", "field": field},
                chain,
                dataset,
                contract_id,
                version,
            )
        )
    options = prop.logicalTypeOptions or {}
    if not isinstance(options, dict):
        options = {}
    format_name = options.get("format")
    if format_name:
        normalized = str(format_name).lower()
        if normalized in _FORMATS:
            format_kind, label = _FORMATS[normalized]
            drafts.append(
                _implicit_draft(
                    schema,
                    prop,
                    f"format_{normalized}",
                    label,
                    {"kind": "FieldFormat", "field": field, "format": {"kind": format_kind}},
                    chain,
                    dataset,
                    contract_id,
                    version,
                )
            )
        else:
            logger.warning(
                f"Rule at schema[{schema.name}].properties[{prop.name}]: format '{format_name}' is not supported "
                "for an implicit Sifflet monitor; skipped."
            )
    if options.get("pattern"):
        drafts.append(
            _implicit_draft(
                schema,
                prop,
                "format_regex",
                "matches pattern",
                {"kind": "FieldFormat", "field": field, "format": {"kind": "Regex", "regex": options["pattern"]}},
                chain,
                dataset,
                contract_id,
                version,
            )
        )
    return drafts


def _implicit_draft(schema, prop, suffix, label, parameters, chain, dataset, contract_id, version) -> _Draft:
    friendly_id = _join_id(schema.name, prop.name if prop else None, suffix)
    return _Draft(
        friendly_id=friendly_id,
        override=False,
        implicit=True,
        document=_document(
            friendly_id=friendly_id,
            name=_monitor_name(contract_id, schema.name, prop.name if prop else None, label),
            description=_description(None, contract_id, version),
            schedule=map_schedule(None, {}, chain, friendly_id),
            severity=map_severity(None, {}, chain, friendly_id),
            message=_lookup(chain, "sifflet.incidentMessage"),
            create_on_failure=_lookup(chain, "sifflet.createOnFailure"),
            notifications=_lookup(chain, "sifflet.notifications"),
            tags=_lookup(chain, "sifflet.tags"),
            dataset=dataset,
            parameters=parameters,
        ),
    )


def _quality_draft(quality, schema, prop, index, parent_chain, dataset, server, contract_id, version):
    column = prop.name if prop else None
    if column:
        path = f"schema[{schema.name}].properties[{column}].quality[{index}]"
    else:
        path = f"schema[{schema.name}].quality[{index}]"
    quality_props = _read_properties(quality, "quality")
    chain = [quality_props, *parent_chain]
    if not _lookup(chain, "sifflet.enabled", True):
        return None
    kind = _quality_kind(quality)
    if kind == "custom":
        logger.debug(f"Rule at {path}: type custom is not exported.")
        return None
    if kind == "text":
        logger.debug(f"Rule at {path}: type text is not exported.")
        return None
    if kind == "sql" and not ("sifflet.friendlyId" in quality_props or quality.id or quality.name):
        logger.warning(
            f"Rule at {path}: 'id' or 'name' is required for SQL quality rules in the Sifflet export; rule skipped."
        )
        return None
    if kind not in ("sql", "library"):
        logger.warning(f"Rule at {path}: type '{quality.type}' is not supported; rule skipped.")
        return None

    metric = _metric_name(quality)
    if kind == "library" and not metric:
        logger.warning(f"Rule at {path}: library rule has no metric; rule skipped.")
        return None
    override = True
    if "sifflet.friendlyId" in quality_props:
        friendly_id = str(quality_props["sifflet.friendlyId"])
    elif quality.id:
        friendly_id = str(quality.id)
    elif quality.name:
        friendly_id = snake(quality.name)
    else:
        override = False
        parts = [schema.name, column, "library", metric]
        for operator, token in _OPERATORS.items():
            value = getattr(quality, operator)
            if value is not None:
                parts.append(token)
                parts.extend(_num(bound) for bound in (value if operator == "mustBeBetween" else [value]))
        friendly_id = _join_id(*parts)

    inherited = chain[1:]
    try:
        if kind == "sql":
            field = _physical_name(prop) if prop is not None else None
            parameters = {
                "kind": "CustomMetrics",
                "sql": prepare_query(quality.query or "", dataset["name"], field, server),
            }
        else:
            parameters = _library_parameters(quality, prop, friendly_id)
        _attach_threshold(parameters, quality, quality_props, friendly_id, kind == "sql")
    except SkipRule as error:
        logger.warning(f"Rule {friendly_id}: {error.reason}; rule skipped.")
        return None
    extra_parameters = quality_props.get("sifflet.parameters")
    if isinstance(extra_parameters, dict):
        extra_parameters = dict(extra_parameters)
        if "kind" in extra_parameters:
            logger.warning(f"Rule {friendly_id}: sifflet.parameters cannot change kind; kind ignored.")
            del extra_parameters["kind"]
        parameters = _deep_merge(parameters, extra_parameters)

    label = quality_props.get("sifflet.name")
    if label is None:
        label = _label(quality, metric)
        name = _monitor_name(contract_id, schema.name, column, label)
    else:
        name = str(label)
    return _Draft(
        friendly_id=friendly_id,
        override=override,
        implicit=False,
        document=_document(
            friendly_id=friendly_id,
            name=name,
            description=_description(quality, contract_id, version),
            schedule=map_schedule(quality, quality_props, inherited, friendly_id),
            severity=map_severity(quality, quality_props, inherited, friendly_id),
            message=_lookup(chain, "sifflet.incidentMessage") or quality.description or None,
            create_on_failure=_lookup(chain, "sifflet.createOnFailure"),
            notifications=_lookup(chain, "sifflet.notifications"),
            tags=_lookup(chain, "sifflet.tags"),
            dataset=dataset,
            parameters=parameters,
        ),
    )


def _library_parameters(quality, prop, friendly_id) -> dict:
    metric = _metric_name(quality)
    arguments = quality.arguments if isinstance(quality.arguments, dict) else {}
    level = "property" if prop is not None else "table"
    field = _physical_name(prop) if prop is not None else None
    if level == "property" and metric == "nullValues":
        return _field_nulls(quality, field)
    if level == "property" and metric == "missingValues":
        ignored = [value for value in arguments.get("missingValues") or [] if value is not None]
        if ignored:
            listed = ", ".join(repr(value) for value in ignored)
            logger.warning(f"Rule {friendly_id}: only NULL values are monitored; {listed} ignored.")
        return _field_nulls(quality, field)
    if level == "property" and metric == "invalidValues":
        has_values = arguments.get("validValues") is not None
        has_pattern = bool(arguments.get("pattern"))
        if has_values and has_pattern:
            raise SkipRule("invalidValues has both validValues and pattern")
        if has_values:
            if not isinstance(arguments["validValues"], list):
                raise SkipRule("invalidValues validValues must be a list")
            return {"kind": "FieldInList", "field": field, "values": list(arguments["validValues"])}
        if has_pattern:
            return {"kind": "FieldFormat", "field": field, "format": {"kind": "Regex", "regex": arguments["pattern"]}}
        raise SkipRule("invalidValues needs validValues or pattern")
    if level == "property" and metric == "duplicateValues":
        if arguments.get("properties"):
            logger.warning(
                f"Rule {friendly_id}: arguments.properties is ignored for a property-level duplicateValues rule."
            )
        return {"kind": "FieldDuplicates", "field": field}
    if level == "table" and metric == "duplicateValues":
        columns = arguments.get("properties")
        if isinstance(columns, list) and columns:
            return {"kind": "FieldDuplicates", "field": list(columns)}
        return {"kind": "RowDuplicates"}
    if level == "table" and metric == "rowCount":
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
    if "sifflet.threshold" in quality_props:
        parameters["threshold"] = quality_props["sifflet.threshold"]
        return
    derived = map_threshold(quality)
    kind = parameters["kind"]
    if derived is None and kind in _ZERO_DEFAULT_KINDS:
        return
    if derived is None and is_sql:
        logger.warning(
            f"Rule {friendly_id}: no operator given; monitor exported without threshold, "
            "Sifflet's default dynamic threshold applies."
        )
        return
    if derived is None:
        raise SkipRule("no operator given")
    exact_zero = {"kind": "Static", "min": 0, "isMinInclusive": True, "max": 0, "isMaxInclusive": True}
    if kind in _ZERO_DEFAULT_KINDS and derived == exact_zero:
        return
    parameters["threshold"] = derived


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
    # A fresh copy per monitor: yaml.dump writes shared dicts as anchors and aliases.
    document["datasets"] = [{**dataset, "datasource": dict(dataset["datasource"])}]
    document["parameters"] = parameters
    return document


def _label(quality, metric) -> str:
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


def _monitor_name(contract_id, table, column, label) -> str:
    subject = f"{table}.{column}" if column else table
    return f"[{contract_id}] {subject} – {label}"


def _join_id(*parts) -> str:
    tokens = []
    for part in parts:
        if part is None or part == "":
            continue
        is_token = isinstance(part, str) and part.replace("_", "").isalnum() and part == part.lower()
        token = part if is_token else snake(part)
        if token:
            tokens.append(token)
    return "_".join(tokens)


def _quality_kind(quality) -> str:
    if quality.type == "custom":
        return "custom"
    if quality.type == "text":
        return "text"
    if quality.type == "sql":
        return "sql"
    if quality.type == "library" or _metric_name(quality):
        return "library"
    if quality.query:
        return "sql"
    return "other"


def _metric_name(quality) -> str | None:
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


def _require_severity(value) -> str:
    if value not in _SEVERITIES:
        raise RuntimeError(f"sifflet.severity '{value}' is not one of Low, Moderate, High, Critical.")
    return value


def _validate_cron(value, friendly_id) -> str | None:
    text = str(value).strip()
    if not text:
        return None
    if not (text.startswith("@") or len(text.split()) == 5):
        logger.warning(
            f"Rule {friendly_id}: schedule '{text}' is not a 5-field cron or a @ macro; value passed through."
        )
    return text


def _read_properties(element, level: str) -> dict:
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
        value = entry.value
        if key in _STRUCTURED:
            value = _structured(key, value)
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


def _structured(key, value):
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


def _lookup(chain: list[dict], key: str, default=None):
    for props in chain:
        if key in props:
            return props[key]
    return default


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _resolve_collisions(drafts: list[_Draft]) -> list[_Draft]:
    groups: dict[str, list[_Draft]] = {}
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


def _identity(parameters: dict) -> tuple:
    field = parameters.get("field")
    field_key = tuple(field) if isinstance(field, list) else field
    fmt = parameters.get("format") if isinstance(parameters.get("format"), dict) else {}
    values = parameters.get("values")
    values_key = tuple(values) if isinstance(values, list) else values
    return (parameters.get("kind"), field_key, fmt.get("kind"), fmt.get("regex"), values_key)


def _num(value) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
