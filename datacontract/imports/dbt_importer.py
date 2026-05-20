import json
import re
from typing import Any, List, Optional, TypedDict

from open_data_contract_standard.model import CustomProperty, OpenDataContractStandard, SchemaProperty

from datacontract.imports.bigquery_importer import map_type_from_bigquery
from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
)

# Minimum supported dbt manifest schema version. v9 corresponds to dbt 1.5
# (May 2023), which is when column constraints and the current test_metadata
# shape stabilized. Older manifests should be regenerated.
MIN_MANIFEST_SCHEMA_VERSION = 9

_SCHEMA_VERSION_RE = re.compile(r"/v(\d+)\.json")


class DBTImportArgs(TypedDict, total=False):
    dbt_nodes: list[str]
    resource_types: list[str]


class DbtManifestImporter(Importer):
    def import_source(
        self,
        source: str,
        import_args: DBTImportArgs,
    ) -> OpenDataContractStandard:
        manifest = read_dbt_manifest(manifest_path=source)
        return import_dbt_manifest(
            manifest=manifest,
            dbt_nodes=import_args.get("dbt_model", []),
            resource_types=import_args.get("resource_types", ["model"]),
        )


def read_dbt_manifest(manifest_path: str) -> dict:
    """Read and validate a dbt manifest.json file."""
    with open(file=manifest_path, mode="r", encoding="utf-8") as f:
        manifest: dict = json.load(f)
    _check_schema_version(manifest)
    return manifest


def _check_schema_version(manifest: dict) -> None:
    schema_url = manifest.get("metadata", {}).get("dbt_schema_version", "")
    match = _SCHEMA_VERSION_RE.search(schema_url)
    if not match:
        return
    version = int(match.group(1))
    if version < MIN_MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            f"dbt manifest schema version v{version} is not supported. "
            f"Minimum supported version is v{MIN_MANIFEST_SCHEMA_VERSION} (dbt 1.5+). "
            f"Regenerate the manifest with a newer dbt version."
        )


def _get_test_metadata_column(test_node: dict) -> Optional[str]:
    """Pull the column name from a generic test node, preferring kwargs.column_name."""
    test_metadata = test_node.get("test_metadata") or {}
    kwargs = test_metadata.get("kwargs") or {}
    column = kwargs.get("column_name")
    if isinstance(column, str):
        return column
    return test_node.get("column_name")


def _is_generic_test(node: dict) -> bool:
    return node.get("resource_type") == "test" and node.get("test_metadata") is not None


def _iter_attached_tests(manifest: dict, model_unique_id: str):
    """Yield generic test nodes attached to the given model, skipping conditional (where) tests."""
    child_map = manifest.get("child_map") or {}
    nodes = manifest.get("nodes") or {}
    for child_id in child_map.get(model_unique_id, []):
        child = nodes.get(child_id)
        if not child or not _is_generic_test(child):
            continue
        if (child.get("config") or {}).get("where") is not None:
            continue
        yield child


def _infer_primary_keys(manifest: dict, node: dict) -> List[str]:
    """Reimplements dbt's ModelNode.infer_primary_key against a raw manifest dict.

    Order of precedence:
    1. Model-level primary_key constraint
    2. Column-level primary_key constraint
    3. Columns with both unique and not_null tests
    4. Columns with enabled unique tests
    5. Columns with disabled unique tests
    """
    if node.get("resource_type") != "model":
        return []

    for constraint in node.get("constraints") or []:
        if constraint.get("type") == "primary_key":
            cols = constraint.get("columns") or []
            if cols:
                return list(cols)

    for column_name, column in (node.get("columns") or {}).items():
        for constraint in column.get("constraints") or []:
            if constraint.get("type") == "primary_key":
                return [column_name]

    enabled_unique: set = set()
    disabled_unique: set = set()
    not_null: set = set()
    for test_node in _iter_attached_tests(manifest, node["unique_id"]):
        test_metadata = test_node.get("test_metadata") or {}
        test_name = test_metadata.get("name")
        kwargs = test_metadata.get("kwargs") or {}

        columns: List[str] = []
        column_name = kwargs.get("column_name")
        if isinstance(column_name, str):
            columns = [column_name]
        else:
            combo = kwargs.get("combination_of_columns")
            if isinstance(combo, list):
                columns = [c for c in combo if isinstance(c, str)]

        if not columns:
            continue

        if test_name in ("unique", "unique_combination_of_columns"):
            target = enabled_unique if (test_node.get("config") or {}).get("enabled", True) else disabled_unique
            target.update(columns)
        elif test_name == "not_null":
            not_null.update(columns)

    both = [c for c in not_null if c in enabled_unique or c in disabled_unique]
    if both:
        return both
    if enabled_unique:
        return list(enabled_unique)
    if disabled_unique:
        return list(disabled_unique)
    return []


def _get_references(manifest: dict, node: dict) -> dict[str, str]:
    """Find foreign-key references from `relationships` tests attached to this model."""
    references: dict[str, str] = {}
    nodes = manifest.get("nodes") or {}
    node_unique_id = node["unique_id"]
    for test_node in _iter_attached_tests(manifest, node_unique_id):
        test_metadata = test_node.get("test_metadata") or {}
        if test_metadata.get("name") != "relationships":
            continue
        if test_node.get("attached_node") != node_unique_id:
            continue
        depends_on_nodes = (test_node.get("depends_on") or {}).get("nodes") or []
        target_ids = [n for n in depends_on_nodes if n != node_unique_id]
        if not target_ids:
            continue
        target_node = nodes.get(target_ids[0])
        if not target_node:
            continue
        column_name = _get_test_metadata_column(test_node)
        target_field = (test_metadata.get("kwargs") or {}).get("field")
        if not column_name or not target_field:
            continue
        references[f"{node['name']}.{column_name}"] = f"{target_node['name']}.{target_field}"
    return references


_VERSION_SUFFIX_RE = re.compile(r"^v?(\d+)$")


def _matches_dbt_node_filter(node: dict, dbt_nodes: list[str]) -> bool:
    """Return True if *node* matches any entry in *dbt_nodes*.

    Entries may be plain model names (``my_model``) or versioned names using
    dbt's ``name.vN`` convention (``my_model.v1``).  A plain name matches any
    version of that model; a versioned name matches only the specific version.

    Model names that contain dots but whose final segment does not look like a
    version suffix (``v<digits>`` or bare ``<digits>``) are treated as plain
    names so that names such as ``schema.my_model`` are matched correctly.
    """
    for filter_name in dbt_nodes:
        if "." in filter_name:
            base, _, suffix = filter_name.rpartition(".")
            m = _VERSION_SUFFIX_RE.match(suffix)
            if m:
                # Versioned filter — match base name and version number only.
                if node.get("name") == base and str(node.get("version", "")) == m.group(1):
                    return True
                continue  # versioned filter didn't match; try next entry
            # Suffix doesn't look like a version — fall through to plain-name match.
        if node.get("name") == filter_name:
            return True
    return False


def import_dbt_manifest(
    manifest: dict,
    dbt_nodes: list[str],
    resource_types: list[str],
) -> OpenDataContractStandard:
    """Extracts all relevant information from the manifest into an ODCS data contract."""
    metadata = manifest.get("metadata") or {}
    odcs = create_odcs()
    odcs.name = metadata.get("project_name")

    odcs.customProperties = [CustomProperty(property="dbt_version", value=metadata.get("dbt_version"))]

    adapter_type = metadata.get("adapter_type")
    odcs.schema_ = []

    for node in (manifest.get("nodes") or {}).values():
        if node.get("resource_type") not in resource_types:
            continue

        if dbt_nodes and not _matches_dbt_node_filter(node, dbt_nodes):
            continue

        model_unique_id = node["unique_id"]
        primary_keys = _infer_primary_keys(manifest, node)
        references = _get_references(manifest, node)

        primary_key = None
        if len(primary_keys) == 1:
            primary_key = primary_keys[0]

        properties = create_fields(
            manifest,
            model_unique_id=model_unique_id,
            columns=node.get("columns") or {},
            primary_key_name=primary_key,
            references=references,
            adapter_type=adapter_type,
        )

        schema_obj = create_schema_object(
            name=node.get("name"),
            physical_type=(node.get("config") or {}).get("materialized"),
            description=node.get("description"),
            properties=properties,
        )

        if node.get("tags"):
            if schema_obj.customProperties is None:
                schema_obj.customProperties = []
            schema_obj.customProperties.append(CustomProperty(property="tags", value=",".join(node["tags"])))

        if len(primary_keys) > 1:
            if schema_obj.customProperties is None:
                schema_obj.customProperties = []
            schema_obj.customProperties.append(CustomProperty(property="primaryKey", value=",".join(primary_keys)))

        odcs.schema_.append(schema_obj)

    return odcs


def convert_data_type_by_adapter_type(data_type: str, adapter_type: str) -> str:
    if adapter_type == "bigquery":
        return map_type_from_bigquery(data_type)
    return map_dbt_type_to_odcs(data_type)


def map_dbt_type_to_odcs(data_type: str) -> str:
    """Map dbt data type to ODCS logical type."""
    if not data_type:
        return "string"

    data_type_lower = data_type.lower()

    type_mapping = {
        "string": "string",
        "varchar": "string",
        "text": "string",
        "char": "string",
        "int": "integer",
        "integer": "integer",
        "bigint": "integer",
        "smallint": "integer",
        "float": "number",
        "double": "number",
        "decimal": "number",
        "numeric": "number",
        "boolean": "boolean",
        "bool": "boolean",
        "date": "date",
        "datetime": "date",
        "timestamp": "date",
        "time": "string",
        "array": "array",
        "object": "object",
        "struct": "object",
        "json": "object",
    }

    for key, value in type_mapping.items():
        if data_type_lower.startswith(key):
            return value

    return "string"


def create_fields(
    manifest: dict,
    model_unique_id: str,
    columns: dict[str, Any],
    primary_key_name: str,
    references: dict[str, str],
    adapter_type: str,
) -> List[SchemaProperty]:
    """Create ODCS SchemaProperties from dbt columns."""
    return [
        create_field(manifest, model_unique_id, column, primary_key_name, references, adapter_type)
        for column in columns.values()
    ]


def get_column_tests(manifest: dict, model_unique_id: str, column_name: str) -> list[dict[str, str]]:
    nodes = manifest.get("nodes") or {}
    if model_unique_id not in nodes:
        raise ValueError(f"Model {model_unique_id} not found in manifest.")

    column_tests = []
    for test_node in _iter_attached_tests(manifest, model_unique_id):
        if test_node.get("column_name") != column_name:
            continue
        test_metadata = test_node.get("test_metadata") or {}
        column_tests.append(
            {
                "test_name": test_node.get("name"),
                "test_type": test_metadata.get("name"),
                "column": test_node.get("column_name"),
            }
        )
    return column_tests


def create_field(
    manifest: dict,
    model_unique_id: str,
    column: dict,
    primary_key_name: str,
    references: dict[str, str],
    adapter_type: str,
) -> SchemaProperty:
    """Create an ODCS SchemaProperty from a dbt column."""
    data_type = column.get("data_type")
    column_type = convert_data_type_by_adapter_type(data_type, adapter_type) if data_type else "string"

    all_tests = get_column_tests(manifest, model_unique_id, column.get("name"))

    constraints = column.get("constraints") or []

    required = False
    if any(c.get("type") == "not_null" for c in constraints):
        required = True
    if [test for test in all_tests if test["test_type"] == "not_null"]:
        required = True

    unique = False
    if any(c.get("type") == "unique" for c in constraints):
        unique = True
    if [test for test in all_tests if test["test_type"] == "unique"]:
        unique = True

    is_primary_key = column.get("name") == primary_key_name

    custom_props = {}
    model_node = (manifest.get("nodes") or {}).get(model_unique_id) or {}
    references_key = f"{model_node.get('name')}.{column.get('name')}"
    if references_key in references:
        custom_props["references"] = references[references_key]
    if column.get("tags"):
        custom_props["tags"] = ",".join(column["tags"])

    return create_property(
        name=column.get("name"),
        logical_type=column_type,
        physical_type=data_type,
        description=column.get("description"),
        required=required if required else None,
        unique=unique if unique else None,
        primary_key=is_primary_key if is_primary_key else None,
        primary_key_position=1 if is_primary_key else None,
        custom_properties=custom_props if custom_props else None,
    )
