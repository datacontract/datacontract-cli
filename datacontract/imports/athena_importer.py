"""Create a data contract from an Amazon Athena database.

Athena has no catalog of its own: its tables live in the AWS Glue Data Catalog,
so the metadata is read with the shared Glue reader rather than by querying
Athena. Reading the catalog costs nothing, needs only ``glue:GetTables``, and
avoids the S3 staging round-trip an ``information_schema`` query would need.

The one thing Glue and Athena disagree on is the name of two types: Glue stores
the Hive spelling, Athena reports the Trino spelling. Everything else already
compares equal in the Athena dialect (``int``/``integer``, ``array<int>``/
``array(integer)``, ``struct``/``row(...)``, ``decimal``/``decimal(10,2)``), so
only those two tokens are rewritten — otherwise every string column would fail
its physical type check on the first `datacontract test`.
"""

from __future__ import annotations

from typing import List, Optional

from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty

from datacontract.imports.glue_importer import create_schema_objects, get_glue_tables
from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import create_odcs, create_server
from datacontract.model.exceptions import DataContractException

DEFAULT_CATALOG = "awsdatacatalog"

# Glue (Hive) spelling -> what Athena reports back from its catalog.
HIVE_TO_ATHENA_TYPES = {
    "string": "varchar",
    "binary": "varbinary",
}


class AthenaImporter(Importer):
    def import_source(self, source: str, import_args: dict, config=None) -> OpenDataContractStandard:
        return import_athena(
            schema=import_args.get("schema"),
            staging_dir=import_args.get("staging_dir"),
            region=import_args.get("region"),
            catalog=import_args.get("catalog"),
            tables=import_args.get("athena_table"),
            config=config,
        )


def import_athena(
    schema: Optional[str],
    staging_dir: Optional[str],
    region: Optional[str] = None,
    catalog: Optional[str] = None,
    tables: Optional[List[str]] = None,
    config=None,
) -> OpenDataContractStandard:
    if not schema:
        raise DataContractException(
            type="source",
            name="athena import schema",
            reason="The Athena database is required for the athena import, e.g. --schema my_database",
            engine="datacontract",
        )
    if not staging_dir:
        raise DataContractException(
            type="source",
            name="athena import staging dir",
            reason=(
                "An S3 staging directory is required for the athena import so the contract can be tested, "
                "e.g. --staging-dir s3://my-bucket/athena-results/"
            ),
            engine="datacontract",
        )

    selected = _select_tables(get_glue_tables(schema, region, config), tables)
    if not selected:
        raise DataContractException(
            type="schema",
            result="failed",
            name="no tables found",
            reason=f"No tables found in the Athena database '{schema}'.",
            engine="datacontract",
        )

    odcs = create_odcs()
    odcs.servers = [
        create_server(
            name="athena",
            server_type="athena",
            catalog=catalog or DEFAULT_CATALOG,
            schema=schema,
            region_name=region,
            staging_dir=staging_dir,
        )
    ]
    odcs.schema_ = create_schema_objects(schema, selected, region, config)
    for schema_object in odcs.schema_:
        for prop in schema_object.properties or []:
            _to_athena_types(prop)
    return odcs


def _select_tables(table_names: List[str], tables: Optional[List[str]]) -> List[str]:
    if not tables:
        return sorted(table_names, key=str.lower)
    wanted = {table.lower() for table in tables}
    return sorted((name for name in table_names if name.lower() in wanted), key=str.lower)


def _to_athena_types(prop: SchemaProperty) -> None:
    """Rewrite the Hive-only type names, in place, through the whole property tree."""
    if prop.physicalType:
        prop.physicalType = HIVE_TO_ATHENA_TYPES.get(prop.physicalType.lower(), prop.physicalType)
    for child in prop.properties or []:
        _to_athena_types(child)
    if prop.items:
        _to_athena_types(prop.items)
