import logging
import re
from typing import TYPE_CHECKING, Any, List, Optional

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty, Server

from datacontract.config import Config
from datacontract.engines.ibis.connections.aws_credentials import resolve_aws_credentials
from datacontract.export.duckdb_type_converter import convert_to_duckdb_csv_type, convert_to_duckdb_json_type
from datacontract.export.sql_type_converter import convert_to_duckdb
from datacontract.model.run import Run

if TYPE_CHECKING:
    import duckdb

logger = logging.getLogger(__name__)


def _import_duckdb():
    try:
        import duckdb

        return duckdb
    except ImportError:
        raise ImportError("duckdb is required for this server type. Install with: pip install datacontract-cli[duckdb]")


def get_duckdb_connection(
    data_contract: OpenDataContractStandard,
    server: Server,
    run: Run,
    duckdb_connection: "duckdb.DuckDBPyConnection | None" = None,
    schema_name: str = "all",
    config: Config | None = None,
    untrusted_contract: bool = False,
) -> "duckdb.DuckDBPyConnection":
    duckdb = _import_duckdb()
    config = Config.resolve(config)
    own_connection = duckdb_connection is None
    if own_connection:
        con = duckdb.connect(database=":memory:")
    else:
        con = duckdb_connection

    path: str = ""
    if server.type == "local":
        path = server.path
    if server.type == "s3":
        path = server.location
        setup_s3_connection(con, server, config)
    if server.type == "gcs":
        path = server.location
        setup_gcs_connection(con, server, config)
    if server.type == "azure":
        path = server.location
        setup_azure_connection(con, server, config)

    if server.format == "delta":
        # Updating an extension reaches the network and the extension directory,
        # both of which the sandbox below takes away -- so do it first, and once
        # for the whole connection rather than once per model.
        con.sql("update extensions;")  # Make sure we have the latest delta extension
    if server.format == "xml":
        try:
            con.install_extension("webbed", repository="community")
            con.load_extension("webbed")
        except Exception as e:
            raise RuntimeError("Failed to install the 'webbed' DuckDB community extension to read XML files.") from e

    model_paths = _model_paths(data_contract, path, schema_name)
    if untrusted_contract and own_connection:
        # After the extensions are loaded and the secrets created -- both need
        # access the sandbox takes away -- and before any contract-supplied SQL
        # can run. Not applied to a connection the caller handed us: that one is
        # theirs to configure.
        restrict_to_paths(con, model_paths)

    if data_contract.schema_:
        for schema_obj in data_contract.schema_:
            model_name = schema_obj.name
            if schema_name != "all" and model_name != schema_name:
                continue
            model_path = _model_path(path, model_name)
            run.log_info(f"Creating table {model_name} for {model_path}")

            if server.format == "json":
                encoding = _duckdb_encoding(server)
                if encoding and encoding != "utf-8":
                    run.log_warn(
                        f"Server '{server.server}' declares encoding '{server.encoding}', but JSON files are read as UTF-8."
                    )
                json_format = "auto"
                if server.delimiter == "new_line":
                    json_format = "newline_delimited"
                elif server.delimiter == "array":
                    json_format = "array"
                columns = to_json_types(schema_obj)
                if columns is None:
                    con.sql(f"""
                            CREATE VIEW "{model_name}" AS SELECT * FROM read_json_auto('{model_path}', format='{json_format}', hive_partitioning=1);
                            """)
                else:
                    con.sql(
                        # A value of the wrong type reads as NULL, so the other checks on its column still run;
                        # the JSON Schema check reports the value itself
                        f"""CREATE VIEW "{model_name}" AS SELECT * FROM read_json_auto('{model_path}', format='{json_format}', columns={columns}, hive_partitioning=1, ignore_errors=true);"""
                    )
                    add_nested_views(con, model_name, schema_obj.properties)
                # Raw view without the columns= projection to check for absent columns (check_property_is_present)
                con.sql(
                    f"""CREATE VIEW "{model_name}__raw__" AS SELECT * FROM read_json_auto('{model_path}', format='{json_format}', hive_partitioning=1);"""
                )
            elif server.format == "parquet":
                create_view_with_schema_union(con, schema_obj, model_path, "read_parquet", to_parquet_types)
            elif server.format == "csv":
                create_view_with_schema_union(
                    con, schema_obj, model_path, "read_csv", to_csv_types, read_options=_csv_encoding_options(server)
                )
            elif server.format == "delta":
                con.sql(f"""CREATE VIEW "{model_name}" AS SELECT * FROM delta_scan('{model_path}');""")
            elif server.format == "xml":
                create_xml_views(con, schema_obj, model_path)
            table_info = con.sql(f"PRAGMA table_info({_quote(model_name)});").fetchall()
            if table_info:
                run.log_info(f"DuckDB Table Info: {table_info}")
    return con


def _model_path(path: str, model_name: str) -> str:
    """The data location of one model: the server path with `{model}` filled in."""
    return path.format(model=model_name) if "{model}" in path else path


def _model_paths(data_contract: OpenDataContractStandard, path: str, schema_name: str) -> list[str]:
    """Every location this connection is going to read, one per model under test."""
    if not path or not data_contract.schema_:
        return []
    return [
        _model_path(path, schema_obj.name)
        for schema_obj in data_contract.schema_
        if schema_name == "all" or schema_obj.name == schema_name
    ]


# duckdb globs against the filesystem, so a location holding one of these has to be
# allowed as a directory prefix rather than as an exact file.
_GLOB_CHARACTERS = ("*", "?", "[")


def restrict_to_paths(con, paths: list[str]) -> None:
    """Confine the connection to `paths` and nothing else.

    A data contract carries SQL (`quality.type: sql`) that runs on this
    connection, and for a file server type that connection is duckdb -- which
    reads and writes the local filesystem. So the contract's own data locations
    are the only ones it may touch: `read_text('/etc/passwd')` and `COPY ... TO`
    alike are then refused by duckdb itself.

    `enable_external_access = false` is one-way -- duckdb refuses to re-enable it,
    and refuses to widen `allowed_paths`/`allowed_directories` once it is off --
    so the restriction holds without `lock_configuration`, which would also stop
    ibis from setting the session timezone.

    Must run after the extensions are loaded (installing one needs access this
    takes away) and before any contract-supplied SQL.
    """
    directories = sorted({_glob_root(p) for p in paths if _is_glob(p)})
    files = sorted({p for p in paths if not _is_glob(p)})
    if directories:
        con.sql(f"SET allowed_directories = {_sql_list(directories)}")
    if files:
        con.sql(f"SET allowed_paths = {_sql_list(files)}")
    con.sql("SET enable_external_access = false")


def _is_glob(path: str) -> bool:
    return any(character in path for character in _GLOB_CHARACTERS) or path.endswith("/")


def _glob_root(path: str) -> str:
    """The fixed prefix of a glob, which is the directory duckdb has to be allowed into."""
    cut = min((path.find(c) for c in _GLOB_CHARACTERS if c in path), default=len(path))
    root = path[:cut].rstrip("/")
    return root or "/"


def _sql_list(values: list[str]) -> str:
    return "[" + ", ".join(f"'{_sql_literal(value)}'" for value in values) + "]"


# ODCS `encoding` values (IANA names) DuckDB's CSV reader understands
_DUCKDB_ENCODINGS = {
    "utf-8": "utf-8",
    "utf8": "utf-8",
    "utf-16": "utf-16",
    "utf16": "utf-16",
    "iso-8859-1": "latin-1",
    "iso8859-1": "latin-1",
    "latin-1": "latin-1",
    "latin1": "latin-1",
}


def _duckdb_encoding(server: Server) -> str | None:
    """The DuckDB spelling of the server's declared payload encoding, or ``None`` if not declared."""
    declared = getattr(server, "encoding", None)
    if not declared:
        return None
    return _DUCKDB_ENCODINGS.get(declared.strip().lower(), declared.strip().lower())


def _csv_encoding_options(server: Server) -> str:
    """Extra ``read_csv`` arguments for the server's encoding (ODCS v3.2.0); empty for UTF-8."""
    encoding = _duckdb_encoding(server)
    if not encoding or encoding == "utf-8":
        return ""
    return f", encoding='{encoding}'"


def create_view_with_schema_union(
    con, schema_obj: SchemaObject, model_path: str, read_function: str, type_converter, read_options: str = ""
):
    """Create a view by unioning empty schema table with data files using union_by_name"""
    converted_types = type_converter(schema_obj)
    model_name = schema_obj.name

    # Raw view to check for absent columns (check_property_is_present)
    con.sql(
        f"""CREATE VIEW "{model_name}__raw__" AS
            SELECT * FROM {read_function}('{model_path}', union_by_name=true, hive_partitioning=1{read_options});"""
    )

    if converted_types:
        # Create empty table with contract schema
        columns_def = [f'"{col_name}" {col_type}' for col_name, col_type in converted_types.items()]
        create_empty_table = f"""CREATE TABLE "{model_name}" ({", ".join(columns_def)});"""
        con.sql(create_empty_table)

        # Read columns existing in both current data contract and data
        intersecting_columns = con.sql(f"""SELECT column_name
            FROM (DESCRIBE SELECT * FROM {read_function}('{model_path}', union_by_name=true, hive_partitioning=1{read_options}))
            INTERSECT SELECT column_name
            FROM information_schema.columns
            WHERE table_name = '{model_name}'""").fetchall()

        # Insert data into table by name, but only columns existing in contract and data
        if intersecting_columns:
            selected_columns = ", ".join(f'"{column[0]}"' for column in intersecting_columns)
            insert_data_sql = f"""INSERT INTO "{model_name}" BY NAME
                (SELECT {selected_columns} FROM {read_function}('{model_path}', union_by_name=true, hive_partitioning=1{read_options}));"""
            con.sql(insert_data_sql)
    else:
        # Fallback
        con.sql(
            f"""CREATE VIEW "{model_name}" AS SELECT * FROM {read_function}('{model_path}', union_by_name=true, hive_partitioning=1{read_options});"""
        )


# read_xml refuses files above 16 MB by default, with a SAX parsing error; a file is read whole either way
XML_MAXIMUM_FILE_SIZE = 2**40


def create_xml_views(con, schema_obj: SchemaObject, model_path: str):
    """Views over the records of XML documents: every element named like the schema's physical name is one.

    The checks address a schema by its physical name, quality SQL often by its name, so both name the view.
    """
    record_element = schema_obj.physicalName or schema_obj.name
    read_xml = (
        f"read_xml('{_sql_literal(model_path)}', record_element='{_sql_literal(record_element)}', "
        f"union_by_name=true, maximum_file_size={XML_MAXIMUM_FILE_SIZE}"
    )
    columns = to_json_types(_as_read_by_read_xml(schema_obj))
    if columns:
        struct = ", ".join(f"'{_sql_literal(name)}': '{_sql_literal(sql_type)}'" for name, sql_type in columns.items())
        typed = f"{read_xml}, columns={{{struct}}})"
    else:
        typed = f"{read_xml})"
    con.sql(f"CREATE VIEW {_quote(record_element)} AS {_xml_as_contract(con, typed, schema_obj)};")
    if columns:
        add_nested_views(con, record_element, schema_obj.properties)
    # Raw view without the columns= projection to check for absent columns (check_property_is_present);
    # as text, so that a value of the wrong type fails the checks of its column, not the presence of all
    raw = f"{read_xml}, all_varchar=true)"
    con.sql(f"CREATE VIEW {_quote(record_element + '__raw__')} AS {_xml_as_contract(con, raw, schema_obj)};")
    if schema_obj.name != record_element:
        con.sql(f"CREATE VIEW {_quote(schema_obj.name)} AS SELECT * FROM {_quote(record_element)};")


def _as_read_by_read_xml(schema_obj: SchemaObject) -> SchemaObject:
    """The schema with the names read_xml gives: #text for the text of an element with attributes, and an
    attribute named like a child element (@id) under its own name, which read_xml reads instead of the element's."""

    def rename(properties: List[SchemaProperty]) -> List[SchemaProperty]:
        attributes = {_xml_name(p).removeprefix("@") for p in properties if _is_xml_attribute(p)}
        renamed = []
        for prop in properties:
            if not _is_xml_attribute(prop) and not _is_xml_text(prop) and _xml_name(prop) in attributes:
                logger.warning(
                    f"The XML element {_xml_name(prop)} is named like an attribute; read_xml reads only the attribute"
                )
                continue
            physical_name = (
                "#text"
                if _is_xml_text(prop)
                else _xml_name(prop).removeprefix("@")
                if _is_xml_attribute(prop)
                else prop.physicalName
            )
            renamed.append(
                prop.model_copy(
                    update={
                        "physicalName": physical_name,
                        "properties": rename(prop.properties) if prop.properties else prop.properties,
                        "items": rename([prop.items])[0] if prop.items else prop.items,
                    }
                )
            )
        return renamed

    return schema_obj.model_copy(update={"properties": rename(schema_obj.properties or [])})


def _xml_as_contract(con, read_xml: str, schema_obj: SchemaObject) -> str:
    """A query that names and shapes what read_xml reads as the contract does.

    The text of an element with attributes is read as #text, where read_xml's own text_key option leaves it
    empty; it gets the name of the contract's xmlNode: text property. An attribute named like a child element
    gets its @ name.
    """
    relation = con.sql(f"SELECT * FROM {read_xml}")
    properties = schema_obj.properties or []
    keys = _xml_keys(properties)
    by_name = {_xml_name(p): p for p in properties}
    columns = []
    for name, dtype in zip(relation.columns, relation.types):
        target = keys.get(name, name)
        columns.append(f"{_xml_value(_quote(name), dtype, by_name.get(target))} AS {_quote(target)}")
    return f"SELECT {', '.join(columns)} FROM {read_xml}"


def _xml_value(expression: str, dtype, prop: Optional[SchemaProperty], depth: int = 0) -> str:
    """The expression named and shaped as the contract expects."""
    children = (prop.properties if prop else None) or []
    if dtype.id == "list":
        variable = f"x{depth}"
        value = _xml_value(variable, dtype.child, prop.items if prop else None, depth + 1)
        return expression if value == variable else f"list_transform({expression}, lambda {variable}: {value})"
    if prop is not None and prop.logicalType == "array":
        # An element that occurs once in every document is inferred as one value, not as a list of one
        return f"CASE WHEN {expression} IS NULL THEN NULL ELSE [{_xml_value(expression, dtype, prop.items, depth)}] END"
    if dtype.id != "struct":
        text = next((child for child in children if _is_xml_text(child)), None)
        if text is None:
            return expression
        # Inferred as plain text where some of the elements carry none of their attributes
        fields = ", ".join(f"{_quote(_xml_name(c))} := {expression if c is text else 'NULL'}" for c in children)
        return f"CASE WHEN {expression} IS NULL THEN NULL ELSE struct_pack({fields}) END"

    keys = _xml_keys(children)
    by_name = {_xml_name(child): child for child in children}
    fields = []
    changed = False
    for name, child_type in dtype.children:
        target = keys.get(name, name)
        source = f"struct_extract({expression}, '{_sql_literal(name)}')"
        value = _xml_value(source, child_type, by_name.get(target), depth)
        changed = changed or target != name or value != source
        fields.append(f"{_quote(target)} := {value}")
    if not changed:
        return expression
    # An absent object stays NULL, rather than becoming one whose fields are all NULL
    return f"CASE WHEN {expression} IS NULL THEN NULL ELSE struct_pack({', '.join(fields)}) END"


def _xml_keys(properties: List[SchemaProperty]) -> dict[str, str]:
    """The contract name of each key read_xml reads; for a name shared with an element, it reads the attribute."""
    keys = {_xml_name(p): _xml_name(p) for p in properties if not _is_xml_attribute(p) and not _is_xml_text(p)}
    keys |= {_xml_name(p).removeprefix("@"): _xml_name(p) for p in properties if _is_xml_attribute(p)}
    keys |= {"#text": _xml_name(p) for p in properties if _is_xml_text(p)}
    return keys


def _xml_node(prop: SchemaProperty) -> Optional[str]:
    return next((c.value for c in prop.customProperties or [] if c.property == "xmlNode"), None)


def _is_xml_text(prop: SchemaProperty) -> bool:
    return _xml_node(prop) == "text"


def _is_xml_attribute(prop: SchemaProperty) -> bool:
    return _xml_node(prop) == "attribute"


def _xml_name(prop: SchemaProperty) -> str:
    return prop.physicalName or prop.name


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def to_csv_types(schema_obj: SchemaObject) -> dict[Any, str | None] | None:
    if schema_obj is None:
        return None
    columns = {}
    if schema_obj.properties:
        for prop in schema_obj.properties:
            columns[prop.physicalName or prop.name] = convert_to_duckdb_csv_type(prop)
    return columns


def to_parquet_types(schema_obj: SchemaObject) -> dict[Any, str | None] | None:
    """Get proper SQL types for Parquet (preserves decimals, etc.)"""
    if schema_obj is None:
        return None
    columns = {}
    if schema_obj.properties:
        for prop in schema_obj.properties:
            columns[prop.physicalName or prop.name] = convert_to_duckdb(prop)
    return columns


def to_json_types(schema_obj: SchemaObject) -> dict[Any, str | None] | None:
    if schema_obj is None:
        return None
    columns = {}
    if schema_obj.properties:
        for prop in schema_obj.properties:
            columns[prop.physicalName or prop.name] = convert_to_duckdb_json_type(prop)
    return columns


def _get_type(prop: SchemaProperty) -> Optional[str]:
    """Get the type from a schema property. Prefers physicalType for accurate type checking."""
    if prop.physicalType:
        return prop.physicalType
    if prop.logicalType:
        return prop.logicalType
    return None


def add_nested_views(con: "duckdb.DuckDBPyConnection", model_name: str, properties: List[SchemaProperty] | None):
    model_name = model_name.strip('"')
    if properties is None:
        return
    for prop in properties:
        prop_type = _get_type(prop)
        if prop_type is None or prop_type.lower() not in ["array", "object"]:
            continue
        field_type = prop_type.lower()
        if field_type == "array" and prop.items is None:
            continue
        elif field_type == "object" and (prop.properties is None or len(prop.properties) == 0):
            continue

        field_name = prop.physicalName or prop.name
        nested_model_name = f"{model_name}__{field_name}"
        max_depth = 2 if field_type == "array" else 1

        ## if parent field is not required, the nested objects may resolve
        ## to a row of NULLs -- but if the objects themselves have required
        ## fields, this will fail the check.
        where = "" if prop.required else f" WHERE {_quote(field_name)} IS NOT NULL"
        con.sql(f"""
            CREATE VIEW IF NOT EXISTS {_quote(nested_model_name)} AS
            SELECT unnest({_quote(field_name)}, max_depth := {max_depth}) as {_quote(field_name)} FROM {_quote(model_name)} {where}
            """)
        if field_type == "array":
            add_nested_views(con, nested_model_name, prop.items.properties if prop.items else None)
        elif field_type == "object":
            add_nested_views(con, nested_model_name, prop.properties)


def _load_extension(con, name: str, extra: str) -> None:
    import gzip
    import importlib.resources
    import pathlib
    import shutil
    import tempfile

    # first try to use locally bundled wheel to support air-gapped environments
    try:
        ext_module = importlib.import_module(f"duckdb_extension_{name}")
        module_path = pathlib.Path(str(importlib.resources.files(ext_module)))
        duckdb_version = con.sql("PRAGMA version;").fetchone()[0]
        extension_file_gz = module_path / "extensions" / duckdb_version / f"{name}.duckdb_extension.gz"

        if extension_file_gz.exists():
            tmpdir = pathlib.Path(tempfile.mkdtemp(prefix=f"datacontract-{name}-"))
            extension_file = tmpdir / f"{name}.duckdb_extension"
            with gzip.open(extension_file_gz, "rb") as src, open(extension_file, "wb") as dst:
                shutil.copyfileobj(src, dst)
            con.sql(f"LOAD '{extension_file}'")
            return
    except ImportError:
        pass

    try:
        con.install_extension(name)
        con.load_extension(name)
    except Exception as e:
        raise RuntimeError(
            f"Failed to install the '{name}' DuckDB extension. "
            f"Please install the extension wheel via: pip install 'datacontract-cli[{extra}]'"
        ) from e


def _sql_literal(value) -> str:
    """Escape a value for a single-quoted duckdb string literal.

    Several of these come from the contract rather than the environment —
    `endpointUrl` and the storage account derived from `location` — and a
    contract can be a URL someone else published. A quote in one of those
    would otherwise end the literal and let the rest be parsed as SQL.
    """
    return str(value).replace("'", "''") if value is not None else ""


def setup_s3_connection(con, server: Server, config: Config | None = None):
    """boto3 resolves the credentials because duckdb's ``PROVIDER credential_chain`` cannot read an SSO cache."""
    _load_extension(con, "httpfs", "s3")
    _load_extension(con, "aws", "s3")
    s3_endpoint = "s3.amazonaws.com"
    use_ssl = "true"
    url_style = "vhost"
    if server.endpointUrl is not None:
        url_style = "path"
        s3_endpoint = server.endpointUrl.removeprefix("http://").removeprefix("https://")
        if server.endpointUrl.startswith("http://"):
            use_ssl = "false"

    options = {"ENDPOINT": s3_endpoint, "USE_SSL": use_ssl, "URL_STYLE": url_style}
    credentials = resolve_aws_credentials(config)
    if credentials is not None:
        # No PROVIDER: defaults to `config`, which accepts these explicit keys.
        # (duckdb >=1.5 rejects CREDENTIAL_CHAIN combined with explicit credentials.)
        options |= {
            "KEY_ID": credentials.access_key_id,
            "SECRET": credentials.secret_access_key,
            "REGION": credentials.region,
            "SESSION_TOKEN": credentials.session_token,
        }
    clauses = ", ".join(f"{name} '{_sql_literal(value)}'" for name, value in options.items() if value)
    con.sql(f"CREATE OR REPLACE SECRET s3_secret (TYPE S3, {clauses});")


def setup_gcs_connection(con, server: Server, config: Config):
    _load_extension(con, "httpfs", "gcs")
    key_id = config.get_gcs_key_id(required=True)
    secret = config.get_gcs_secret(required=True)

    con.sql(f"""
    CREATE SECRET gcs_secret (
        TYPE GCS,
        KEY_ID '{_sql_literal(key_id)}',
        SECRET '{_sql_literal(secret)}'
    );
    """)


def setup_azure_connection(con, server: Server, config: Config):
    tenant_id = config.get_azure_tenant_id(required=True)
    client_id = config.get_azure_client_id(required=True)
    client_secret = config.get_azure_client_secret(required=True)
    storage_account = (
        to_azure_storage_account(server.location) if server.type == "azure" and "://" in server.location else None
    )

    _load_extension(con, "azure", "azure")

    if storage_account is not None:
        con.sql(f"""
        CREATE SECRET azure_spn (
            TYPE AZURE,
            PROVIDER SERVICE_PRINCIPAL,
            TENANT_ID '{_sql_literal(tenant_id)}',
            CLIENT_ID '{_sql_literal(client_id)}',
            CLIENT_SECRET '{_sql_literal(client_secret)}',
            ACCOUNT_NAME '{_sql_literal(storage_account)}'
        );
        """)
    else:
        con.sql(f"""
        CREATE SECRET azure_spn (
            TYPE AZURE,
            PROVIDER SERVICE_PRINCIPAL,
            TENANT_ID '{_sql_literal(tenant_id)}',
            CLIENT_ID '{_sql_literal(client_id)}',
            CLIENT_SECRET '{_sql_literal(client_secret)}'
        );
        """)


def to_azure_storage_account(location: str) -> str | None:
    """
    Converts a storage location string to extract the storage account name.
    ODCS v3.0 has no explicit field for the storage account. It uses the location field, which is a URI.
    This function parses a storage location string to identify and return the
    storage account name. It handles two primary patterns:
    1. Protocol://containerName@storageAccountName
    2. Protocol://storageAccountName
    :param location: The storage location string to parse, typically following
                     the format protocol://containerName@storageAccountName. or
                     protocol://storageAccountName.
    :return: The extracted storage account name if found, otherwise None
    """
    # to catch protocol://containerName@storageAccountName. pattern from location
    match = re.search(r"(?<=@)([^.]*)", location, re.IGNORECASE)
    if match:
        return match.group()
    else:
        # to catch protocol://storageAccountName. pattern from location
        match = re.search(r"(?<=//)(?!@)([^.]*)", location, re.IGNORECASE)
    return match.group() if match else None
