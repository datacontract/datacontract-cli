from typing import Any

from open_data_contract_standard.model import SchemaProperty

_HANA_LOGICAL_TYPE_MAPPING = {
    "string": {"NVARCHAR", "VARCHAR", "NCLOB", "CLOB", "SHORTTEXT"},
    "text": {"NVARCHAR", "VARCHAR", "NCLOB", "CLOB", "SHORTTEXT"},
    "varchar": {"NVARCHAR", "VARCHAR", "NCLOB", "CLOB", "SHORTTEXT"},
    "integer": {"INTEGER", "INT", "BIGINT", "SMALLINT", "TINYINT"},
    "int": {"INTEGER", "INT", "BIGINT", "SMALLINT", "TINYINT"},
    "long": {"BIGINT"},
    "bigint": {"BIGINT"},
    "float": {"DOUBLE", "FLOAT", "REAL"},
    "double": {"DOUBLE", "FLOAT", "REAL"},
    "decimal": {"DECIMAL", "NUMERIC"},
    "numeric": {"DECIMAL", "NUMERIC"},
    "number": {"DECIMAL", "NUMERIC"},
    "boolean": {"BOOLEAN"},
    "date": {"DATE"},
    "time": {"TIME"},
    "timestamp": {"TIMESTAMP", "SECONDDATE"},
    "timestamp_tz": {"TIMESTAMP", "SECONDDATE"},
    "timestamp_ntz": {"SECONDDATE", "TIMESTAMP"},
    "binary": {"VARBINARY", "BLOB"},
    "bytes": {"VARBINARY", "BLOB"},
}

_HANA_TYPES = {hana_type for types in _HANA_LOGICAL_TYPE_MAPPING.values() for hana_type in types}
_HANA_TYPES.update({"SMALLINT", "TINYINT", "REAL", "NCLOB", "CLOB", "SHORTTEXT"})


def _get_base_type(type_name: str | None) -> str | None:
    if type_name is None:
        return None
    for separator in ("(", "<"):
        if separator in type_name:
            return type_name[: type_name.index(separator)].strip().upper()
    return type_name.strip().upper()


def _get_base_type_raw(type_name: str | None) -> str | None:
    if type_name is None:
        return None
    for separator in ("(", "<"):
        if separator in type_name:
            return type_name[: type_name.index(separator)].strip()
    return type_name.strip()


def types_match(hana_catalog_type: str, expected_type: str) -> bool:
    catalog_base_type = _get_base_type(hana_catalog_type)
    expected_base_type = _get_base_type(expected_type)
    expected_base_type_raw = _get_base_type_raw(expected_type)
    if catalog_base_type is None or expected_base_type is None:
        return False

    if expected_base_type in _HANA_TYPES and expected_base_type_raw != expected_base_type_raw.lower():
        return catalog_base_type == expected_base_type

    accepted_hana_types = _HANA_LOGICAL_TYPE_MAPPING.get(expected_base_type_raw.lower())
    if accepted_hana_types is None:
        return catalog_base_type == expected_base_type

    return catalog_base_type in accepted_hana_types


def _custom_properties_dict(field: Any) -> dict[str, Any]:
    if isinstance(field, SchemaProperty):
        if field.customProperties is None:
            return {}
        return {custom_property.property: custom_property.value for custom_property in field.customProperties}
    config = getattr(field, "config", None)
    if config is None:
        return {}
    return config


def _get_type(field: Any) -> str | None:
    if isinstance(field, SchemaProperty):
        return field.physicalType or field.logicalType
    return getattr(field, "type", None)


def _get_base_logical_type(field: Any) -> str | None:
    field_type = _get_type(field)
    if field_type is None:
        return None
    for separator in ("(", "<"):
        if separator in field_type:
            return field_type[: field_type.index(separator)].strip().lower()
    return field_type.lower()


def _get_params(field: Any) -> str | None:
    field_type = _get_type(field)
    if field_type and "(" in field_type and field_type.endswith(")"):
        return field_type[field_type.index("(") + 1 : -1]
    return None


def _get_precision(field: Any) -> int | None:
    if (
        isinstance(field, SchemaProperty)
        and field.logicalTypeOptions
        and field.logicalTypeOptions.get("precision") is not None
    ):
        return int(field.logicalTypeOptions.get("precision"))
    precision = getattr(field, "precision", None)
    if precision is not None:
        return int(precision)
    config_value = _custom_properties_dict(field).get("precision")
    if config_value:
        return int(config_value)
    params = _get_params(field)
    if params:
        try:
            return int(params.split(",")[0].strip())
        except ValueError:
            return None
    return None


def _get_scale(field: Any) -> int | None:
    if (
        isinstance(field, SchemaProperty)
        and field.logicalTypeOptions
        and field.logicalTypeOptions.get("scale") is not None
    ):
        return int(field.logicalTypeOptions.get("scale"))
    scale = getattr(field, "scale", None)
    if scale is not None:
        return int(scale)
    config_value = _custom_properties_dict(field).get("scale")
    if config_value:
        return int(config_value)
    params = _get_params(field)
    if params and "," in params:
        try:
            return int(params.split(",")[1].strip())
        except ValueError:
            return None
    return None


def _attach_params_if_present(base_type: str, field: Any, *, default: str | None = None) -> str:
    params = _get_params(field)
    if params:
        return f"{base_type}({params})"
    if default:
        return f"{base_type}({default})"
    return base_type


def _decimal_type(field: Any) -> str:
    precision = _get_precision(field)
    scale = _get_scale(field)
    if precision is not None and scale is not None:
        return f"DECIMAL({precision},{scale})"
    if precision is not None:
        return f"DECIMAL({precision})"
    return _attach_params_if_present("DECIMAL", field)


def convert_type_to_hana(field: Any) -> str | None:
    hana_type = _custom_properties_dict(field).get("hanaType")
    if hana_type:
        return hana_type

    base_type = _get_base_logical_type(field)
    if base_type is None:
        return None

    if base_type in ["string", "varchar", "text", "nvarchar"]:
        return _attach_params_if_present("NVARCHAR", field, default="5000")
    if base_type in ["integer", "int"]:
        return "INTEGER"
    if base_type in ["long", "bigint"]:
        return "BIGINT"
    if base_type == "smallint":
        return "SMALLINT"
    if base_type == "tinyint":
        return "TINYINT"
    if base_type == "float":
        return "REAL"
    if base_type == "double":
        return "DOUBLE"
    if base_type in ["decimal", "numeric", "number"]:
        return _decimal_type(field)
    if base_type == "boolean":
        return "BOOLEAN"
    if base_type == "date":
        return "DATE"
    if base_type == "time":
        return "TIME"
    if base_type in ["timestamp", "timestamp_tz"]:
        return "TIMESTAMP"
    if base_type == "timestamp_ntz":
        return "SECONDDATE"
    if base_type in ["binary", "bytes", "varbinary"]:
        return _attach_params_if_present("VARBINARY", field)
    if base_type in ["object", "record", "struct", "array"]:
        return "NCLOB"
    if _get_params(field):
        return _get_type(field)
    return None
