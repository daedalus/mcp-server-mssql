# mcp-server-mssql

MCP server for Microsoft SQL Server using mssql-python.

[![PyPI](https://img.shields.io/pypi/v/mcp-server-mssql.svg)](https://pypi.org/project/mcp-server-mssql/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-server-mssql.svg)](https://pypi.org/project/mcp-server-mssql/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

mcp-name: io.github.daedalus/mcp-server-mssql

## Install

```bash
pip install mcp-server-mssql
```

## Usage

### Run as MCP Server

```bash
mcp-server-mssql
```

### Configure in Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcp-server-mssql": {
      "command": "mcp-server-mssql"
    }
  }
}
```

## Available Tools

- `connect_tool` - Connect to Microsoft SQL Server
- `close_connection` - Close an existing connection
- `list_connections` - List all active connections
- `execute_query` - Execute SQL query and return results
- `execute_scalar` - Execute SQL and return single value
- `fetch_results` - Fetch results from a cursor
- `call_procedure` - Call a stored procedure
- `commit` - Commit current transaction
- `rollback` - Rollback current transaction
- `bulk_copy` - Perform bulk copy operation
- `get_tables` - List database tables
- `get_columns` - List table columns
- `get_procedures` - List stored procedures
- `get_foreign_keys` - List foreign keys
- `get_primary_keys` - List primary keys
- `parse_connection_string` - Parse connection string
- `build_connection_string` - Build connection string
- `set_connection_timeout` - Set connection timeout
- `set_login_timeout` - Set login timeout
- `set_autocommit` - Set autocommit mode
- `get_connection_info` - Get connection information

## Development

```bash
git clone https://github.com/daedalus/mcp-server-mssql.git
cd mcp-server-mssql
pip install -e ".[test]"

# run tests
pytest

# format
ruff format src/ tests/

# lint
ruff check src/ tests/

# type check
mypy src/
```
