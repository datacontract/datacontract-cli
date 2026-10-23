from __future__ import annotations

import json
import logging
import re
import zipfile
from collections import OrderedDict
from pathlib import Path
from typing import Any

import sqlglot
from open_data_contract_standard.model import (
    CustomProperty,
    OpenDataContractStandard,
    Relationship,
    SchemaObject,
    SchemaProperty,
)
from sqlglot import exp
from sqlglot.optimizer.scope import build_scope

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
    create_server,
    report_unmapped_types,
)
from datacontract.model.exceptions import DataContractException

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Power BI data type → (ODCS logical type, optional format)
# ---------------------------------------------------------------------------
_PBI_TYPE_TO_ODCS: dict[str, tuple[str, str | None]] = {
    "string": ("string", None),
    "int64": ("integer", None),
    "double": ("number", None),
    "decimal": ("number", None),
    "boolean": ("boolean", None),
    "datetime": ("timestamp", None),
    "date": ("date", None),
    "time": ("time", None),
    "binary": ("string", "binary"),
    "duration": ("string", None),
    "unknown": ("string", None),
    "variant": ("object", None),
}


def _map_pbi_type(data_type: str | None) -> tuple[str | None, str | None]:
    """Map a Power BI data type string to ``(logicalType, format)``; the logicalType is None if unmapped."""
    if data_type is None:
        return (None, None)
    return _PBI_TYPE_TO_ODCS.get(data_type.lower(), (None, None))


def _normalize(name: str) -> str:
    """Turn a Power BI name into a valid ODCS identifier token.

    Examples:
        "Sales"        → "Sales"
        "Account Owner" → "Account_Owner"
        "Sales MoM %"   → "Sales_MoM_percent"
    """
    normalized = re.sub(r"[^A-Za-z0-9_]", "_", name.replace("%", "percent"))
    if normalized[:1].isdigit():
        normalized = "_" + normalized
    return normalized


# ---------------------------------------------------------------------------
# Importer class
# ---------------------------------------------------------------------------


class PowerBiImporter(Importer):
    def import_source(self, source: str, import_args: dict) -> OpenDataContractStandard:
        if source is None:
            raise DataContractException(
                type="source",
                name="powerbi import source",
                reason=(
                    "Source file path is required for Power BI import. "
                    "Provide a path to a .pbit file, a .bim file, or a model.bim JSON file."
                ),
                engine="datacontract-cli",
            )
        return import_powerbi_from_file(source_path=source)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def import_powerbi_from_file(source_path: str) -> OpenDataContractStandard:
    """Import a Power BI semantic model from a ``.pbit``, ``.bim``, or ``.json`` file."""
    path = Path(source_path)
    if not path.exists():
        raise DataContractException(
            type="import",
            name="powerbi import",
            reason=f"File not found: {source_path}",
            engine="datacontract-cli",
        )

    suffix = path.suffix.lower()
    if suffix == ".pbit":
        bim = _load_bim_from_pbit(path)
    elif suffix in (".bim", ".json"):
        bim = _load_bim_from_json(path)
    else:
        raise DataContractException(
            type="import",
            name="powerbi import",
            reason=(f"Unsupported file extension '{suffix}'. Supported formats: .pbit, .bim, .json"),
            engine="datacontract-cli",
        )

    return _build_odcs(bim, model_name=path.stem)


# ---------------------------------------------------------------------------
# BIM loaders
# ---------------------------------------------------------------------------


def _load_bim_from_pbit(pbit_path: Path) -> dict[str, Any]:
    """Extract and parse the ``DataModelSchema`` JSON from a .pbit ZIP archive.

    Power BI Desktop embeds the tabular model as a UTF-16 LE JSON file called
    ``DataModelSchema`` inside the .pbit ZIP archive.  This entry has been
    present since mid-2021; older files may not include it.
    """
    _ENTRY_NAME = "DataModelSchema"
    try:
        with zipfile.ZipFile(pbit_path, "r") as zf:
            if _ENTRY_NAME not in zf.namelist():
                raise DataContractException(
                    type="import",
                    name="powerbi import",
                    reason=(
                        f"'DataModelSchema' was not found inside '{pbit_path.name}'. "
                        "This entry is present in Power BI Desktop files saved since mid-2021. "
                        "Try re-saving the file from an up-to-date Power BI Desktop, or export "
                        "the model as a .bim file using pbi-tools (https://pbi.tools) and "
                        "import that instead."
                    ),
                    engine="datacontract-cli",
                )
            raw = zf.read(_ENTRY_NAME)
    except zipfile.BadZipFile as exc:
        raise DataContractException(
            type="import",
            name="powerbi import",
            reason=f"'{pbit_path.name}' is not a valid .pbit / ZIP file: {exc}",
            engine="datacontract-cli",
            original_exception=exc,
        )

    # DataModelSchema is always UTF-16 LE, optionally with a BOM
    text = raw.decode("utf-16-le").lstrip("\ufeff")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise DataContractException(
            type="import",
            name="powerbi import",
            reason=f"Failed to parse DataModelSchema JSON: {exc}",
            engine="datacontract-cli",
            original_exception=exc,
        )


def _load_bim_from_json(bim_path: Path) -> dict[str, Any]:
    """Load a ``model.bim`` / ``.json`` file as BIM JSON (UTF-8 with optional BOM)."""
    try:
        with open(bim_path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise DataContractException(
            type="import",
            name="powerbi import",
            reason=f"Failed to read BIM file '{bim_path}': {exc}",
            engine="datacontract-cli",
            original_exception=exc,
        )


# ---------------------------------------------------------------------------
# ODCS builder
# ---------------------------------------------------------------------------


def _build_odcs(bim: dict[str, Any], model_name: str) -> OpenDataContractStandard:
    # Some BIM files wrap everything under a top-level "model" key; others don't.
    model = bim.get("model", bim)

    odcs = create_odcs(
        id=model_name.lower().replace(" ", "-"),
        name=model_name,
    )

    odcs.servers = [
        create_server(
            name="powerbi",
            server_type="custom",
            path=model_name,
        )
    ]

    tables = model.get("tables", [])
    bim_relationships = model.get("relationships", [])

    schema_objects: list[SchemaObject] = []
    # original BIM table name → SchemaObject (for relationship wiring)
    table_name_to_obj: dict[str, SchemaObject] = {}

    try:
        lineage = column_lineage(model)
    except Exception as exc:  # lineage is best effort and must never break the import
        logger.warning("Could not derive column lineage from Power Query: %s", exc)
        lineage = {}

    for table in tables:
        schema_obj = _map_table(table, lineage)
        if schema_obj is not None:
            t_name = table.get("name", "")
            schema_objects.append(schema_obj)
            table_name_to_obj[t_name] = schema_obj

    _apply_bim_relationships(bim_relationships, table_name_to_obj)

    if not schema_objects:
        logger.warning("Power BI import produced an empty contract: No tables were found in the semantic model.")

    schema_objects.sort(key=lambda s: s.name.lower())
    odcs.schema_ = schema_objects
    report_unmapped_types(odcs, fallback="string")
    return odcs


# ---------------------------------------------------------------------------
# Table → SchemaObject
# ---------------------------------------------------------------------------


def _map_table(
    table: dict[str, Any], lineage: dict[tuple[str, str], tuple[str | None, list[str]]]
) -> SchemaObject | None:
    name = table.get("name", "")
    if not name:
        return None
    if name.startswith("LocalDateTable_"):
        return None
    if name.startswith("DateTableTemplate_"):
        return None

    description = table.get("description") or None
    is_hidden = table.get("isHidden", False)
    physical_type = _table_physical_type(table)
    tags = ["hidden"] if is_hidden else None

    properties: list[SchemaProperty] = []

    # Columns — skip internal rowNumber columns added by the engine
    for col in table.get("columns", []):
        if col.get("columnType") == "rowNumber":
            continue
        prop = _map_column(col)
        if prop:
            logic, sources = lineage.get((name, col.get("name", "")), (None, []))
            prop.transformLogic = prop.transformLogic or logic
            prop.transformSourceObjects = sources or None
            properties.append(prop)

    # Measures
    for measure in table.get("measures", []):
        prop = _map_measure(measure)
        if prop:
            properties.append(prop)

    # Hierarchies
    for hierarchy in table.get("hierarchies", []):
        prop = _map_hierarchy(hierarchy)
        if prop:
            properties.append(prop)

    schema_obj = create_schema_object(
        name=_normalize(name),
        physical_type=physical_type,
        description=description,
        business_name=name,
        tags=tags,
        properties=properties if properties else None,
    )

    return schema_obj


def _table_physical_type(table: dict[str, Any]) -> str:
    partitions = table.get("partitions", [])
    if not partitions:
        return "table"
    source_type = partitions[0].get("source", {}).get("type", "")
    return "calculated table" if source_type == "calculated" else "table"


# ---------------------------------------------------------------------------
# Column → SchemaProperty
# ---------------------------------------------------------------------------


def _map_column(col: dict[str, Any]) -> SchemaProperty | None:
    name = col.get("name", "")
    if not name:
        return None

    data_type = col.get("dataType", "string")
    column_type = col.get("columnType", "data")
    is_calculated = column_type == "calculated"

    logical_type, fmt = _map_pbi_type(data_type)
    physical_type = "calculated column" if is_calculated else data_type
    is_nullable = col.get("isNullable", True)
    description = col.get("description") or None

    custom_props: dict[str, Any] = {}

    if col.get("formatString"):
        custom_props["formatString"] = col["formatString"]
    if col.get("displayFolder"):
        custom_props["displayFolder"] = col["displayFolder"]
    if col.get("summarizeBy") and col["summarizeBy"] not in ("none", "default", None):
        custom_props["summarizeBy"] = col["summarizeBy"]
    if col.get("isHidden"):
        custom_props["isHidden"] = True

    expression = col.get("expression")
    if isinstance(expression, list):
        expression = "".join(expression)

    property = create_property(
        name=_normalize(name),
        logical_type=logical_type,
        physical_type=physical_type,
        description=description,
        required=True if not is_nullable else None,
        format=fmt,
        custom_properties=custom_props if custom_props else None,
    )

    property.businessName = name
    property.transformLogic = expression.strip() if expression else None

    return property


# ---------------------------------------------------------------------------
# Measure → SchemaProperty
# ---------------------------------------------------------------------------


def _map_measure(measure: dict[str, Any]) -> SchemaProperty | None:
    name = measure.get("name", "")
    if not name:
        return None

    description = measure.get("description") or None
    expression = measure.get("expression", "")
    # Power BI sometimes stores multi-line DAX as a list of strings
    if isinstance(expression, list):
        expression = "\n".join(expression)

    custom_props: dict[str, Any] = {}
    if measure.get("isHidden"):
        custom_props["isHidden"] = True
    if measure.get("displayFolder"):
        custom_props["displayFolder"] = measure["displayFolder"]

    logical_type = _infer_measure_type(measure.get("formatString", ""), expression)

    property = create_property(
        name=_normalize(name),
        logical_type=logical_type,
        physical_type="measure",
        description=description,
        custom_properties=custom_props if custom_props else None,
    )
    property.businessName = name
    property.transformLogic = expression.strip() if expression else None

    return property


def _infer_measure_type(format_string: str, expression: str) -> str:
    """Best-effort inference of a measure's return type from its format string."""
    if not format_string:
        return "number"
    fs = format_string.lower()
    if any(k in fs for k in ["yyyy", "mmm", "ddd", "hh:mm"]):
        return "timestamp"
    if "true" in fs or "false" in fs:
        return "boolean"
    # Numeric format patterns: digits, comma separators, currency, percentage
    if any(c in fs for c in ["#", "0", "%", "$", "€", "£"]):
        return "number"
    return "number"


# ---------------------------------------------------------------------------
# Hierarchy → SchemaProperty
# ---------------------------------------------------------------------------


def _map_hierarchy(hierarchy: dict[str, Any]) -> SchemaProperty | None:
    name = hierarchy.get("name", "")
    if not name:
        return None

    description = hierarchy.get("description") or None
    levels = sorted(hierarchy.get("levels", []), key=lambda lv: lv.get("ordinal", 0))

    level_props = []
    for lv in levels:
        if not lv.get("name"):
            continue
        level_prop = create_property(
            name=_normalize(lv.get("name")),
            logical_type="string",
            physical_type="hierarchy level",
            custom_properties={"columnRef": _normalize(lv["column"])} if lv.get("column") else None,
        )
        level_prop.businessName = lv.get("name")
        level_props.append(level_prop)

    hierarchy_prop = create_property(
        name=_normalize(name),
        logical_type="object",
        physical_type="hierarchy",
        description=description,
        properties=level_props if level_props else None,
    )
    hierarchy_prop.businessName = name
    return hierarchy_prop


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------


def _apply_bim_relationships(
    bim_relationships: list[dict[str, str]],
    table_name_to_obj: dict[str, SchemaObject],
) -> None:
    """Attach BIM relationships as ODCS Relationship objects on the 'from' SchemaObject.

    ``from`` and ``to`` are ``table.column`` references built from the normalized
    (identifier-safe) names, so each matches the ``name`` of its target.
    The relationship is placed on the *from* side (many side) of the join.
    """
    for rel in bim_relationships:
        from_table = rel.get("fromTable", "")
        from_col_name = rel.get("fromColumn", "")
        to_table = rel.get("toTable", "")
        to_col_name = rel.get("toColumn", "")

        from_obj = table_name_to_obj.get(from_table)
        to_obj = table_name_to_obj.get(to_table)
        if from_obj is None or to_obj is None:
            continue

        from_card = rel.get("fromCardinality", "many")
        to_card = rel.get("toCardinality", "one")
        is_active = rel.get("isActive", True)

        custom_props = [CustomProperty(property="cardinality", value=f"{from_card}-to-{to_card}")]
        if not is_active:
            custom_props.append(CustomProperty(property="active", value=False))

        odcs_rel = Relationship(
            type="foreignKey",
            **{"from": f"{_normalize(from_table)}.{_normalize(from_col_name)}"},
            to=f"{_normalize(to_table)}.{_normalize(to_col_name)}",
            customProperties=custom_props,
        )

        if from_obj.relationships is None:
            from_obj.relationships = []
        from_obj.relationships.append(odcs_rel)


# ───────────────────────── M (Power Query) : scanner ─────────────────────────


def strip_comments(s):
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == '"':
            j = i + 1
            while j < n:
                if s[j] == '"':
                    if j + 1 < n and s[j + 1] == '"':
                        j += 2
                        continue
                    break
                j += 1
            out.append(s[i : j + 1])
            i = j + 1
        elif s.startswith("//", i):
            j = s.find("\n", i)
            i = n if j < 0 else j
        elif s.startswith("/*", i):
            j = s.find("*/", i + 2)
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def scan(s):
    """Rend (i, char, depth, in_string) pour chaque caractère."""
    depth, i, n = 0, 0, len(s)
    while i < n:
        c = s[i]
        if c == '"':
            j = i + 1
            while j < n:
                if s[j] == '"':
                    if j + 1 < n and s[j + 1] == '"':
                        j += 2
                        continue
                    break
                j += 1
            for k in range(i, min(j + 1, n)):
                yield k, s[k], depth, True
            i = j + 1
            continue
        if c in "([{":
            yield i, c, depth, False
            depth += 1
        elif c in ")]}":
            depth -= 1
            yield i, c, depth, False
        else:
            yield i, c, depth, False
        i += 1


def split_top(s, sep=","):
    parts, last = [], 0
    for i, c, d, ins in scan(s):
        if c == sep and d == 0 and not ins:
            parts.append(s[last:i])
            last = i + 1
    parts.append(s[last:])
    return parts


def split_let(expr):
    """Retourne (steps[(name, expr)], result_expr) ou None si pas un let."""
    e = strip_comments(expr).strip()
    if not re.match(r"let\b", e):
        return None
    body = e[3:]
    in_pos = None
    for m in re.finditer(r"\bin\b", body):
        # profondeur 0 et hors chaîne
        pass
    depth_at = {i: (d, ins) for i, c, d, ins in scan(body)}
    for m in re.finditer(r"\bin\b", body):
        d, ins = depth_at.get(m.start(), (1, True))
        if d == 0 and not ins:
            in_pos = m.start()  # dernier "in" de profondeur 0
    if in_pos is None:
        return None
    steps = []
    for part in split_top(body[:in_pos]):
        m = re.match(r'\s*(#"(?:[^"]|"")*"|[A-Za-z_][\w.]*)\s*=\s*(.*)$', part, re.S)
        if m:
            steps.append((unq(m.group(1)), m.group(2).strip()))
    return steps, body[in_pos + 2 :].strip()


def unq(name):
    name = name.strip()
    if name.startswith('#"') and name.endswith('"'):
        return name[2:-1].replace('""', '"')
    return name


def decode_m_string(lit):
    s = lit[1:-1].replace('""', '"')

    def rep(m):
        out = []
        for tok in m.group(1).split(","):
            tok = tok.strip().lower()
            out.append(
                {"lf": "\n", "cr": "\r", "tab": "\t"}.get(tok)
                or (chr(int(tok, 16)) if re.fullmatch(r"[0-9a-f]{4}|[0-9a-f]{8}", tok) else "")
            )
        return "".join(out)

    return re.sub(r"#\(([^)]*)\)", rep, s)


STR_RE = r'"(?:[^"]|"")*"'


def eval_m_string(expr, steps, params, depth=0):
    """Évalue une expression M faite de littéraux, de & et d'identifiants -> (texte, résolu?)."""
    text, ok = [], True
    for part in split_top(expr.strip(), "&"):
        p = part.strip()
        while p.startswith("(") and p.endswith(")"):
            p = p[1:-1].strip()
        if re.fullmatch(STR_RE, p, re.S):
            text.append(decode_m_string(p))
        else:
            name = unq(p)
            if name in steps and depth < 5:
                t, o = eval_m_string(steps[name], steps, params, depth + 1)
                text.append(t)
                ok &= o
            elif name in params:
                text.append("${%s}" % name)
            else:
                text.append("${?%s}" % re.sub(r"\W+", "_", p)[:40])
                ok = False
    return "".join(text), ok


def call_args(expr, fn):
    """Arguments top-level du premier appel `fn(...)` dans expr."""
    i = expr.find(fn + "(")
    if i < 0:
        return None
    start = i + len(fn)
    sub = expr[start:]
    for k, c, d, ins in scan(sub):
        if c == ")" and d == 0 and not ins:
            return split_top(sub[1:k])
    return None


def str_list(txt):
    return [s[1:-1].replace('""', '"') for s in re.findall(STR_RE, txt)]


# ───────────────────────── SQL ─────────────────────────


def parse_sql(sql, params_used):
    """Retourne dict {projections, tables, ctes, error?}."""
    ph = {}

    def sub(m):
        key = "__p_%s__" % re.sub(r"\W", "_", m.group(1))
        ph[key] = m.group(0)
        return key

    clean = re.sub(r"\$\{(\??[^}]+)\}", sub, sql)
    res = {"projections": [], "tables": [], "ctes": [], "parseError": None}

    def restore(t):
        for k, v in ph.items():
            t = t.replace(k, v)
        return t

    try:
        ast = sqlglot.parse_one(clean, read="databricks")
    except Exception as e:
        res["parseError"] = str(e).split("\n")[0][:300]
        return res
    # CTE
    cte_names = {c.alias_or_name for c in ast.find_all(exp.CTE)}
    res["ctes"] = sorted(cte_names)

    # tables FROM/JOIN
    seen = OrderedDict()
    for t in ast.find_all(exp.Table):
        if not t.name or (t.name in cte_names and not t.db):
            continue
        if isinstance(t.this, exp.Func) if hasattr(exp, "Func") else False:
            continue
        par = t.parent
        role, joinkind = "FROM", None
        if isinstance(par, exp.Join):
            role = "JOIN"
            joinkind = (
                " ".join(x for x in [par.args.get("method"), par.args.get("side"), par.args.get("kind")] if x)
                or "INNER"
            )
        elif isinstance(par, exp.From):
            role = "FROM"
        else:
            role = "FROM"
        full = restore(".".join(p for p in [t.catalog, t.db, t.name] if p))
        key = (full, t.alias, role, joinkind)
        if key not in seen:
            seen[key] = {
                "table": full,
                "catalog": restore(t.catalog) or None,
                "schema": restore(t.db) or None,
                "name": restore(t.name),
                "alias": t.alias or None,
                "clause": role,
                "joinType": joinkind,
            }
    res["tables"] = list(seen.values())

    # projections (select le plus externe ; UNION -> branche gauche, tables de toutes les branches)
    top = ast
    while isinstance(top, exp.With) or (
        isinstance(top, exp.Subquery) and top.this is not None and not isinstance(top, exp.Select)
    ):
        top = top.this
    while isinstance(top, (exp.Union, exp.Except, exp.Intersect)):
        top = top.this
    if not isinstance(top, exp.Select):
        sel = ast.find(exp.Select)
        top = sel
    root = None
    try:
        root = build_scope(ast)
    except Exception:
        root = None
    scope_of = {}
    if root is not None:
        for sc in root.traverse():
            scope_of[id(sc.expression)] = sc

    def resolve(col, scope, depth=0):
        """colonne -> liste {table, column} feuilles."""
        if scope is None or depth > 8:
            return [{"table": None, "column": col.name}]
        qual = col.table
        srcs = scope.sources
        cands = []
        if qual and qual in srcs:
            cands = [(qual, srcs[qual])]
        elif not qual:
            cands = list(srcs.items())
        else:
            return [{"table": restore(qual), "column": col.name}]
        out = []
        multi = len(cands) > 1 and not qual
        for alias, src in cands:
            if isinstance(src, exp.Table):
                out.append(
                    {
                        "table": restore(".".join(p for p in [src.catalog, src.db, src.name] if p)),
                        "alias": alias,
                        "column": col.name,
                        **({"ambiguous": True} if multi else {}),
                    }
                )
            else:  # sous-scope (CTE, sous-requête)
                matched = False
                for pr in src.expression.selects:
                    if pr.alias_or_name.lower() == col.name.lower():
                        matched = True
                        inner = list(pr.find_all(exp.Column)) if not isinstance(pr, exp.Column) else [pr]
                        for ic in inner:
                            out.extend(resolve(ic, src, depth + 1))
                        if not inner:
                            pass
                if not matched and not multi:
                    # étoile dans la sous-requête
                    for pr in src.expression.selects:
                        if isinstance(pr, exp.Star) or (isinstance(pr, exp.Column) and isinstance(pr.this, exp.Star)):
                            out.extend(resolve(col, src, depth + 1))
        return out or [{"table": None, "column": col.name}]

    def uniq(lst):
        seen_, o = set(), []
        for x in lst:
            k = json.dumps(x, sort_keys=True)
            if k not in seen_:
                seen_.add(k)
                o.append(x)
        return o

    if top is not None:
        scope = scope_of.get(id(top))
        for pr in top.selects:
            is_star = isinstance(pr, exp.Star) or (isinstance(pr, exp.Column) and isinstance(pr.this, exp.Star))
            if is_star:
                q = pr.table if isinstance(pr, exp.Column) else None
                tgt = []
                if scope is not None:
                    for al, src in scope.sources.items():
                        if q and al != q:
                            continue
                        if isinstance(src, exp.Table):
                            tgt.append(restore(".".join(p for p in [src.catalog, src.db, src.name] if p)))
                res["projections"].append({"output": "*", "star": True, "qualifier": q or None, "starTables": tgt})
                continue
            expr = pr.this if isinstance(pr, exp.Alias) else pr
            cols = list(expr.find_all(exp.Column)) if not isinstance(expr, exp.Column) else [expr]
            srcs = []
            for c in cols:
                srcs.extend(resolve(c, scope))
            res["projections"].append(
                {
                    "output": restore(pr.alias_or_name)
                    or restore(expr.sql(dialect="databricks", normalize_functions="lower")),
                    "expression": restore(expr.sql(dialect="databricks")),
                    "isPassThrough": isinstance(expr, exp.Column),
                    "sourceColumns": uniq(srcs),
                }
            )
    return res


# ───────────────────────── lignée Power Query ─────────────────────────


class Lineage:
    def __init__(self, model):
        self.m = model
        self.params = {
            e["name"] for e in model.get("expressions", []) if "IsParameterQuery=true" in str(e.get("expression"))
        }
        self.exprs = {e["name"]: e for e in model.get("expressions", [])}
        self.tables = {t["name"]: t for t in model["tables"]}
        self.cache, self.stack = {}, set()
        self.sql_cache = {}

    @staticmethod
    def expr_text(e):
        x = e.get("source", {}).get("expression") if "source" in e else e.get("expression")
        return "\n".join(x) if isinstance(x, list) else (x or "")

    def query_state(self, name):
        if name in self.cache:
            return self.cache[name]
        if name in self.stack:
            return None
        self.stack.add(name)
        try:
            if name in self.tables:
                p = self.tables[name]["partitions"][0]
                text = self.expr_text(p)
                st = self.eval_m(text, name) if p["source"]["type"] == "m" else None
            elif name in self.exprs:
                st = self.eval_m(self.expr_text(self.exprs[name]), name)
            else:
                st = None
        finally:
            self.stack.discard(name)
        self.cache[name] = st
        return st

    def new_state(self):
        return {
            "cols": OrderedDict(),
            "enumerated": False,
            "queries": [],
            "physical": [],
            "upstream": [],
            "notes": [],
            "steps": [],
        }

    def eval_m(self, text, qname):
        sl = split_let(text)
        if not sl:
            st = self.new_state()
            st["notes"].append("expression M non-let")
            return st
        steps, result = sl
        sdict = dict(steps)
        states = {}
        prev = None
        for name, e in steps:
            st = self.apply_step(name, e, states, prev, sdict, qname)
            states[name] = st
            prev = name
        final = unq(result)
        st = states.get(final) or (states[prev] if prev else self.new_state())
        return st

    @staticmethod
    def clone(st):
        o = {
            k: (
                OrderedDict((c, dict(v, mSteps=list(v.get("mSteps", [])))) for c, v in st["cols"].items())
                if k == "cols"
                else (list(st[k]) if isinstance(st[k], list) else st[k])
            )
            for k in st
        }
        return o

    def input_state(self, e, states, prev):
        m = re.match(r'[\w.]+\(\s*(#"(?:[^"]|"")*"|[A-Za-z_]\w*)', e)
        if m:
            n = unq(m.group(1))
            if n in states:
                return states[n]
        return states.get(prev)

    def apply_step(self, name, e, states, prev, sdict, qname):
        # ─ sources
        if "Value.NativeQuery(" in e:
            args = call_args(e, "Value.NativeQuery")
            st = self.new_state()
            if args and len(args) >= 2:
                sql, ok = eval_m_string(args[1], sdict, self.params)
                key = sql
                if key not in self.sql_cache:
                    self.sql_cache[key] = parse_sql(sql, self.params)
                p = self.sql_cache[key]
                q = {"step": name, "sqlResolved": ok, "sqlLength": len(sql), **p}
                st["queries"].append(q)
                st["physical"] = [dict(t, via="sql") for t in p["tables"]]
                st["enumerated"] = not any(x.get("star") for x in p["projections"])
                st["hasStar"] = any(x.get("star") for x in p["projections"])
                for pr in p["projections"]:
                    if pr.get("star"):
                        st.setdefault("starTables", []).extend(pr["starTables"])
                        continue
                    st["cols"][pr["output"]] = {
                        "origin": {
                            "kind": "sql_projection",
                            "sqlStep": name,
                            "sqlOutput": pr["output"],
                            "sqlExpression": pr["expression"],
                            "isPassThrough": pr["isPassThrough"],
                            "sourceColumns": pr["sourceColumns"],
                        },
                        "mSteps": [],
                    }
                if p["parseError"]:
                    st["notes"].append("SQL non analysable: " + p["parseError"])
            return st
        m = re.match(
            r"(Databricks\.Catalogs|Sql\.Database|Sql\.Databases|CommonDataService\.Database|Excel\.Workbook|"
            r"Csv\.Document|Web\.Contents|SharePoint\.\w+|AzureStorage\.\w+)\(",
            e,
        )
        if m:
            st = self.new_state()
            fn = m.group(1)
            st["source"] = {"connector": fn}
            if fn == "Excel.Workbook":
                u = re.search(r"Web\.Contents\(\s*(" + STR_RE + ")", e)
                st["source"]["url"] = decode_m_string(u.group(1)) if u else None
            elif fn == "Sql.Database":
                a = call_args(e, fn)
                st["source"].update(
                    server=a[0].strip().strip('"') if a else None,
                    database=a[1].strip().strip('"') if a and len(a) > 1 else None,
                )
            elif fn == "Databricks.Catalogs":
                a = call_args(e, fn)
                st["source"].update(host=a[0].strip() if a else None)
                c = re.search(r"Catalog\s*=\s*([^,\]]+)", e)
                st["source"]["catalog"] = c.group(1).strip() if c else None
            st["notes"].append("source %s" % fn)
            return st
        # ─ navigation {[Name=..,Kind=..]}
        if re.search(r"\{\s*\[\s*(Name|Schema|Item)\s*=", e):
            base = self.input_state(e, states, prev)
            st = self.clone(base) if base else self.new_state()
            src = dict(st.get("source") or {})
            mk = re.search(r'Kind\s*=\s*"(\w+)"', e)
            mn = re.search(r"Name\s*=\s*(" + STR_RE + r"|[A-Za-z_]\w*)", e)
            if mn:
                v = decode_m_string(mn.group(1)) if mn.group(1).startswith('"') else "${%s}" % mn.group(1)
            else:
                v = None
            if mk and v is not None:
                src[mk.group(1).lower()] = v
            ms = re.search(r"Schema\s*=\s*(" + STR_RE + ")", e)
            mi = re.search(r"Item\s*=\s*(" + STR_RE + ")", e)
            if ms:
                src["schema"] = decode_m_string(ms.group(1))
            if mi:
                src["item"] = decode_m_string(mi.group(1))
            st["source"] = src
            if src.get("table") or src.get("item"):
                if src.get("connector") == "Excel.Workbook":
                    st["physical"] = [
                        {
                            "table": "%s#%s" % (src["url"], src.get("item")) if src.get("url") else src.get("item"),
                            "schema": None,
                            "name": src.get("item"),
                            "clause": "FROM",
                            "via": "excel",
                        }
                    ]
                else:
                    sch = src.get("schema")
                    tb = src.get("table") or src.get("item")
                    cat = src.get("database") if src.get("connector") == "Databricks.Catalogs" else None
                    full = ".".join(x for x in [cat, sch, tb] if x)
                    st["physical"] = [
                        {
                            "table": full,
                            "catalog": cat,
                            "schema": sch,
                            "name": tb,
                            "clause": "FROM",
                            "via": "navigation",
                            "connector": src.get("connector"),
                        }
                    ]
                st["enumerated"] = False
                st["navigated"] = True
            return st
        # ─ référence à une autre requête / table
        mref = re.fullmatch(r'(#"(?:[^"]|"")*"|[A-Za-z_]\w*)', e.strip())
        if mref:
            n = unq(mref.group(1))
            if n in states:
                return states[n]
            up = self.query_state(n) if (n in self.tables or n in self.exprs) else None
            if up is not None:
                st = self.clone(up)
                st["upstream"] = st["upstream"] + [n]
                for c in st["cols"].values():
                    c["mSteps"].append("ref:%s" % n)
                return st
            st = self.new_state()
            st["notes"].append("référence non résolue: %s" % n)
            return st
        # ─ transformations
        fn = re.match(r"(Table\.\w+|List\.\w+|#table|Json\.Document)", e)
        fn = fn.group(1) if fn else None
        base = self.input_state(e, states, prev)
        st = self.clone(base) if base else self.new_state()
        if fn:
            st["steps"] = st["steps"] + [{"step": name, "fn": fn}]
        if fn == "Table.RenameColumns":
            for a, b in re.findall(r"\{\s*(" + STR_RE + r")\s*,\s*(" + STR_RE + r")\s*\}", e):
                a, b = decode_m_string(a), decode_m_string(b)
                if a in st["cols"]:
                    cols = OrderedDict()
                    for k, v in st["cols"].items():
                        if k == a:
                            v = dict(v, mSteps=v["mSteps"] + ["rename %s -> %s" % (a, b)])
                            cols[b] = v
                        else:
                            cols[k] = v
                    st["cols"] = cols
                else:  # colonne physique non énumérée : pass-through renommé
                    st["cols"][b] = {
                        "origin": {"kind": "physical_passthrough", "physicalName": a},
                        "mSteps": ["rename %s -> %s" % (a, b)],
                    }
        elif fn == "Table.RemoveColumns":
            args = call_args(e, fn)
            for a in str_list(args[1]) if args and len(args) > 1 else []:
                st["cols"].pop(a, None)
                st.setdefault("removed", []).append(a)
        elif fn == "Table.SelectColumns":
            args = call_args(e, fn)
            keep = str_list(args[1]) if args and len(args) > 1 else []
            cols = OrderedDict()
            for k in keep:
                cols[k] = st["cols"].get(k) or {
                    "origin": {"kind": "physical_passthrough", "physicalName": k},
                    "mSteps": [],
                }
            st["cols"] = cols
            st["enumerated"] = True
            st["hasStar"] = False
        elif fn == "Table.AddColumn":
            args = call_args(e, fn)
            if args and len(args) >= 3:
                cn = decode_m_string(args[1].strip()) if args[1].strip().startswith('"') else unq(args[1])
                refs = sorted(set(re.findall(r"\[([^\[\]]+)\]", args[2])))
                st["cols"][cn] = {
                    "origin": {
                        "kind": "m_added_column",
                        "mExpression": re.sub(r"\s+", " ", args[2]).strip()[:500],
                        "referencedColumns": refs,
                    },
                    "mSteps": ["AddColumn"],
                }
        elif fn == "Table.DuplicateColumn":
            args = call_args(e, fn)
            if args and len(args) >= 3:
                a, b = decode_m_string(args[1].strip()), decode_m_string(args[2].strip())
                if a in st["cols"]:
                    st["cols"][b] = dict(st["cols"][a], mSteps=st["cols"][a]["mSteps"] + ["duplicate of %s" % a])
        elif fn == "Table.PromoteHeaders":
            st["enumerated"] = False
            st["notes"].append("en-têtes promus (colonnes déterminées par la source)")
        elif fn == "Table.Combine":
            args = call_args(e, fn)
            names = [unq(x) for x in re.findall(r'(#"(?:[^"]|"")*"|[A-Za-z_]\w*)', args[0])] if args else []
            parts = [states[n] for n in names if n in states]
            if parts:
                st = self.clone(parts[0])
                for p in parts[1:]:
                    st["queries"] += [q for q in p["queries"] if q not in st["queries"]]
                    st["physical"] += [t for t in p["physical"] if t not in st["physical"]]
                    for k, v in p["cols"].items():
                        if k not in st["cols"]:
                            st["cols"][k] = v
                        else:
                            st["cols"][k].setdefault("alsoFrom", []).append(v["origin"])
                st["notes"].append("Table.Combine (UNION) de: " + ", ".join(names))
        elif fn == "#table" or (fn == "Table.FromRows"):
            tt = re.search(r"type table\s*\[(.*?)\]", e, re.S)
            names = [unq(x) for x in re.findall(r'(#"(?:[^"]|"")*"|[A-Za-z_]\w*)\s*=', tt.group(1))] if tt else []
            hdr = re.match(r"#table\(\s*\{(.*?)\}", e, re.S)
            if not names and hdr:
                names = str_list(hdr.group(1))
            st = self.new_state()
            for n in names:
                st["cols"][n] = {"origin": {"kind": "inline_data"}, "mSteps": []}
            st["enumerated"] = True
        elif fn == "Table.FromList":
            args = call_args(e, fn)
            names = str_list(args[2]) if args and len(args) >= 3 else []
            st = self.new_state()
            for n in names:
                st["cols"][n] = {"origin": {"kind": "generated"}, "mSteps": []}
            st["enumerated"] = True
        elif fn in ("Table.NestedJoin", "Table.Join", "Table.ExpandTableColumn", "Table.ExpandRecordColumn"):
            args = call_args(e, fn) or []
            refs = [
                unq(a) for a in args if re.fullmatch(r'\s*(#"(?:[^"]|"")*"|[A-Za-z_]\w*)\s*', a) and unq(a) in states
            ]
            for r in refs[1:]:
                st["queries"] += [q for q in states[r]["queries"] if q not in st["queries"]]
                st["physical"] += [t for t in states[r]["physical"] if t not in st["physical"]]
            st["notes"].append("%s: colonnes jointes non tracées colonne à colonne" % fn)
        elif fn == "Table.TransformColumnNames":
            args = call_args(e, fn)
            f = args[1] if args and len(args) > 1 else ""
            mp = re.fullmatch(r"\s*each\s*(" + STR_RE + r")\s*&\s*_\s*", f)
            ms_ = re.fullmatch(r"\s*each\s*_\s*&\s*(" + STR_RE + r")\s*", f)
            if mp or ms_:
                lit = decode_m_string((mp or ms_).group(1))
                cols = OrderedDict()
                for k, v in st["cols"].items():
                    nk = lit + k if mp else k + lit
                    cols[nk] = dict(v, mSteps=v["mSteps"] + ["rename %s -> %s" % (k, nk)])
                st["cols"] = cols
            else:
                st["notes"].append("Table.TransformColumnNames non interprété: " + re.sub(r"\s+", " ", f)[:120])
        elif fn == "Table.TransformColumns":
            for a in re.findall(r"\{\s*(" + STR_RE + r")\s*,", e):
                a = decode_m_string(a)
                if a in st["cols"]:
                    st["cols"][a]["mSteps"].append("TransformColumns")
        elif fn == "Table.TransformColumnTypes":
            for a, t in re.findall(r"\{\s*(" + STR_RE + r")\s*,\s*([^{}]*?)\s*\}", e):
                a = decode_m_string(a)
                if a in st["cols"]:
                    st["cols"][a]["mType"] = t.strip()
        return st


def column_lineage(model: dict[str, Any]) -> dict[tuple[str, str], tuple[str | None, list[str]]]:
    """Return ``(table, column) -> (transformLogic, transformSourceObjects)`` for the data columns of a model.

    Lineage is best effort: tables or columns whose Power Query cannot be interpreted are left out.
    """
    lineage = Lineage(model)
    result: dict[tuple[str, str], tuple[str | None, list[str]]] = {}
    for table in model.get("tables", []):
        try:
            state = lineage.query_state(table["name"]) if table["partitions"][0]["source"]["type"] == "m" else None
        except (KeyError, IndexError, TypeError):
            state = None
        if state is None:
            continue
        physical = [p["table"] for p in state["physical"]]
        for col in table.get("columns", []):
            if col.get("type", col.get("columnType", "data")) in ("calculated", "calculatedTableColumn", "rowNumber"):
                continue
            source_column = col.get("sourceColumn", col["name"])
            hit = state["cols"].get(source_column) or next(
                (v for k, v in state["cols"].items() if k.lower() == source_column.lower()), None
            )
            logic, sources = None, []
            if hit:
                origin = hit["origin"]
                kind = origin.get("kind")
                if kind == "sql_projection":
                    logic = origin["sqlExpression"]
                    sources = [f"{s['table']}.{s['column']}" for s in origin["sourceColumns"] if s.get("table")]
                elif kind == "m_added_column":
                    logic = origin["mExpression"]
                    sources = origin["referencedColumns"]
                elif kind == "physical_passthrough":
                    sources = [f"{t}.{origin['physicalName']}" for t in physical]
                if not logic and hit["mSteps"]:
                    logic = "; ".join(hit["mSteps"])
            elif state.get("hasStar"):
                sources = [f"{t}.{source_column}" for t in sorted(set(state.get("starTables", [])))]
            elif not state["enumerated"] and physical:
                sources = [f"{t}.{source_column}" for t in physical]
            if logic or sources:
                result[(table["name"], col["name"])] = (logic, list(dict.fromkeys(sources)))
    return result
