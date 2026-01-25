from __future__ import annotations

import json
import os
from collections import OrderedDict
from typing import Any, Dict

import yaml
from open_data_contract_standard.model import OpenDataContractStandard

from datacontract.imports.importer import Importer
from datacontract.model.exceptions import DataContractException


class SnowflakeImporter(Importer):
    def import_source(self, source: str, import_args: dict) -> OpenDataContractStandard:
        if source is not None:
            return import_Snowflake_from_connector(
                account=source,
                database=import_args.get("snowflake_db"),
                schema=import_args.get("schema"),
            )


def import_Snowflake_from_connector(account: str, database: str, schema: str) -> OpenDataContractStandard:
    ## connect to snowflake and get cursor
    conn = snowflake_cursor(account, database, schema)
    with conn.cursor() as cur:
        cur.execute(f"USE SCHEMA {database}.{schema}")

        cur.execute(f"SHOW COLUMNS IN SCHEMA {database}.{schema}")
        schema_sfqid = str(cur.sfqid)
        cur.execute(f"SHOW PRIMARY KEYS IN SCHEMA {database}.{schema}")
        businessKey_sfqid = str(cur.sfqid)
        # -- AS
        # SET(col, pk) = (SELECT LAST_QUERY_ID(-2), LAST_QUERY_ID(-1));"
        cur.execute_async(snowflake_query(account, schema, schema_sfqid, businessKey_sfqid))
        cur.get_results_from_sfqid(cur.sfqid)
        # extract and save ddl script into sql file
        json_contract = cur.fetchall()

        # Try to Preserve order when dumping to yaml properties as columns order matters
        yaml.add_representer(dict, map_representer, Dumper=yaml.Dumper)
        yaml.add_representer(OrderedDict, map_representer, Dumper=yaml.Dumper)

        if len(json_contract) == 0 or len(json_contract[0]) == 0:
            raise DataContractException(
                type="import",
                result="failed",
                name="snowflake import",
                reason=f"No data contract returned from schema {schema} in database {database} please check connectivity and schema existence",
                engine="datacontract",
            )
        result_set = json.loads(json_contract[0][0], object_pairs_hook=OrderedDict)
        sorted_properties = sort_schema_by_name_properties_by_ordinalPosition(result_set)

        toYaml = yaml.dump(sorted_properties, sort_keys=False)

        return OpenDataContractStandard.from_string(toYaml)


def map_representer(dumper, data):
    return dumper.represent_dict(getattr(data, "items")())


def snowflake_query(account: str, schema: str, schema_sfqid: str, businessKey_sfqid: str) -> str:
    sqlStatement = """
    --SHOW COLUMNS;
    --SHOW PRIMARY KEYS;

    --SET(schema_sfqid, businessKey_sfqid) = (SELECT LAST_QUERY_ID(-2), LAST_QUERY_ID(-1));

WITH INFO_SCHEMA_COLUMNS AS (
    SELECT 
    "schema_name" as schema_name,
    "table_name" as table_name,
    "column_name" as "name", 
    "null?" = 'NOT_NULL' as required,
    RIGHT("column_name",3) = '_SK' as "unique",
    coalesce(GET_PATH(TRY_PARSE_JSON("comment"),'description'), "comment") as description,
    CASE GET_PATH(TRY_PARSE_JSON("data_type"),'type')::string
    WHEN 'TEXT' THEN 'string'
    WHEN 'FIXED' THEN 'number'
    WHEN 'REAL' THEN 'number'
    WHEN 'BOOLEAN' THEN 'boolean'
    WHEN 'VARIANT' THEN 'object'
    WHEN 'TIMESTAMP_TZ' THEN 'timestamp'
    WHEN 'TIMESTAMP_NTZ' THEN 'timestamp'
    WHEN 'TIMESTAMP_LTZ' THEN 'timestamp'
    WHEN 'DATE' THEN 'date'
    ELSE 'object' END as LogicalType, -- FIXED NUMBER
    CASE GET_PATH(TRY_PARSE_JSON("data_type"),'type')::string
    WHEN 'TEXT' THEN CONCAT('STRING','(',GET_PATH(TRY_PARSE_JSON("data_type"),'length'),')')
    WHEN 'FIXED' THEN CONCAT('NUMBER','(',GET_PATH(TRY_PARSE_JSON("data_type"),'precision')::string,',',GET_PATH(TRY_PARSE_JSON("data_type"),'scale'),')',' ',"autoincrement")
    WHEN 'BOOLEAN' THEN 'BOOLEAN'
    WHEN 'TIMESTAMP_NTZ' THEN CONCAT('TIMESTAMP_NTZ','(',GET_PATH(TRY_PARSE_JSON("data_type"),'scale'),')')
    ELSE GET_PATH(TRY_PARSE_JSON("data_type"),'type') END as PhysicalType,
    IFF (GET_PATH(TRY_PARSE_JSON("data_type"),'type')::string = 'TEXT', GET_PATH(TRY_PARSE_JSON("data_type"),'length')::string , NULL) as logicatTypeOptions_maxlength,
    IFF ("column_name" IN ('APP_NAME','CREATE_TS','CREATE_AUDIT_ID','UPDATE_TS','UPDATE_AUDIT_ID','CURRENT_RECORD_IND','DELETED_RECORD_IND', 'FILE_BLOB_PATH', 'FILE_ROW_NUMBER', 'FILE_LAST_MODIFIED', 'IS_VALID_IND', 'INVALID_MESSAGE' ), ARRAY_CONSTRUCT('metadata'), NULL ) as tags,
    IS_C.ORDINAL_POSITION
    FROM TABLE(RESULT_SCAN('$schema_sfqid')) as T
    JOIN INFORMATION_SCHEMA.COLUMNS as IS_C ON T."table_name"= IS_C.TABLE_NAME AND  T."schema_name" = IS_C.TABLE_SCHEMA AND T."column_name" = IS_C.COLUMN_NAME AND T."database_name" = IS_C.TABLE_CATALOG
)
,
INFO_SCHEMA_CONSTRAINTS AS (
SELECT 
    "schema_name" as schema_name, 
    "table_name" as table_name,
    "column_name" as "name", 
    IFF(RIGHT("column_name",3)='_SK', -1, "key_sequence") as primaryKeyPosition,
        true as primaryKey, 
FROM(TABLE(RESULT_SCAN('$businessKey_sfqid')))
),
INFO_SCHEMA_TABLES AS (
SELECT 
    TABLE_SCHEMA as table_schema, 
    TABLE_NAME as "name",
    UPPER(CONCAT(T.table_schema,'.',T.table_name)) as physical_name,
    NULLIF(coalesce(GET_PATH(TRY_PARSE_JSON(COMMENT),'description'), COMMENT),'') as description,
    'object' as logicalType,
    lower(REPLACE(TABLE_TYPE,'BASE ','')) as physicalType
FROM INFORMATION_SCHEMA.TABLES as T
),
PROPERTIES AS (
SELECT 
C.schema_name,
C.table_name,
ARRAY_AGG(OBJECT_CONSTRUCT(
    'id',           C."name"||'_propId',
    'name',         C."name",
    'required',     C.required,
    'unique',       C."unique",
    'description',  C.description,
    'logicalType',  C.LogicalType,
    IFF(logicatTypeOptions_maxlength::number IS NOT NULL,'logicalTypeOptions',NULL), IFF( logicatTypeOptions_maxlength::number IS NOT NULL , OBJECT_CONSTRUCT('maxLength',logicatTypeOptions_maxlength::number), NULL),  
    'physicalType', TRIM(C.PhysicalType),
    IFF(BK.primaryKey = true, 'primaryKey', NULL), IFF(BK.primaryKey = true,true, NULL),
    IFF(BK.primaryKey = true, 'primaryKeyPosition', NULL), IFF(BK.primaryKey = true, BK.primaryKeyPosition, NULL),
    IFF(C.tags IS NOT NULL,'tags',NULL) , IFF(C.tags IS NOT NULL, C.tags, NULL),
    'customProperties', ARRAY_CONSTRUCT_COMPACT(
                                        OBJECT_CONSTRUCT(
                                        'property', 'ordinal_position',
                                        'value', C.ORDINAL_POSITION
                                        ),
                                        OBJECT_CONSTRUCT(
                                        'property','scdType',    
                                        'value', IFF( COALESCE(BK.primaryKey,false) ,0,1)
                                        ),
                                        IFF(BK.primaryKey = True AND Right(C."name",3) != '_SK', OBJECT_CONSTRUCT(
                                        'property','businessKey',
                                        'value', True), NULL))
                        )) as properties
FROM INFO_SCHEMA_COLUMNS C
LEFT JOIN INFO_SCHEMA_CONSTRAINTS BK ON (C.schema_name = BK.schema_name 
                            AND C.table_name = BK.table_name 
                            AND C."name" = BK."name")
GROUP BY C.schema_name, C.table_name
)
, SCHEMA_DEF AS (
SELECT
T.table_schema,
ARRAY_AGG( OBJECT_CONSTRUCT( 
    'id', T."name" ||'_schId',
    'name',T."name",
    'physicalName',T.physical_name,
    'logicalType',T.logicalType,
    'physicalType',T.physicalType,
    'description',T.description,
    'properties', P.properties))
    as "schema"
FROM PROPERTIES P
LEFT JOIN INFO_SCHEMA_TABLES T ON (P.schema_name = T.table_schema 
                        AND P.table_name = T."name")
WHERE T.table_schema = '{schema}' -- Ignore PUBLIC (default)
GROUP BY T.table_schema
)
SELECT 
OBJECT_CONSTRUCT('apiVersion', 'v3.1.0',
'kind','DataContract',
'id', UUID_STRING(),
'name',table_schema,
'version','0.0.1',
'domain','dataplatform',
'status','development',
'description', OBJECT_CONSTRUCT(
    'purpose','This data can be used for analytical purposes', 
    'limitations', 'not defined',
    'usage', 'not defined'),
'customProperties', ARRAY_CONSTRUCT( OBJECT_CONSTRUCT('property','owner', 'value','dataplatform')),
'servers', ARRAY_CONSTRUCT( 
    OBJECT_CONSTRUCT(
        'server','snowflake_dev', 
        'type','snowflake',
        'account', '{account}',
        'environment', 'dev',
        'host', '{account}.snowflakecomputing.com',
        'port', 443,
        'database', CURRENT_DATABASE(),
        'warehouse', CURRENT_WAREHOUSE(),
        'schema', table_schema,
        'roles', ARRAY_CONSTRUCT(OBJECT_CONSTRUCT(
            'role', CURRENT_ROLE(),
            'access','write',
            'firstLevelApprovers', CURRENT_USER()
            )                                                                                    
                                    )
                    ),
    OBJECT_CONSTRUCT(
        'server','snowflake_uat', 
        'type','snowflake',
        'account', '{account}',
        'environment', 'uat',
        'host', '{account}.snowflakecomputing.com',
        'port', 443,
        'database', CURRENT_DATABASE(),
        'warehouse', CURRENT_WAREHOUSE(),
        'schema', table_schema,
        'roles', ARRAY_CONSTRUCT(OBJECT_CONSTRUCT(
            'role', CURRENT_ROLE(),
            'access','write',
            'firstLevelApprovers', CURRENT_USER()
            )                                                                                    
        )
                    ),                
        OBJECT_CONSTRUCT(
        'server','snowflake', 
        'type','snowflake',
        'account', '{account}',
        'environment', 'prd',
        'host', '{account}.snowflakecomputing.com',
        'port', 443,
        'database', CURRENT_DATABASE(),
        'warehouse', CURRENT_WAREHOUSE(),
        'schema', table_schema,
        'roles', ARRAY_CONSTRUCT(OBJECT_CONSTRUCT(
            'role', CURRENT_ROLE(),
            'access','write',
            'firstLevelApprovers', CURRENT_USER()
            )                                                                                    
        )
                    )
        ),                                       
'schema', "schema") as "DataContract (ODCS)"
FROM SCHEMA_DEF
    """
    return (
        sqlStatement.replace("$schema_sfqid", schema_sfqid)
        .replace("$businessKey_sfqid", businessKey_sfqid)
        .replace("{schema}", schema)
        .replace("{account}", account)
    )


def snowflake_cursor(account: str, databasename: str = "DEMO_DB", schema: str = "PUBLIC"):
    try:
        from snowflake.connector import connect
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="snowflake extra missing",
            reason="Install the extra datacontract-cli[snowflake] to use snowflake",
            engine="datacontract",
            original_exception=e,
        )

    ###
    ## Snowflake connection
    ## https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-connect
    ###
    # gather connection parameters from environment variables
    user_connect = os.environ.get("DATACONTRACT_SNOWFLAKE_USERNAME", None)
    password_connect = os.environ.get("DATACONTRACT_SNOWFLAKE_PASSWORD", None)
    account_connect = account
    role_connect = os.environ.get("DATACONTRACT_SNOWFLAKE_ROLE", None)
    authenticator_connect = "externalbrowser" if password_connect is None else "snowflake"
    warehouse_connect = os.environ.get("DATACONTRACT_SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
    database_connect = databasename or "DEMO_DB"
    schema_connect = schema or "PUBLIC"
    private_key_file = None
    private_key_file_pwd = None

    # build connection
    if os.environ.get("SNOWFLAKE_DEFAULT_CONNECTION_NAME", None) is not None:
        # use the default connection defined in the snowflake config file : connections.toml and config.toml
        conn = connect(
            session_parameters={
                "QUERY_TAG": "datacontract-cli import",
                "use_openssl_only": False,
            }
        )
    elif authenticator_connect == "externalbrowser":
        # use external browser auth
        conn = connect(
            user=user_connect,
            account=account_connect,
            authenticator=authenticator_connect,
            session_parameters={
                "QUERY_TAG": "datacontract-cli import",
                "use_openssl_only": False,
            },
            warehouse=warehouse_connect,
            role=role_connect,
            database=database_connect,
            schema=schema_connect,
        )
    elif private_key_file is not None:
        # use private key auth
        conn = connect(
            user=user_connect,
            account=account_connect,
            private_key_file=private_key_file,
            private_key_fil_pwd=private_key_file_pwd.encode("UTF-8"),
            session_parameters={
                "QUERY_TAG": "datacontract-cli import",
                "use_openssl_only": False,
            },
            warehouse=warehouse_connect,
            role=role_connect,
            database=database_connect,
            schema=schema_connect,
        )
    else:
        # use the login/password auth
        conn = connect(
            user=user_connect,
            password=password_connect,
            account=account_connect,
            authenticator=authenticator_connect,
            session_parameters={
                "QUERY_TAG": "datacontract-cli import",
                "use_openssl_only": False,
            },
            warehouse=warehouse_connect,
            role=role_connect,
            database=database_connect,
            schema=schema_connect,
        )
    return conn


def _get_ordinal_position_value(col: Dict[str, Any]) -> Any:
    """Extract customProperties value where property == 'ordinal_position'."""
    for cp in col.get("customProperties") or []:
        if isinstance(cp, dict) and cp.get("property") == "ordinal_position":
            return cp.get("value")
    return None


def sort_schema_by_name_properties_by_ordinalPosition(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    - Does NOT reorder payload['schema'].
    - For each schema element (table), sorts table['properties'] by ordinal_position.value.
    - Does NOT sort customProperties themselves.
    """
    schema = payload.get("schema")
    if not isinstance(schema, list):
        return payload
    new_schema = []
    for table in schema:
        props = table.get("properties")
        if not isinstance(props, list):
            continue

        def col_key(col: Dict[str, Any]):
            ord_val = _get_ordinal_position_value(col)
            return (ord_val, f"{table.get('name').lower()}.{col.get('name').lower()}")

        props.sort(key=col_key)
        table["properties"] = props
        new_schema.append(table)

    new_schema.sort(key=lambda t: t.get("name").lower())

    payload["schema"] = new_schema
    return payload
