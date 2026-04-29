from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, List

from open_data_contract_standard.model import (
    CustomProperty,
    DataQuality,
    OpenDataContractStandard,
    Role,
    SchemaProperty,
)
from pydantic import TypeAdapter

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import create_odcs, create_property, create_schema_object, create_server
from datacontract.imports.sql_importer import map_type_from_sql
from datacontract.model.exceptions import DataContractException


class SnowflakeImporter(Importer):
    def import_source(self, source: str, import_args: dict) -> OpenDataContractStandard:
        if source is not None:
            return import_Snowflake_from_connector(
                account=source,
                database=import_args.get("database"),
                schema=import_args.get("schema"),
            )


def information_schema_table_privileges_query() -> str:
    return """
        SELECT 
            TABLE_CATALOG,                
            TABLE_SCHEMA, 
            CURRENT_WAREHOUSE() as WAREHOUSE,
            ARRAY_AGG(
                OBJECT_CONSTRUCT(
                    'role', GRANTEE,
                    'access',LOWER(PRIVILEGE_TYPE),
                    'firstLevelApprovers', GRANTOR
                    )
            )   as Roles
        FROM information_schema.table_privileges
        WHERE GRANTED_TO = 'ROLE' 
        AND TABLE_CATALOG = CURRENT_DATABASE()
        AND TABLE_SCHEMA = CURRENT_SCHEMA()  
                
        GROUP BY TABLE_CATALOG, TABLE_SCHEMA;
    """


def information_schema_tables_query() -> str:
    return """
        SELECT 
            TABLE_SCHEMA, 
            TABLE_NAME,
            UPPER(TABLE_NAME) as physical_name,
            NULLIF(coalesce(GET_PATH(TRY_PARSE_JSON(COMMENT),'description'), COMMENT),'') as description,
            lower(REPLACE(TABLE_TYPE,'BASE ','')) as physical_Type
        FROM INFORMATION_SCHEMA.TABLES
        WHERE CURRENT_SCHEMA() = TABLE_SCHEMA 
        AND CURRENT_DATABASE() = TABLE_CATALOG;
    """


def information_schema_columns_query() -> str:
    return """
                SELECT 
            IS_C.TABLE_CATALOG,
            IS_C.TABLE_SCHEMA,
            IS_C.TABLE_NAME, -- schema.name
            ARRAY_AGG(
                OBJECT_CONSTRUCT( 
                'id', IS_C.COLUMN_NAME ||'_propId', 
                'name', IS_C.COLUMN_NAME ,-- property.name
                'description', COALESCE(
                                GET_PATH(TRY_PARSE_JSON(IS_C.COMMENT),'description'), 
                                IS_C.COMMENT) ,
                'required', IFF(IS_C.IS_NULLABLE = 'YES', false, true), -- property.Required
                'unique', IFF(IS_C.IS_IDENTITY = 'YES', true, false), -- property.unique
                'logicalType', COALESCE(IS_C.DATA_TYPE,IS_C.DATA_TYPE_ALIAS),
                'logicalTypeOptions', 
                                        IFF(  IS_C.CHARACTER_MAXIMUM_LENGTH IS NOT NULL,
                                            OBJECT_CONSTRUCT('maxLength',IS_C.CHARACTER_MAXIMUM_LENGTH)
                                            , NULL), -- property.Logical Type Option . 
                'physicalType', CASE WHEN IS_C.IS_IDENTITY = 'YES' THEN 
                            CONCAT(COALESCE(IS_C.DATA_TYPE_ALIAS,IS_C.DATA_TYPE),
                                'AUTOINCREMENENT START ', IS_C.IDENTITY_START, ' INCREMENT ', IS_C.IDENTITY_INCREMENT, 
                                IFF(IS_C.IDENTITY_ORDERED = 'YES', ' ORDER', ' NOORDER'))
                            ELSE COALESCE(IS_C.DATA_TYPE_ALIAS,IS_C.DATA_TYPE) END,
                'customProperties',ARRAY_CONSTRUCT_COMPACT(
                    OBJECT_CONSTRUCT(
                        'property','ordinalPosition',    
                        'value', IS_C.ORDINAL_POSITION
                    ),
                    IFF (IS_C.COLUMN_DEFAULT IS NOT NULL,
                        OBJECT_CONSTRUCT(
                        'property','default',    
                        'value', IS_C.COLUMN_DEFAULT
                    ), NULL),
                    IFF(IS_C.NUMERIC_PRECISION IS NOT NULL OR IS_C.DATETIME_PRECISION IS NOT NULL,
                        OBJECT_CONSTRUCT(
                        'property','precision',    
                        'value', COALESCE(IS_C.NUMERIC_PRECISION, IS_C.DATETIME_PRECISION)
                    ), NULL),
                    IFF(IS_C.NUMERIC_SCALE IS NOT NULL,
                        OBJECT_CONSTRUCT(
                        'property','scale',    
                        'value', IS_C.NUMERIC_SCALE
                    ), NULL),
                    IFF( IS_C.CHARACTER_SET_NAME IS NOT NULL,
                        OBJECT_CONSTRUCT(
                        'property','characterSet',    
                        'value', IS_C.CHARACTER_SET_NAME
                    ), NULL),
                    IFF( IS_C.COLLATION_NAME IS NOT NULL,
                        OBJECT_CONSTRUCT(
                        'property','collation',    
                        'value', IS_C.COLLATION_NAME
                    ), NULL)
                    )               
                ) ) as properties
        FROM INFORMATION_SCHEMA.COLUMNS as IS_C 
        WHERE IS_C.TABLE_CATALOG = CURRENT_DATABASE()
        AND IS_C.TABLE_SCHEMA = CURRENT_SCHEMA()
        GROUP BY IS_C.TABLE_CATALOG, IS_C.TABLE_SCHEMA, IS_C.TABLE_NAME;
    """


def account_usage_tags_references_query() -> str:
    return """
        SELECT 
            OBJECT_DATABASE,
            OBJECT_SCHEMA, 
            OBJECT_NAME, 
            COLUMN_NAME, 
            ARRAY_AGG(CONCAT(TAG_NAME,'=',TAG_VALUE)) as TAGS
        FROM SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES
        WHERE OBJECT_SCHEMA = CURRENT_SCHEMA()
        AND OBJECT_DATABASE = CURRENT_DATABASE()
        GROUP BY OBJECT_DATABASE, OBJECT_SCHEMA, OBJECT_NAME, COLUMN_NAME;
    """


def local_data_quality_monitoring_results_query() -> str:
    return """
        SELECT 
            TABLE_DATABASE,
            TABLE_SCHEMA,
            TABLE_NAME, 
            TYPES, 
            COLUMN_NAME, 
            ARRAY_AGG(quality) as QUALITY
        FROM (
            SELECT  
                TABLE_DATABASE,
                TABLE_SCHEMA,
                TABLE_NAME, 
                IFF(ARRAY_SIZE(ARGUMENT_NAMES) = 1 
                        AND ARGUMENT_TYPES[0]::string = 'COLUMN', 
                            'COLUMN', 'RECORD') as TYPES , 
                ARRAY_TO_STRING(ARGUMENT_NAMES, ',') as COLUMN_NAME,   
                OBJECT_CONSTRUCT(
                'id', CONCAT(LOWER(TABLE_NAME),'_',
                                LOWER(
                                    IFF(ARRAY_SIZE(ARGUMENT_NAMES) = 1 
                                            AND ARGUMENT_TYPES[0]::string = 'COLUMN', 
                                                'COLUMN', 'RECORD')
                                ),
                            '_',
                            LOWER(METRIC_NAME),
                            '_',
                            LOWER(ARRAY_TO_STRING(ARGUMENT_NAMES, ',')),
                            '_id'),
                'metric', COALESCE(ODCS_RULES.odcs_metric, METRIC_NAME),
                COALESCE(odcs_operator,'mustBe'), VALUE
                ) as quality,
            FROM SNOWFLAKE.LOCAL.DATA_QUALITY_MONITORING_RESULTS
            -- https://bitol-io.github.io/open-data-contract-standard/latest/data-quality/#metrics
            LEFT JOIN (VALUES('NULL_COUNT', 'nullValues', 'mustBe'), 
                            ('BLANK_COUNT','missingValues', 'mustBe'), 
                            ('ROW_COUNT', 'rowCount','mustBeGreaterOrEqualTo'),
                            ('ACCEPTED_VALUES', 'invalidValues','mustBeLessThan'),
                            ('DUPLICATE_COUNT', 'duplicateValues','mustBeLessThan')                 
                            ) as ODCS_RULES(snowflake_metricName, odcs_metric, odcs_operator) 
                    ON METRIC_NAME = snowflake_metricName
            WHERE TABLE_DATABASE = CURRENT_DATABASE() 
            AND TABLE_SCHEMA = CURRENT_SCHEMA()
            QUALIFY ROW_NUMBER() 
                    OVER (PARTITION BY TABLE_DATABASE,TABLE_SCHEMA, TABLE_NAME, ARGUMENT_TYPES, METRIC_NAME, ARGUMENT_NAMES 
                            ORDER BY MEASUREMENT_TIME DESC) = 1
            ) as DMF_METRICS_RESULT
            GROUP BY TABLE_DATABASE, TABLE_SCHEMA,TABLE_NAME, TYPES, COLUMN_NAME;
"""


def import_information_schema(conn) -> Dict[str, List[Dict]]:
    from snowflake.connector import DictCursor
    from snowflake.connector.constants import QueryStatus

    query_pool = {}
    with conn.cursor(DictCursor) as cur:
        ##Run all queries in parallel to optimize performance
        cur.execute_async(information_schema_table_privileges_query())
        query_pool["server"] = str(cur.sfqid)

        cur.execute_async(information_schema_tables_query())
        query_pool["schemas"] = str(cur.sfqid)

        cur.execute_async(information_schema_columns_query())
        query_pool["properties"] = str(cur.sfqid)

        cur.execute_async(account_usage_tags_references_query())
        query_pool["tags"] = str(cur.sfqid)

        cur.execute_async(local_data_quality_monitoring_results_query())
        query_pool["quality"] = str(cur.sfqid)

    # wait for all queries to finish before fetching results to optimize performance by running queries in parallel
    for qid in query_pool.values():
        while conn.get_query_status(qid) not in [QueryStatus.SUCCESS, QueryStatus.FAILED_WITH_ERROR]:
            time.sleep(0.2)

    # load resultsets into a dict of name to resultset to optimize performance by fetching results
    resultsets = {}
    for name, qid in query_pool.items():
        with conn.cursor(DictCursor) as cur:
            cur.get_results_from_sfqid(qid)
            resultsets[name] = cur.fetchall()

    return resultsets


def schema_properties_cleansing(
    properties: List[SchemaProperty], propertiesTags: List[Dict[str, Any]], propertiesQuality: List[Dict[str, Any]]
) -> List[SchemaProperty]:
    """
    Cleanses the properties list by removing None values and ensuring all required fields are present.
    """
    tagsAdapter = TypeAdapter(list[str])
    qualityAdapter = TypeAdapter(list[DataQuality])
    cleansed_properties = []

    for prop in properties:
        if prop.name is None or prop.logicalType is None:
            continue  # Skip properties that don't have required fields

        logical_type, format = map_type_from_sql(prop.logicalType)
        max_length = prop.logicalTypeOptions.get("maxLength", None) if prop.logicalTypeOptions else None

        precision = [cp.value for cp in prop.customProperties if cp.property == "precision"]
        scale = [cp.value for cp in prop.customProperties if cp.property == "scale"]

        tags = [
            tag["TAGS"] for tag in propertiesTags if tag["COLUMN_NAME"] == prop.name and tag["COLUMN_NAME"] is not None
        ]
        quality = [
            q["QUALITY"] for q in propertiesQuality if q["COLUMN_NAME"] == prop.name and q["COLUMN_NAME"] is not None
        ]

        prop = create_property(
            name=prop.name,
            logical_type=logical_type,
            physical_type=prop.physicalType,
            description=prop.description,
            max_length=max_length,
            precision=precision[0] if len(precision) > 0 else None,
            scale=scale[0] if len(scale) > 0 else None,
            format=format,
            required=prop.required,
            tags=tagsAdapter.validate_json(tags[0] if len(tags) > 0 else "[]"),
            custom_properties={cp.property: cp.value for cp in prop.customProperties},
            id=prop.id,
            quality=qualityAdapter.validate_json(quality[0] if len(quality) > 0 else "[]"),
        )
        cleansed_properties.append(prop)

    return cleansed_properties


def _get_ordinal_position_value(cpList: List[CustomProperty]) -> Any:
    """Extract customProperties value where property == 'ordinalPosition'."""
    for cp in cpList:
        if cp.property == "ordinalPosition":
            return int(cp.value)
    return None


def property_customs_ordinalPosition_sort(col: SchemaProperty) -> Any:
    ord_val = _get_ordinal_position_value(col.customProperties)
    return (ord_val, f"{col.name.lower()}")


def import_Snowflake_from_connector(account: str, database: str, schema: str) -> OpenDataContractStandard:
    ## connect to snowflake and get cursor
    conn = snowflake_cursor(account, database, schema)
    try:
        # To catch incomplete installation of snowflake extra which will cause the connect import to succeed but fail later when trying to catch ProgrammingError for schema with double-quoted identifiers issue https://docs.snowflake.com/en/sql-reference/identifiers-syntax#double-quoted-identifiers
        from snowflake.connector.errors import ProgrammingError
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="snowflake extra missing",
            reason="Install the extra datacontract-cli[snowflake] to use snowflake",
            engine="datacontract",
            original_exception=e,
        )

    # Define Database and Schema Context for the import, to avoid having to specify it in every query and to catch double_quoted identifier issue https://docs.snowflake.com/en/sql-reference/identifiers-syntax#double-quoted-identifiers
    with conn.cursor() as cur:
        try:
            cur.execute(f"USE SCHEMA {database}.{schema}")
            schema_identifier = schema
        except ProgrammingError:
            # schema with double-quoted identifiers issue https://docs.snowflake.com/en/sql-reference/identifiers-syntax#double-quoted-identifiers
            cur.execute(f'USE SCHEMA {database}."{schema}"')
            schema_identifier = f'"{schema}"'

    # get all information from information_schema in parallel to optimize performance
    resulsets = import_information_schema(conn)

    odcs = create_odcs()
    # server
    ListRoleAdapter = TypeAdapter(List[Role])
    for row in resulsets["server"]:
        server = create_server(
            name="workspace",
            server_type="snowflake",
            environment=row["TABLE_CATALOG"]
            .split("_")[0]
            .lower(),  # we don't have environment info in snowflake metadata, so we default to first part of the database name before the first underscore which is usually the organization name in snowflake, e.g. PRD_, QA_, DEV_ etc. This is of course a heuristic and might not work for everyone but it's the best we can do with the available metadata, and it can be easily overridden by the user if needed.
            account=account,
            host=f"{account}.azure.snowflakecomputing.com",
            database=row["TABLE_CATALOG"],
            schema=schema_identifier,
            warehouse=row["WAREHOUSE"],
            port=443,
            roles=ListRoleAdapter.validate_json(row["ROLES"]),
        )
    # only one server in snowflake, we can safely assign it to the ODCS
    odcs.servers = [server]

    # schemas
    ListPropertiesAdapter = TypeAdapter(List[SchemaProperty])
    DataQualityAdapter = TypeAdapter(List[DataQuality])
    schemas = []
    enhanced_schemas = []

    for schema in resulsets["schemas"]:
        # for each schema we need to get the properties and quality information from the resultsets we fetched in parallel to optimize performance by avoiding nested loops and multiple iterations over the resultsets, we can filter the relevant information for each schema using list comprehensions which are optimized in python and will be much faster than nested loops especially when we have a large number of schemas and properties.
        listOfProperties = [
            prop["PROPERTIES"] for prop in resulsets["properties"] if prop["TABLE_NAME"] == schema["TABLE_NAME"]
        ]
        listOfDataQuality = [
            quality["QUALITY"]
            for quality in resulsets["quality"]
            if quality["TABLE_NAME"] == schema["TABLE_NAME"] and quality["TYPES"] == "RECORD"
        ]

        schemas.append(
            create_schema_object(
                name=schema["TABLE_NAME"],
                description=schema["DESCRIPTION"],
                physical_name=schema["PHYSICAL_NAME"],
                physical_type=schema["PHYSICAL_TYPE"],  # table or view
                properties=ListPropertiesAdapter.validate_json(listOfProperties[0])
                if len(listOfProperties) > 0
                else None,
                quality=DataQualityAdapter.validate_json(listOfDataQuality[0]) if len(listOfDataQuality) > 0 else None,
            )
        )

    # cleansing
    for schema in schemas:
        # tags
        properties_tags = [tag for tag in resulsets["tags"] if tag["TABLE_NAME"] == schema.name]

        # quality
        properties_quality = [
            quality
            for quality in resulsets["quality"]
            if quality["TABLE_NAME"] == schema.name and quality["TYPES"] == "COLUMN"
        ]

        schema.properties = schema_properties_cleansing(schema.properties, properties_tags, properties_quality)
        schema.properties.sort(key=property_customs_ordinalPosition_sort)
        enhanced_schemas.append(schema)

    # ODCS building
    enhanced_schemas.sort(key=lambda s: f"{s.physicalType.lower()}/{s.name.lower()}")
    odcs.schema_ = enhanced_schemas

    return odcs


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
    authenticator_connect = (
        "externalbrowser"
        if password_connect is None
        else os.environ.get("DATACONTRACT_SNOWFLAKE_AUTHENTICATOR", "snowflake")
    )
    warehouse_connect = os.environ.get("DATACONTRACT_SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
    database_connect = databasename or "DEMO_DB"
    schema_connect = schema or "PUBLIC"
    snowflake_home = os.environ.get("DATACONTRACT_SNOWFLAKE_HOME") or os.environ.get("SNOWFLAKE_HOME")
    snowflake_connections_file = os.environ.get("DATACONTRACT_SNOWFLAKE_CONNECTIONS_FILE") or os.environ.get(
        "SNOWFLAKE_CONNECTIONS_FILE"
    )
    if not snowflake_connections_file and snowflake_home:
        snowflake_connections_file = os.path.join(snowflake_home, "connections.toml")

    default_connection = os.environ.get("DATACONTRACT_SNOWFLAKE_DEFAULT_CONNECTION_NAME") or os.environ.get(
        "SNOWFLAKE_DEFAULT_CONNECTION_NAME"
    )

    private_key_file = os.environ.get("DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_FILE") or os.environ.get(
        "SNOWFLAKE_PRIVATE_KEY_FILE"
    )
    private_key_file_pwd = os.environ.get("DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_FILE_PWD") or os.environ.get(
        "SNOWFLAKE_PRIVATE_KEY_FILE_PWD"
    )

    # build connection
    if default_connection is not None and password_connect is None:
        # use the default connection defined in the snowflake config file : connections.toml and config.toml

        # optional connection params (will override the defaults if set)
        connection_params = {}
        if default_connection:
            connection_params["connection_name"] = default_connection
        if snowflake_connections_file:
            connection_params["connections_file_path"] = Path(snowflake_connections_file)
        if role_connect:
            connection_params["role"] = role_connect
        if account_connect:
            connection_params["account"] = account_connect
        # don't override default connection with defaults set above
        if database_connect and database_connect != "DEMO_DB":
            connection_params["database"] = database_connect
        if schema_connect and schema_connect != "PUBLIC":
            connection_params["schema"] = schema_connect
        if warehouse_connect and warehouse_connect != "COMPUTE_WH":
            connection_params["warehouse"] = warehouse_connect

        conn = connect(
            session_parameters={
                "QUERY_TAG": "datacontract-cli import",
                "use_openssl_only": False,
            },
            **connection_params,
        )
    elif private_key_file is not None:
        # use private key auth
        if not os.path.exists(private_key_file):
            raise FileNotFoundError(f"Private key file not found at: {private_key_file}")

        conn = connect(
            user=user_connect,
            account=account_connect,
            private_key_file=private_key_file,
            private_key_file_pwd=private_key_file_pwd,
            session_parameters={
                "QUERY_TAG": "datacontract-cli import",
                "use_openssl_only": False,
            },
            warehouse=warehouse_connect,
            role=role_connect,
            database=database_connect,
            schema=schema_connect,
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
