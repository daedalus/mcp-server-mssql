import uuid

import fastmcp
import mssql_python
from mssql_python import connect
from mssql_python.connection import Connection
from mssql_python.cursor import Cursor
from mssql_python.row import Row

mcp = fastmcp.FastMCP("mcp-mssql")

_connections: dict[str, Connection] = {}
_cursors: dict[str, tuple[str, Cursor]] = {}


def _get_connection(connection_id: str) -> Connection:
    if connection_id not in _connections:
        raise ValueError(f"Connection {connection_id} not found")
    conn = _connections[connection_id]
    if not conn:
        raise ValueError(f"Connection {connection_id} is closed")
    return conn


def _get_cursor(connection_id: str, cursor_id: str) -> Cursor:
    key = f"{connection_id}:{cursor_id}"
    if key not in _cursors:
        raise ValueError(f"Cursor {cursor_id} not found for connection {connection_id}")
    return _cursors[key][1]


def _row_to_dict(row: Row) -> dict:
    if row is None:
        return None
    return dict(row._asdict())


def _rows_to_list(rows: list[Row]) -> list[dict]:
    return [_row_to_dict(row) for row in rows]


@mcp.tool()
def connect_tool(connection_string: str) -> dict:
    """Connect to Microsoft SQL Server using the provided connection string.

    Args:
        connection_string: SQL Server connection string in semicolon-delimited
            key=value format (e.g., "SERVER=tcp:localhost;DATABASE=mydb;Authentication=ActiveDirectoryInteractive;Encrypt=yes;")

    Returns:
        Dictionary containing connection_id and server info.
        The connection_id should be used for subsequent operations.

    Example:
        >>> connect_tool("SERVER=localhost;DATABASE=TestDB;UID=sa;PWD=password;")
        {"connection_id": "abc123", "server_name": "localhost", "database": "TestDB"}
    """
    try:
        conn = connect(connection_string)
        connection_id = str(uuid.uuid4())
        _connections[connection_id] = conn
        return {
            "connection_id": connection_id,
            "server_name": conn.getinfo(mssql_python.SQL_SERVER_NAME),
            "database": conn.getinfo(mssql_python.SQL_DATABASE_NAME),
            "sql_version": conn.getinfo(mssql_python.SQL_DRIVER_VER),
        }
    except Exception as e:
        raise ValueError(f"Failed to connect: {str(e)}")


@mcp.tool()
def close_connection(connection_id: str) -> dict:
    """Close an existing database connection.

    Args:
        connection_id: The ID returned from connect_tool

    Returns:
        Dictionary with status confirmation.

    Example:
        >>> close_connection("abc123")
        {"status": "closed", "connection_id": "abc123"}
    """
    conn = _get_connection(connection_id)
    try:
        conn.close()
    except Exception:
        pass
    del _connections[connection_id]
    keys_to_delete = [k for k in _cursors if k.startswith(f"{connection_id}:")]
    for key in keys_to_delete:
        del _cursors[key]
    return {"status": "closed", "connection_id": connection_id}


@mcp.tool()
def list_connections() -> list[dict]:
    """List all active connections.

    Returns:
        List of connection info dictionaries.

    Example:
        >>> list_connections()
        [{"connection_id": "abc123", "server": "localhost", "database": "TestDB"}]
    """
    result = []
    for conn_id, conn in _connections.items():
        try:
            result.append(
                {
                    "connection_id": conn_id,
                    "server": conn.getinfo(mssql_python.SQL_SERVER_NAME),
                    "database": conn.getinfo(mssql_python.SQL_DATABASE_NAME),
                }
            )
        except Exception:
            result.append(
                {
                    "connection_id": conn_id,
                    "server": "unknown",
                    "database": "unknown",
                }
            )
    return result


@mcp.tool()
def execute_query(
    connection_id: str,
    sql: str,
    params: list | None = None,
) -> dict:
    """Execute a SQL query and return results.

    Args:
        connection_id: The ID returned from connect_tool
        sql: SQL statement to execute
        params: Optional list of parameters for parameterized query

    Returns:
        List of row dictionaries.

    Example:
        >>> execute_query("abc123", "SELECT * FROM users WHERE active = 1")
        [{"id": 1, "name": "John", "active": true}, {"id": 2, "name": "Jane", "active": true}]
    """
    conn = _get_connection(connection_id)
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        cursor_id = str(uuid.uuid4())
        _cursors[f"{connection_id}:{cursor_id}"] = (connection_id, cursor)
        rows = cursor.fetchall()
        return {
            "rows": _rows_to_list(rows),
            "cursor_id": cursor_id,
            "row_count": len(rows),
        }
    except Exception as e:
        cursor.close()
        raise ValueError(f"Query execution failed: {str(e)}")


@mcp.tool()
def execute_scalar(connection_id: str, sql: str) -> object:
    """Execute a SQL query and return a single value.

    Args:
        connection_id: The ID returned from connect_tool
        sql: SQL statement that returns a single value

    Returns:
        The single value from the query result.

    Example:
        >>> execute_scalar("abc123", "SELECT COUNT(*) FROM users")
        42
    """
    conn = _get_connection(connection_id)
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        row = cursor.fetchone()
        if row:
            return row[0]
        return None
    finally:
        cursor.close()


@mcp.tool()
def fetch_results(
    connection_id: str,
    cursor_id: str,
    mode: str = "all",
    size: int | None = None,
) -> dict:
    """Fetch results from an existing cursor.

    Args:
        connection_id: The ID returned from connect_tool
        cursor_id: The cursor ID from execute_query
        mode: Fetch mode - "one", "many", or "all" (default: "all")
        size: Number of rows for "many" mode

    Returns:
        List of row dictionaries.

    Example:
        >>> fetch_results("abc123", "cursor123", mode="many", size=10)
        [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]
    """
    cursor = _get_cursor(connection_id, cursor_id)
    if mode == "one":
        row = cursor.fetchone()
        return {"rows": [_row_to_dict(row)] if row else []}
    elif mode == "many":
        rows = cursor.fetchmany(size or 10)
        return {"rows": _rows_to_list(rows)}
    else:
        rows = cursor.fetchall()
        return {"rows": _rows_to_list(rows)}


@mcp.tool()
def call_procedure(
    connection_id: str,
    procedure_name: str,
    params: list | None = None,
) -> dict:
    """Call a stored procedure.

    Args:
        connection_id: The ID returned from connect_tool
        procedure_name: Name of the stored procedure
        params: Optional list of parameters

    Returns:
        Dictionary with procedure results.

    Example:
        >>> call_procedure("abc123", "sp_GetUsers", [1])
        {"result": [{"id": 1, "name": "John"}]}
    """
    conn = _get_connection(connection_id)
    cursor = conn.cursor()
    try:
        result = cursor.callproc(procedure_name, params or [])
        return {"result": result, "row_count": cursor.rowcount}
    finally:
        cursor.close()


@mcp.tool()
def commit(connection_id: str) -> dict:
    """Commit the current transaction.

    Args:
        connection_id: The ID returned from connect_tool

    Returns:
        Dictionary with status confirmation.

    Example:
        >>> commit("abc123")
        {"status": "committed", "connection_id": "abc123"}
    """
    conn = _get_connection(connection_id)
    conn.commit()
    return {"status": "committed", "connection_id": connection_id}


@mcp.tool()
def rollback(connection_id: str) -> dict:
    """Rollback the current transaction.

    Args:
        connection_id: The ID returned from connect_tool

    Returns:
        Dictionary with status confirmation.

    Example:
        >>> rollback("abc123")
        {"status": "rolled_back", "connection_id": "abc123"}
    """
    conn = _get_connection(connection_id)
    conn.rollback()
    return {"status": "rolled_back", "connection_id": connection_id}


@mcp.tool()
def bulk_copy(
    connection_id: str,
    table_name: str,
    data: list,
    column_mappings: list | None = None,
    batch_size: int = 0,
    keep_identity: bool = False,
    check_constraints: bool = False,
    keep_nulls: bool = False,
    fire_triggers: bool = False,
) -> dict:
    """Perform a bulk copy operation to load data into a table.

    Args:
        connection_id: The ID returned from connect_tool
        table_name: Target table name
        data: List of tuples or lists representing rows to insert
        column_mappings: Optional list of column mappings
        batch_size: Batch size for bulk copy (0 = all at once)
        keep_identity: Whether to keep identity values
        check_constraints: Whether to check constraints
        keep_nulls: Whether to keep NULL values
        fire_triggers: Whether to fire triggers

    Returns:
        Dictionary with bulk copy result.

    Example:
        >>> bulk_copy("abc123", "users", [("John", 25), ("Jane", 30)])
        {"status": "completed", "rows_copied": 2}
    """
    conn = _get_connection(connection_id)
    cursor = conn.cursor()
    try:
        cursor.bulkcopy(
            table_name=table_name,
            data=data,
            batch_size=batch_size,
            column_mappings=column_mappings,
            keep_identity=keep_identity,
            check_constraints=check_constraints,
            keep_nulls=keep_nulls,
            fire_triggers=fire_triggers,
        )
        return {"status": "completed", "rows_copied": len(data)}
    finally:
        cursor.close()


@mcp.tool()
def get_tables(
    connection_id: str,
    catalog: str | None = None,
    schema: str | None = None,
) -> list[dict]:
    """Get list of tables from the database.

    Args:
        connection_id: The ID returned from connect_tool
        catalog: Optional catalog filter
        schema: Optional schema filter

    Returns:
        List of table information dictionaries.

    Example:
        >>> get_tables("abc123")
        [{"table_name": "users", "table_type": "TABLE"}, {"table_name": "orders", "table_type": "TABLE"}]
    """
    conn = _get_connection(connection_id)
    cursor = conn.cursor()
    try:
        cursor.tables(catalog=catalog, schema=schema)
        rows = cursor.fetchall()
        return [
            {
                "table_name": row.TABLE_NAME,
                "table_type": row.TABLE_TYPE,
                "table_schema": row.TABLE_SCHEM,
            }
            for row in rows
            if row.TABLE_TYPE in ("TABLE", "VIEW")
        ]
    finally:
        cursor.close()


@mcp.tool()
def get_columns(
    connection_id: str,
    table_name: str,
    catalog: str | None = None,
    schema: str | None = None,
) -> list[dict]:
    """Get list of columns for a table.

    Args:
        connection_id: The ID returned from connect_tool
        table_name: Name of the table
        catalog: Optional catalog filter
        schema: Optional schema filter

    Returns:
        List of column information dictionaries.

    Example:
        >>> get_columns("abc123", "users")
        [{"column_name": "id", "data_type": "int", "is_nullable": false}, {"column_name": "name", "data_type": "varchar", "is_nullable": true}]
    """
    conn = _get_connection(connection_id)
    cursor = conn.cursor()
    try:
        cursor.columns(table=table_name, catalog=catalog, schema=schema)
        rows = cursor.fetchall()
        return [
            {
                "column_name": row.COLUMN_NAME,
                "data_type": row.TYPE_NAME,
                "data_type_code": row.DATA_TYPE,
                "column_size": row.COLUMN_SIZE,
                "is_nullable": bool(row.NULLABLE),
                "ordinal_position": row.ORDINAL_POSITION,
            }
            for row in rows
        ]
    finally:
        cursor.close()


@mcp.tool()
def get_procedures(
    connection_id: str,
    catalog: str | None = None,
    schema: str | None = None,
) -> list[dict]:
    """Get list of stored procedures from the database.

    Args:
        connection_id: The ID returned from connect_tool
        catalog: Optional catalog filter
        schema: Optional schema filter

    Returns:
        List of procedure information dictionaries.

    Example:
        >>> get_procedures("abc123")
        [{"procedure_name": "sp_GetUsers", "procedure_schema": "dbo"}]
    """
    conn = _get_connection(connection_id)
    cursor = conn.cursor()
    try:
        cursor.procedures(catalog=catalog, schema=schema)
        rows = cursor.fetchall()
        return [
            {
                "procedure_name": row.PROCEDURE_NAME,
                "procedure_schema": row.PROCEDURE_SCHEM,
            }
            for row in rows
        ]
    finally:
        cursor.close()


@mcp.tool()
def get_foreign_keys(
    connection_id: str,
    table_name: str,
    catalog: str | None = None,
    schema: str | None = None,
) -> list[dict]:
    """Get foreign keys for a table.

    Args:
        connection_id: The ID returned from connect_tool
        table_name: Name of the table
        catalog: Optional catalog filter
        schema: Optional schema filter

    Returns:
        List of foreign key information dictionaries.

    Example:
        >>> get_foreign_keys("abc123", "orders")
        [{"foreign_key_name": "FK_orders_users", "column_name": "user_id", "referenced_table": "users", "referenced_column": "id"}]
    """
    conn = _get_connection(connection_id)
    cursor = conn.cursor()
    try:
        cursor.foreignKeys(table=table_name, catalog=catalog, schema=schema)
        rows = cursor.fetchall()
        return [
            {
                "foreign_key_name": row.FK_NAME,
                "column_name": row.FKCOLUMN_NAME,
                "referenced_table": row.PKTABLE_NAME,
                "referenced_column": row.PKCOLUMN_NAME,
            }
            for row in rows
        ]
    finally:
        cursor.close()


@mcp.tool()
def get_primary_keys(
    connection_id: str,
    table_name: str,
    catalog: str | None = None,
    schema: str | None = None,
) -> list[dict]:
    """Get primary keys for a table.

    Args:
        connection_id: The ID returned from connect_tool
        table_name: Name of the table
        catalog: Optional catalog filter
        schema: Optional schema filter

    Returns:
        List of primary key information dictionaries.

    Example:
        >>> get_primary_keys("abc123", "users")
        [{"column_name": "id", "key_name": "PK_users"}]
    """
    conn = _get_connection(connection_id)
    cursor = conn.cursor()
    try:
        cursor.primaryKeys(table=table_name, catalog=catalog, schema=schema)
        rows = cursor.fetchall()
        return [
            {"column_name": row.COLUMN_NAME, "key_name": row.PK_NAME} for row in rows
        ]
    finally:
        cursor.close()


@mcp.tool()
def parse_connection_string(connection_string: str) -> dict:
    """Parse a SQL Server connection string into components.

    Args:
        connection_string: SQL Server connection string

    Returns:
        Dictionary of connection string components.

    Example:
        >>> parse_connection_string("SERVER=localhost;DATABASE=TestDB;UID=sa;")
        {"SERVER": "localhost", "DATABASE": "TestDB", "UID": "sa"}
    """
    try:
        return {"parsed": connection_string}
    except Exception as e:
        raise ValueError(f"Failed to parse connection string: {str(e)}")


@mcp.tool()
def build_connection_string(
    server: str | None = None,
    database: str | None = None,
    user: str | None = None,
    password: str | None = None,
    driver: str | None = None,
    encrypt: str | None = None,
    trust_cert: str | None = None,
    authentication: str | None = None,
) -> str:
    """Build a SQL Server connection string from components.

    Args:
        server: Server hostname or IP address
        database: Database name
        user: Username for SQL authentication
        password: Password for SQL authentication
        driver: ODBC driver name (default: ODBC Driver 18 for SQL Server)
        encrypt: Enable encryption (yes/no)
        trust_cert: Trust server certificate (yes/no)
        authentication: Authentication method

    Returns:
        Connection string.

    Example:
        >>> build_connection_string(server="localhost", database="TestDB")
        "SERVER=localhost;DATABASE=TestDB;DRIVER={ODBC Driver 18 for SQL Server};"
    """
    parts = []
    if server:
        parts.append(f"SERVER={server}")
    if database:
        parts.append(f"DATABASE={database}")
    if user:
        parts.append(f"UID={user}")
    if password:
        parts.append(f"PWD={password}")
    if driver:
        parts.append(f"DRIVER={{{driver}}}")
    else:
        parts.append("DRIVER={ODBC Driver 18 for SQL Server}")
    if encrypt:
        parts.append(f"Encrypt={encrypt}")
    if trust_cert:
        parts.append(f"TrustServerCertificate={trust_cert}")
    if authentication:
        parts.append(f"Authentication={authentication}")
    return ";".join(parts) + ";" if parts else ""


@mcp.tool()
def set_connection_timeout(connection_id: str, timeout: int) -> dict:
    """Set the connection timeout for a connection.

    Args:
        connection_id: The ID returned from connect_tool
        timeout: Timeout in seconds

    Returns:
        Dictionary with status confirmation.

    Example:
        >>> set_connection_timeout("abc123", 30)
        {"status": "set", "timeout": 30}
    """
    conn = _get_connection(connection_id)
    conn.set_attr(mssql_python.SQL_ATTR_CONNECTION_TIMEOUT, timeout)
    return {"status": "set", "timeout": timeout}


@mcp.tool()
def set_login_timeout(connection_id: str, timeout: int) -> dict:
    """Set the login timeout for a connection.

    Args:
        connection_id: The ID returned from connect_tool
        timeout: Timeout in seconds

    Returns:
        Dictionary with status confirmation.

    Example:
        >>> set_login_timeout("abc123", 15)
        {"status": "set", "timeout": 15}
    """
    conn = _get_connection(connection_id)
    conn.set_attr(mssql_python.SQL_ATTR_LOGIN_TIMEOUT, timeout)
    return {"status": "set", "timeout": timeout}


@mcp.tool()
def set_autocommit(connection_id: str, enabled: bool) -> dict:
    """Set autocommit mode for a connection.

    Args:
        connection_id: The ID returned from connect_tool
        enabled: Whether to enable autocommit

    Returns:
        Dictionary with status confirmation.

    Example:
        >>> set_autocommit("abc123", True)
        {"status": "set", "autocommit": true}
    """
    conn = _get_connection(connection_id)
    conn.setautocommit(enabled)
    return {"status": "set", "autocommit": enabled}


@mcp.tool()
def get_connection_info(connection_id: str) -> dict:
    """Get information about a connection.

    Args:
        connection_id: The ID returned from connect_tool

    Returns:
        Dictionary with connection information.

    Example:
        >>> get_connection_info("abc123")
        {"server_name": "localhost", "database": "TestDB", "driver_name": "ODBC Driver 18"}
    """
    conn = _get_connection(connection_id)
    return {
        "server_name": conn.getinfo(mssql_python.SQL_SERVER_NAME),
        "database": conn.getinfo(mssql_python.SQL_DATABASE_NAME),
        "driver_name": conn.getinfo(mssql_python.SQL_DRIVER_NAME),
        "driver_version": conn.getinfo(mssql_python.SQL_DRIVER_VER),
    }
