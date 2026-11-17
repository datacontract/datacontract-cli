"""Run datacontract test against Dremio through its REST API.

ibis has no Dremio backend, so this module brings a small one. Its SQL comes
from ibis's Trino compiler rendered in sqlglot's Dremio dialect: both speak
ANSI SQL with double-quoted identifiers, and the dialect spells each function
the way Dremio does. Every statement runs as a Dremio job over the REST API
(``POST /api/v3/sql``, poll ``/api/v3/job/{id}``, page through its results),
the API on the port of the web console (9047), which a contract's Dremio server
names. It needs no driver beyond ``requests``.

A job runs in a context, the path of the space, source or folder its
unqualified table names resolve in. The connection pins the contract's
``schema`` as that context, so a table in a nested folder
(``sales.marts.daily``) is found by its name alone, the way other backends pin
their schema at connect time.
"""

from __future__ import annotations

import contextlib
import functools
import time
from typing import TYPE_CHECKING, Any, Iterator

import requests

if TYPE_CHECKING:
    import ibis.expr.datatypes as dt
    import ibis.expr.schema as sch

# The most rows Dremio returns in one page of job results.
RESULTS_PAGE_SIZE = 500


class DremioQueryError(Exception):
    """A Dremio job failed or was canceled; the message is Dremio's own."""


def split_path(path: str | None) -> list[str]:
    """The names of a Dremio path such as ``sales.marts`` or ``$scratch."bucket.v1".sub``.

    A period separates two names unless it is inside double quotes, which a name
    with a period of its own needs (an S3 bucket ``bucket.v1``). A doubled
    double quote inside quotes is one double quote.
    """
    if not path or not path.strip():
        return []
    names: list[str] = []
    current: list[str] = []
    quoted = False
    i = 0
    while i < len(path):
        char = path[i]
        if quoted:
            if char == '"' and i + 1 < len(path) and path[i + 1] == '"':
                current.append('"')
                i += 1
            elif char == '"':
                quoted = False
            else:
                current.append(char)
        elif char == '"':
            quoted = True
        elif char == ".":
            names.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        i += 1
    names.append("".join(current).strip())
    return [name for name in names if name]


class DremioRestClient:
    """Runs SQL as Dremio jobs: submit, wait until the job ends, read every page of its results.

    Signs in with a personal access token when one is given, else with the user
    name and password, whose session token it then sends with every request.
    """

    def __init__(
        self,
        base_url: str,
        *,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        context: list[str] | None = None,
        verify: bool = True,
        connect_timeout: float = 30,
        read_timeout: float = 300,
        poll_interval: float = 0.2,
        job_timeout: float = 3600,
        session: requests.Session | None = None,
    ) -> None:
        if not token and not (username and password):
            raise ValueError("Dremio needs a personal access token, or a user name and password")
        self.base_url = base_url.rstrip("/")
        self.context = list(context or [])
        self._username = username
        self._password = password
        self._token = token
        self._verify = verify
        self._timeout = (connect_timeout, read_timeout)
        self._poll_interval = poll_interval
        self._job_timeout = job_timeout
        self._session = session or requests.Session()
        self._authorization: str | None = None

    def authorization(self) -> str:
        if self._authorization is None:
            if self._token:
                self._authorization = f"Bearer {self._token}"
            else:
                response = self._session.post(
                    f"{self.base_url}/apiv2/login",
                    json={"userName": self._username, "password": self._password},
                    timeout=self._timeout,
                    verify=self._verify,
                )
                if not response.ok:
                    raise ConnectionError(
                        f"Dremio login failed (HTTP {response.status_code}): {_error_message(response)}"
                    )
                self._authorization = f"_dremio{response.json()['token']}"
        return self._authorization

    def run(self, sql: str) -> tuple[list[dict], list[dict]]:
        """The schema (``[{name, type}]``) and the rows (one dict each) of ``sql``'s results."""
        body: dict[str, Any] = {"sql": sql}
        if self.context:
            body["context"] = self.context
        job_id = self._request("POST", "/api/v3/sql", json=body)["id"]
        self._await(job_id)

        schema: list[dict] = []
        rows: list[dict] = []
        while True:
            page = self._request("GET", f"/api/v3/job/{job_id}/results?offset={len(rows)}&limit={RESULTS_PAGE_SIZE}")
            schema = schema or page.get("schema") or []
            page_rows = page.get("rows") or []
            rows.extend(page_rows)
            if not page_rows or len(rows) >= int(page.get("rowCount", len(rows))):
                return schema, rows

    def _await(self, job_id: str) -> None:
        deadline = time.monotonic() + self._job_timeout
        while True:
            job = self._request("GET", f"/api/v3/job/{job_id}")
            state = job.get("jobState")
            if state == "COMPLETED":
                return
            if state == "FAILED":
                raise DremioQueryError(job.get("errorMessage") or "Dremio query failed")
            if state == "CANCELED":
                raise DremioQueryError(job.get("cancellationReason") or "Dremio query was canceled")
            if time.monotonic() > deadline:
                # A job nobody waits for anymore would keep using the Dremio engine.
                with contextlib.suppress(Exception):
                    self._request("POST", f"/api/v3/job/{job_id}/cancel", expect_body=False)
                raise DremioQueryError(f"Dremio query {job_id} did not finish within {self._job_timeout:.0f} seconds")
            time.sleep(self._poll_interval)

    def _request(self, method: str, path: str, json: Any = None, expect_body: bool = True) -> dict:
        response = self._session.request(
            method,
            f"{self.base_url}{path}",
            json=json,
            headers={"Authorization": self.authorization()},
            timeout=self._timeout,
            verify=self._verify,
        )
        if not response.ok:
            raise DremioQueryError(f"Dremio API error (HTTP {response.status_code}): {_error_message(response)}")
        return response.json() if expect_body else {}

    def cursor(self) -> "DremioCursor":
        return DremioCursor(self)

    def close(self) -> None:
        self._session.close()


def _error_message(response: requests.Response) -> str:
    try:
        return response.json().get("errorMessage") or response.reason
    except ValueError:
        return response.text.strip()[:200] or response.reason


class DremioCursor:
    """The part of a DB-API cursor the check engine reads: ``execute``, ``fetchall``, ``description``."""

    def __init__(self, client: DremioRestClient) -> None:
        self._client = client
        self.schema: list[dict] = []
        self._rows: list[tuple] = []
        self.description: list[tuple] | None = None

    def execute(self, sql: str) -> "DremioCursor":
        self.schema, rows = self._client.run(sql)
        names = [column["name"] for column in self.schema]
        self.description = [(name, None, None, None, None, None, None) for name in names]
        self._rows = [tuple(row.get(name) for name in names) for row in rows]
        return self

    @property
    def rowcount(self) -> int:
        return len(self._rows)

    def fetchall(self) -> list[tuple]:
        rows, self._rows = self._rows, []
        return rows

    def fetchone(self) -> tuple | None:
        return self._rows.pop(0) if self._rows else None

    def close(self) -> None:
        self._rows = []


def ibis_type(column_type: dict | None) -> "dt.DataType":
    """The ibis type of a column type as Dremio's job results report it (``{"name": "DECIMAL", ...}``)."""
    import ibis.expr.datatypes as dt

    column_type = column_type or {}
    name = str(column_type.get("name") or "").upper()
    sub_schema = column_type.get("subSchema") or []
    simple = {
        "VARCHAR": dt.string,
        "CHAR": dt.string,
        "BOOLEAN": dt.boolean,
        "TINYINT": dt.int8,
        "SMALLINT": dt.int16,
        "INTEGER": dt.int32,
        "INT": dt.int32,
        "BIGINT": dt.int64,
        "FLOAT": dt.float32,
        "DOUBLE": dt.float64,
        "DATE": dt.date,
        "TIME": dt.time,
        "VARBINARY": dt.binary,
        "BINARY": dt.binary,
        "NULL": dt.null,
    }
    if name in simple:
        return simple[name]
    if name == "DECIMAL":
        return dt.Decimal(precision=column_type.get("precision"), scale=column_type.get("scale"))
    if name == "TIMESTAMP":
        # Dremio keeps milliseconds, and no time zone.
        return dt.Timestamp(scale=3)
    if name == "LIST" and sub_schema:
        return dt.Array(ibis_type(sub_schema[0].get("type")))
    if name == "STRUCT" and sub_schema:
        return dt.Struct({field.get("name"): ibis_type(field.get("type")) for field in sub_schema})
    if name == "MAP":
        key, value = _map_key_and_value(sub_schema)
        if key is not None:
            return dt.Map(ibis_type(key), ibis_type(value))
    if name.startswith("INTERVAL"):
        return dt.Interval("D") if "DAY" in name else dt.Interval("M")
    return dt.unknown


def _map_key_and_value(sub_schema: list[dict]) -> tuple[dict | None, dict | None]:
    """The key and value types of a map, which Dremio reports as one struct of ``key`` and ``value``."""
    entry = (sub_schema[0].get("type") or {}) if sub_schema else {}
    fields = {field.get("name"): field.get("type") for field in entry.get("subSchema") or []}
    if "key" not in fields:
        return None, None
    return fields["key"], fields.get("value")


def native_type(column_type: dict | None) -> str | None:
    """A column type as Dremio's job results report it, written as a contract's ``physicalType``:
    ``VARCHAR``, ``DECIMAL(10,2)``, ``ARRAY<VARCHAR>``, ``STRUCT<city VARCHAR>``, ``MAP<VARCHAR, INTEGER>``.

    Dremio keeps no length for a string, so ``VARCHAR`` has none.
    """
    column_type = column_type or {}
    name = str(column_type.get("name") or "").upper()
    if not name:
        return None
    sub_schema = column_type.get("subSchema") or []
    if name == "DECIMAL" and column_type.get("precision") is not None:
        return f"DECIMAL({column_type['precision']},{column_type.get('scale') or 0})"
    if name == "LIST" and sub_schema:
        return f"ARRAY<{native_type(sub_schema[0].get('type'))}>"
    if name == "STRUCT" and sub_schema:
        return (
            "STRUCT<" + ", ".join(f"{field.get('name')} {native_type(field.get('type'))}" for field in sub_schema) + ">"
        )
    if name == "MAP":
        key, value = _map_key_and_value(sub_schema)
        if key is not None:
            return f"MAP<{native_type(key)}, {native_type(value)}>"
    return name


def ibis_schema(columns: list[dict]) -> "sch.Schema":
    import ibis.expr.schema as sch

    return sch.Schema({column["name"]: ibis_type(column.get("type")) for column in columns})


@functools.cache
def _backend_class():
    """The ibis backend class, built on first use so that importing this module needs no ibis."""
    import sqlglot as sg
    import sqlglot.expressions as sge
    from ibis.backends import NoExampleLoader
    from ibis.backends.sql import SQLBackend
    from ibis.backends.sql.compilers.trino import TrinoCompiler
    from ibis.backends.sql.datatypes import SqlglotType
    from sqlglot.dialects.dremio import Dremio

    class DremioType(SqlglotType):
        dialect = "dremio"
        default_decimal_precision = 38
        default_decimal_scale = 0
        default_temporal_scale = 3

    class DremioCompiler(TrinoCompiler):
        __slots__ = ()
        dialect = Dremio
        type_mapper = DremioType

    class Backend(SQLBackend, NoExampleLoader):
        name = "dremio"
        compiler = DremioCompiler()
        supports_temporary_tables = False
        supports_python_udfs = False

        def do_connect(self, client: DremioRestClient) -> None:
            self.con = client

        @property
        def version(self) -> str:
            with self._safe_raw_sql("SELECT version FROM sys.version") as cursor:
                row = cursor.fetchone()
            return str(row[0]) if row else ""

        def raw_sql(self, query: str | sge.Expression, **kwargs: Any) -> DremioCursor:
            with contextlib.suppress(AttributeError):
                query = query.sql(dialect=self.dialect)
            return self.con.cursor().execute(query)

        @contextlib.contextmanager
        def _safe_raw_sql(self, query: str | sge.Expression, **kwargs: Any) -> Iterator[DremioCursor]:
            cursor = self.raw_sql(query, **kwargs)
            try:
                yield cursor
            finally:
                cursor.close()

        def get_schema(self, table_name: str, *, catalog: str | None = None, database: str | None = None):
            table = sg.table(table_name, db=database, catalog=catalog, quoted=True).sql(self.dialect)
            return self._get_schema_using_query(f"SELECT * FROM {table}")

        def _get_schema_using_query(self, query: str):
            # A job that returns no rows still reports the types of its columns.
            with self._safe_raw_sql(f"SELECT * FROM ({query}) AS t LIMIT 0") as cursor:
                return ibis_schema(cursor.schema)

        def list_tables(self, *, like: str | None = None, database: str | None = None) -> list[str]:
            path = split_path(database) if database else self.con.context
            # INFORMATION_SCHEMA writes a path's names joined by periods, unquoted.
            schema = ".".join(path).replace("'", "''")
            with self._safe_raw_sql(
                f"SELECT TABLE_NAME FROM INFORMATION_SCHEMA.\"TABLES\" WHERE TABLE_SCHEMA = '{schema}'"
            ) as cursor:
                tables = [row[0] for row in cursor.fetchall()]
            return self._filter_with_like(tables, like=like)

        def _fetch_from_cursor(self, cursor: DremioCursor, schema):
            import pandas as pd
            from ibis.formats.pandas import PandasData

            df = pd.DataFrame.from_records(cursor.fetchall(), columns=schema.names, coerce_float=True)
            return PandasData.convert_table(df, schema)

        def execute(self, expr, /, *, params=None, limit=None, **kwargs: Any):
            self._run_pre_execute_hooks(expr)
            table = expr.as_table()
            sql = self.compile(table, params=params, limit=limit, **kwargs)
            schema = table.schema()
            with self._safe_raw_sql(sql) as cursor:
                result = self._fetch_from_cursor(cursor, schema)
            return expr.__pandas_result__(result)

        def _register_in_memory_table(self, op) -> None:
            raise NotImplementedError("datacontract test does not create tables on Dremio")

        def create_table(self, *args: Any, **kwargs: Any):
            raise NotImplementedError("datacontract test does not create tables on Dremio")

        def disconnect(self) -> None:
            self.con.close()

    return Backend


def connect(client: DremioRestClient):
    """An ibis backend that runs its queries on Dremio through ``client``."""
    backend = _backend_class()()
    backend._can_reconnect = False
    backend.do_connect(client)
    return backend
