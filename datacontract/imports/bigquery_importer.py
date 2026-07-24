import json
import logging
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import List, Optional, Tuple

from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
)
from datacontract.model.exceptions import DataContractException


class BigQueryImporter(Importer):
    def import_source(self, source: str, import_args: dict) -> OpenDataContractStandard:
        if source is not None:
            return import_bigquery_from_json(source)
        else:
            return import_bigquery_from_api(
                import_args.get("bigquery_table"),
                import_args.get("bigquery_project"),
                import_args.get("bigquery_dataset"),
            )


def import_bigquery_from_json(source: str) -> OpenDataContractStandard:
    try:
        with open(source, "r") as file:
            bigquery_schema = json.loads(file.read())
    except json.JSONDecodeError as e:
        raise DataContractException(
            type="schema",
            name="Parse bigquery schema",
            reason=f"Failed to parse bigquery schema from {source}",
            engine="datacontract",
            original_exception=e,
        )
    return convert_bigquery_schema(bigquery_schema)


def import_bigquery_from_api(
    bigquery_tables: List[str],
    bigquery_project: str,
    bigquery_dataset: str,
) -> OpenDataContractStandard:
    try:
        from google.cloud import bigquery
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="bigquery extra missing",
            reason="Install the extra datacontract-cli[bigquery] to use bigquery",
            engine="datacontract",
            original_exception=e,
        )

    client = bigquery.Client(project=bigquery_project)

    if bigquery_tables is None:
        bigquery_tables = fetch_table_names(client, bigquery_dataset)

    odcs = create_odcs()
    odcs.schema_ = []

    for table in bigquery_tables:
        try:
            api_table = client.get_table("{}.{}.{}".format(bigquery_project, bigquery_dataset, table))

        except ValueError as e:
            raise DataContractException(
                type="schema",
                result="failed",
                name="Invalid table name for bigquery API",
                reason=f"Tablename {table} is invalid for the bigquery API",
                original_exception=e,
                engine="datacontract",
            )

        if api_table is None:
            raise DataContractException(
                type="request",
                result="failed",
                name="Query bigtable Schema from API",
                reason=f"Table {table} not found on bigtable schema Project {bigquery_project}, dataset {bigquery_dataset}.",
                engine="datacontract",
            )

        schema_obj = convert_bigquery_table_to_schema(api_table.to_api_repr())
        odcs.schema_.append(schema_obj)

    return odcs


def fetch_table_names(client, dataset: str) -> List[str]:
    table_names = []
    api_tables = client.list_tables(dataset)
    for api_table in api_tables:
        table_names.append(api_table.table_id)

    return table_names


def convert_bigquery_schema(bigquery_schema: dict) -> OpenDataContractStandard:
    """Convert a BigQuery schema to ODCS format."""
    odcs = create_odcs()
    odcs.schema_ = [convert_bigquery_table_to_schema(bigquery_schema)]
    return odcs


def convert_bigquery_table_to_schema(bigquery_schema: dict):
    """Convert a BigQuery table definition to an ODCS SchemaObject."""
    properties = import_table_fields(bigquery_schema.get("schema", {}).get("fields", []))

    table_id = bigquery_schema.get("tableReference", {}).get("tableId", "unknown")
    description = bigquery_schema.get("description")
    title = bigquery_schema.get("friendlyName")
    table_type = map_bigquery_type(bigquery_schema.get("type", "TABLE"))

    schema_obj = create_schema_object(
        name=table_id,
        physical_type=table_type,
        description=description,
        properties=properties,
    )

    if title:
        schema_obj.businessName = title

    return schema_obj


def import_table_fields(table_fields) -> List[SchemaProperty]:
    """Import BigQuery table fields as ODCS SchemaProperties."""
    properties = []

    for field in table_fields:
        field_name = field.get("name")
        required = field.get("mode") == "REQUIRED"
        description = field.get("description")
        field_type = field.get("type")
        repeated = field.get("mode") == "REPEATED"

        if field_type == "RECORD":
            nested_properties = import_table_fields(field.get("fields", []))
            if repeated:
                items_prop = create_property(
                    name="items",
                    logical_type="object",
                    physical_type="RECORD",
                    properties=nested_properties,
                )
                prop = create_property(
                    name=field_name,
                    logical_type="array",
                    description=description,
                    required=None,
                    items=items_prop,
                )
            else:
                prop = create_property(
                    name=field_name,
                    logical_type="object",
                    physical_type="RECORD",
                    description=description,
                    required=required if required else None,
                    properties=nested_properties,
                )
        elif field_type == "STRUCT":
            nested_properties = import_table_fields(field.get("fields", []))
            if repeated:
                items_prop = create_property(
                    name="items",
                    logical_type="object",
                    physical_type="STRUCT",
                    properties=nested_properties,
                )
                prop = create_property(
                    name=field_name,
                    logical_type="array",
                    description=description,
                    required=None,
                    items=items_prop,
                )
            else:
                prop = create_property(
                    name=field_name,
                    logical_type="object",
                    physical_type="STRUCT",
                    description=description,
                    required=required if required else None,
                    properties=nested_properties,
                )
        elif field_type == "RANGE":
            # Range of date/datetime/timestamp - multiple values, map to array
            items_prop = create_property(
                name="items",
                logical_type=map_type_from_bigquery(field.get("rangeElementType", {}).get("type", "STRING")),
                physical_type=field.get("rangeElementType", {}).get("type", "STRING"),
            )
            prop = create_property(
                name=field_name,
                logical_type="array",
                physical_type="RANGE",
                description=description,
                required=required if required else None,
                items=items_prop,
            )
        else:
            logical_type = map_type_from_bigquery(field_type)
            max_length = None
            precision = None
            scale = None

            if field_type == "STRING" and field.get("maxLength") is not None:
                max_length = int(field.get("maxLength"))

            if field_type in ("NUMERIC", "BIGNUMERIC"):
                if field.get("precision") is not None:
                    precision = int(field.get("precision"))
                if field.get("scale") is not None:
                    scale = int(field.get("scale"))

            if repeated:
                items_prop = create_property(
                    name="items",
                    logical_type=logical_type,
                    physical_type=field_type,
                    max_length=max_length,
                    precision=precision,
                    scale=scale,
                )
                prop = create_property(
                    name=field_name,
                    logical_type="array",
                    description=description,
                    required=None,
                    items=items_prop,
                )
            else:
                prop = create_property(
                    name=field_name,
                    logical_type=logical_type,
                    physical_type=field_type,
                    description=description,
                    required=required if required else None,
                    max_length=max_length,
                    precision=precision,
                    scale=scale,
                )
        properties.append(prop)

    return properties


@dataclass
class ParsedBigQueryType:
    """A parsed BigQuery type expression.

    Represents both scalar types (``STRING``, ``INT64``, ``NUMERIC(10, 2)``)
    and compound types (``ARRAY<...>``, ``STRUCT<field1 T1, field2 T2>``).
    """

    base_type: str
    """The BigQuery type name in upper case, e.g. ``STRING``, ``ARRAY``, ``STRUCT``."""

    params: List[str] = dc_field(default_factory=list)
    """Positional parameters, e.g. ``["10", "2"]`` for ``NUMERIC(10, 2)``."""

    element_type: Optional["ParsedBigQueryType"] = None
    """For ``ARRAY<T>`` and ``RANGE<T>``: the element type ``T``."""

    fields: List[Tuple[Optional[str], "ParsedBigQueryType"]] = dc_field(default_factory=list)
    """For ``STRUCT<name1 T1, name2 T2>``: an ordered list of ``(name, type)`` pairs.

    Field names may be ``None`` for anonymous struct fields.
    """


def parse_bigquery_type(type_str: str) -> ParsedBigQueryType:
    """Parse a BigQuery type string into a :class:`ParsedBigQueryType`.

    Understands the compound grammar used by ``INFORMATION_SCHEMA.COLUMNS`` and
    dbt models: ``STRING``, ``STRING(100)``, ``NUMERIC(10, 2)``,
    ``ARRAY<INT64>``, ``STRUCT<name STRING, age INT64>``, and arbitrary
    nesting such as ``ARRAY<STRUCT<items ARRAY<STRING>>>``. Empty struct
    bodies (``STRUCT<>``) are permitted and produce an empty ``fields`` list.
    """
    if type_str is None or not str(type_str).strip():
        raise DataContractException(
            type="schema",
            result="failed",
            name="Parse bigquery type",
            reason="BigQuery type is empty.",
            engine="datacontract",
        )

    parsed, consumed = _parse_bigquery_type(type_str.strip(), 0)
    remainder = type_str.strip()[consumed:].strip()
    if remainder:
        raise DataContractException(
            type="schema",
            result="failed",
            name="Parse bigquery type",
            reason=f"Unexpected trailing characters {remainder!r} in bigquery type {type_str!r}.",
            engine="datacontract",
        )
    return parsed


def _parse_bigquery_type(text: str, pos: int) -> Tuple[ParsedBigQueryType, int]:
    """Parse a single BigQuery type starting at ``pos``. Returns (parsed, end_pos)."""
    pos = _skip_ws(text, pos)
    start = pos
    while pos < len(text) and (text[pos].isalnum() or text[pos] == "_"):
        pos += 1
    if pos == start:
        raise DataContractException(
            type="schema",
            result="failed",
            name="Parse bigquery type",
            reason=f"Expected a type name at position {start} in {text!r}.",
            engine="datacontract",
        )
    base_type = text[start:pos].upper()
    pos = _skip_ws(text, pos)

    parsed = ParsedBigQueryType(base_type=base_type)

    if pos < len(text) and text[pos] == "<":
        pos = _skip_ws(text, pos + 1)
        if base_type in ("STRUCT", "RECORD"):
            parsed.fields, pos = _parse_struct_fields(text, pos)
        else:
            # ARRAY<T>, RANGE<T>, and any other angle-bracket container.
            if pos < len(text) and text[pos] == ">":
                # Empty parameter list, e.g. ARRAY<>.
                pos += 1
            else:
                element, pos = _parse_bigquery_type(text, pos)
                parsed.element_type = element
                pos = _skip_ws(text, pos)
                if pos >= len(text) or text[pos] != ">":
                    raise DataContractException(
                        type="schema",
                        result="failed",
                        name="Parse bigquery type",
                        reason=f"Missing '>' after {base_type} element type in {text!r}.",
                        engine="datacontract",
                    )
                pos += 1
    elif pos < len(text) and text[pos] == "(":
        parsed.params, pos = _parse_paren_params(text, pos)

    return parsed, pos


def _parse_struct_fields(text: str, pos: int) -> Tuple[List[Tuple[Optional[str], ParsedBigQueryType]], int]:
    """Parse the body of a ``STRUCT<...>`` starting after the opening ``<``.

    Returns the ordered list of ``(field_name, field_type)`` pairs and the
    position just after the closing ``>``. An empty body is allowed.
    """
    fields: List[Tuple[Optional[str], ParsedBigQueryType]] = []
    pos = _skip_ws(text, pos)
    if pos < len(text) and text[pos] == ">":
        return fields, pos + 1

    while True:
        pos = _skip_ws(text, pos)
        # A struct field is written as either ``<name> <type>`` or just ``<type>``.
        # Peek to decide: if we see IDENT followed by whitespace and another
        # IDENT-like token (a type name), the first IDENT is the field name.
        name_start = pos
        while pos < len(text) and (text[pos].isalnum() or text[pos] == "_"):
            pos += 1
        first_token = text[name_start:pos]
        after_first = _skip_ws(text, pos)

        field_name: Optional[str] = None
        if after_first < len(text) and (text[after_first].isalnum() or text[after_first] == "_"):
            # Two identifiers in a row — first is the name, second starts the type.
            field_name = first_token
            pos = after_first
            field_type, pos = _parse_bigquery_type(text, pos)
        else:
            # Only one identifier — treat it as an anonymous type name.
            # Re-parse from the beginning of the identifier so parameters
            # like ``STRING(100)`` are picked up.
            pos = name_start
            field_type, pos = _parse_bigquery_type(text, pos)

        fields.append((field_name, field_type))
        pos = _skip_ws(text, pos)
        if pos < len(text) and text[pos] == ",":
            pos += 1
            continue
        if pos < len(text) and text[pos] == ">":
            return fields, pos + 1
        raise DataContractException(
            type="schema",
            result="failed",
            name="Parse bigquery type",
            reason=f"Expected ',' or '>' in STRUCT body at position {pos} in {text!r}.",
            engine="datacontract",
        )


def _parse_paren_params(text: str, pos: int) -> Tuple[List[str], int]:
    """Parse ``(a, b, c)`` starting at the opening ``(`` and return ``([a, b, c], end)``."""
    assert text[pos] == "("
    end = text.find(")", pos + 1)
    if end == -1:
        raise DataContractException(
            type="schema",
            result="failed",
            name="Parse bigquery type",
            reason=f"Missing ')' in bigquery type {text!r}.",
            engine="datacontract",
        )
    raw = text[pos + 1 : end]
    params = [p.strip() for p in raw.split(",")] if raw.strip() else []
    return params, end + 1


def _skip_ws(text: str, pos: int) -> int:
    while pos < len(text) and text[pos].isspace():
        pos += 1
    return pos


def build_schema_property_from_bigquery_type(
    name: str,
    bigquery_type_str: str,
    description: Optional[str] = None,
    required: Optional[bool] = None,
) -> SchemaProperty:
    """Build a :class:`SchemaProperty` for ``name`` from a BigQuery type string.

    Populates nested ``items`` (for ``ARRAY<...>``/``RANGE<...>``) and
    ``properties`` (for ``STRUCT<...>``) recursively, and lifts ``STRING(n)``
    length as well as ``NUMERIC(p, s)``/``BIGNUMERIC(p, s)`` precision/scale
    onto the resulting property.
    """
    parsed = parse_bigquery_type(bigquery_type_str)
    return _build_property_from_parsed(
        parsed,
        name=name,
        description=description,
        required=required,
    )


def _build_property_from_parsed(
    parsed: ParsedBigQueryType,
    name: str,
    description: Optional[str] = None,
    required: Optional[bool] = None,
) -> SchemaProperty:
    """Recursively convert a :class:`ParsedBigQueryType` into a :class:`SchemaProperty`."""
    base = parsed.base_type
    logical_type = _map_base_type_to_logical(base)
    physical_type = base

    max_length = _extract_max_length(parsed)
    precision, scale = _extract_precision_scale(parsed)

    if base in ("STRUCT", "RECORD"):
        nested_properties = [
            _build_property_from_parsed(
                field_type,
                name=field_name if field_name is not None else f"field_{index + 1}",
            )
            for index, (field_name, field_type) in enumerate(parsed.fields)
        ] or None
        return create_property(
            name=name,
            logical_type=logical_type,
            physical_type=physical_type,
            description=description,
            required=required,
            properties=nested_properties,
        )

    if base in ("ARRAY", "RANGE"):
        items_prop: Optional[SchemaProperty] = None
        if parsed.element_type is not None:
            items_prop = _build_property_from_parsed(parsed.element_type, name="items")
        return create_property(
            name=name,
            logical_type=logical_type,
            physical_type=physical_type if base != "ARRAY" else None,
            description=description,
            required=required,
            items=items_prop,
        )

    return create_property(
        name=name,
        logical_type=logical_type,
        physical_type=physical_type,
        description=description,
        required=required,
        max_length=max_length,
        precision=precision,
        scale=scale,
    )


def _extract_max_length(parsed: ParsedBigQueryType) -> Optional[int]:
    """Return the ``STRING(n)``/``BYTES(n)`` length parameter, if any."""
    if parsed.base_type in ("STRING", "BYTES") and len(parsed.params) == 1:
        try:
            return int(parsed.params[0])
        except ValueError:
            return None
    return None


def _extract_precision_scale(parsed: ParsedBigQueryType) -> Tuple[Optional[int], Optional[int]]:
    """Return ``(precision, scale)`` for ``NUMERIC``/``BIGNUMERIC``, if provided."""
    if parsed.base_type not in ("NUMERIC", "BIGNUMERIC"):
        return None, None
    precision: Optional[int] = None
    scale: Optional[int] = None
    if len(parsed.params) >= 1:
        try:
            precision = int(parsed.params[0])
        except ValueError:
            precision = None
    if len(parsed.params) >= 2:
        try:
            scale = int(parsed.params[1])
        except ValueError:
            scale = None
    return precision, scale


def map_type_from_bigquery(bigquery_type_str: str) -> str:
    """Map a BigQuery type string to an ODCS logical type.

    Supports both simple types (``STRING``, ``INT64``) and compound types
    produced by ``INFORMATION_SCHEMA``/dbt such as ``STRING(100)``,
    ``NUMERIC(10, 2)``, ``ARRAY<INT64>``, ``STRUCT<name STRING>``, and
    ``ARRAY<STRUCT<name STRING, age INT64>>``. Only the outer type drives the
    return value; use :func:`build_schema_property_from_bigquery_type` to also
    materialize nested ``items``/``properties`` on a :class:`SchemaProperty`.
    """
    if bigquery_type_str is None:
        raise DataContractException(
            type="schema",
            result="failed",
            name="Map bigquery type to data contract type",
            reason="BigQuery type is None.",
            engine="datacontract",
        )

    parsed = parse_bigquery_type(bigquery_type_str)
    return _map_base_type_to_logical(parsed.base_type)


def _map_base_type_to_logical(base_type: str) -> str:
    """Map a bare BigQuery base type (no parameters, no children) to an ODCS logical type."""
    type_mapping = {
        "STRING": "string",
        "BYTES": "array",
        "INTEGER": "integer",
        "INT64": "integer",  # for dbt-bigquery
        "FLOAT": "number",
        "FLOAT64": "number",  # for dbt-bigquery
        "BOOLEAN": "boolean",
        "BOOL": "boolean",
        "TIMESTAMP": "timestamp",
        "DATE": "date",
        "TIME": "time",
        "DATETIME": "timestamp",
        "NUMERIC": "number",
        "BIGNUMERIC": "number",
        "GEOGRAPHY": "object",
        "JSON": "object",
        "ARRAY": "array",
        "STRUCT": "object",
        "RECORD": "object",
        "RANGE": "array",
        "INTERVAL": "string",
    }

    if base_type in type_mapping:
        return type_mapping[base_type]

    raise DataContractException(
        type="schema",
        result="failed",
        name="Map bigquery type to data contract type",
        reason=f"Unsupported type {base_type} in bigquery json definition.",
        engine="datacontract",
    )


def map_bigquery_type(bigquery_type: str) -> str:
    """Map BigQuery table type to ODCS physical type."""
    if bigquery_type in ("TABLE", "EXTERNAL", "SNAPSHOT"):
        return "table"
    elif bigquery_type in ("VIEW", "MATERIALIZED_VIEW"):
        return "view"
    else:
        logger = logging.getLogger(__name__)
        logger.info(
            f"Can't properly map bigquery table type '{bigquery_type}' to datacontracts model types. Mapping it to table."
        )
        return "table"
