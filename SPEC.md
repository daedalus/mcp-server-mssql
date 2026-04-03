# SPEC.md — mcp-mssql

## Purpose

An MCP (Model Context Protocol) server that exposes the full functionality of the mssql-python library (Microsoft's Python driver for SQL Server) as MCP tools and resources. This allows AI assistants to interact with Microsoft SQL Server databases through a standardized protocol.

## Scope

### In Scope
- Connection management (connect, disconnect, connection pooling settings)
- Query execution (execute, fetchone, fetchall, fetchmany)
- Stored procedure execution (callproc)
- Transaction management (commit, rollback)
- Bulk copy operations for high-performance data loading
- Database metadata retrieval (tables, columns, procedures, foreign keys, etc.)
- Connection string parsing and building
- Output type converters and encoding settings

### Not Scope
- GUI or web interface
- Database administration tasks (backup, restore, user management)
- Advanced SQL parsing or query optimization

## Public API / Interface

### MCP Tools

#### Connection Management
- `connect(connection_string: str) -> dict` - Establish a connection to SQL Server
- `close_connection(connection_id: str) -> dict` - Close an existing connection
- `list_connections() -> list` - List all active connections

#### Query Execution
- `execute_query(connection_id: str, sql: str, params: Optional[List] = None) -> list` - Execute SQL and return results
- `execute_scalar(connection_id: str, sql: str) -> Any` - Execute SQL and return single value
- `fetch_results(connection_id: str, cursor_id: str, mode: str = "all", size: int = None) -> list` - Fetch results from cursor

#### Stored Procedures
- `call_procedure(connection_id: str, procedure_name: str, params: Optional[List] = None) -> Any` - Call a stored procedure

#### Transaction Management
- `commit(connection_id: str) -> dict` - Commit current transaction
- `rollback(connection_id: str) -> dict` - Rollback current transaction

#### Bulk Copy
- `bulk_copy(connection_id: str, table_name: str, data: List, column_mappings: Optional[List] = None, batch_size: int = 0) -> dict` - Perform bulk copy operation

#### Metadata
- `get_tables(connection_id: str, catalog: Optional[str] = None, schema: Optional[str] = None) -> list` - List tables
- `get_columns(connection_id: str, table_name: str, catalog: Optional[str] = None, schema: Optional[str] = None) -> list` - List columns for a table
- `get_procedures(connection_id: str, catalog: Optional[str] = None, schema: Optional[str] = None) -> list` - List stored procedures
- `get_foreign_keys(connection_id: str, table_name: str, catalog: Optional[str] = None, schema: Optional[str] = None) -> list` - List foreign keys
- `get_primary_keys(connection_id: str, table_name: str, catalog: Optional[str] = None, schema: Optional[str] = None) -> list` - List primary keys

#### Connection String Utilities
- `parse_connection_string(connection_string: str) -> dict` - Parse connection string into components
- `build_connection_string(**kwargs) -> str` - Build connection string from components

### MCP Resources
- `connection://config` - Resource to get/set connection configuration
- `schema://{catalog}/{schema}` - Dynamic schema introspection

### Connection Settings
- `set_connection_timeout(connection_id: str, timeout: int)` - Set connection timeout
- `set_login_timeout(connection_id: str, timeout: int)` - Set login timeout
- `set_autocommit(connection_id: str, enabled: bool)` - Set autocommit mode
- `get_connection_info(connection_id: str)` - Get connection metadata

## Data Formats

### Connection String Format
Standard SQL Server connection string (semicolon-delimited key=value pairs):
```
SERVER=hostname;DATABASE=dbname;Authentication=ActiveDirectoryInteractive;Encrypt=yes;
```

### Query Results
Results are returned as lists of dictionaries (Row objects with column names as keys):
```json
[{"column1": "value1", "column2": 123}, {"column1": "value2", "column2": 456}]
```

### Error Responses
All errors return a dictionary with error details:
```json
{"error": "Error message", "code": "ERROR_CODE"}
```

## Edge Cases

1. **Invalid connection string** - Raise ConnectionStringParseError with details
2. **Connection timeout** - Return error with timeout details
3. **SQL syntax errors** - Return DatabaseError with SQL state and message
4. **Empty result sets** - Return empty list (not null)
5. **Transaction in progress** - Handle commit/rollback on active transaction
6. **Bulk copy with mismatched columns** - Raise error with column mismatch details
7. **Disconnected connection** - Detect and remove from active connections
8. **Concurrent connection attempts** - Handle thread-safely

## Performance & Constraints

- Connection pooling is enabled by default (handled by mssql-python)
- Cursor results are fetched client-side (memory considerations for large datasets)
- Bulk copy uses batch sizes for large data loads
- All operations should complete within reasonable timeouts
