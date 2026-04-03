from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_connection():
    conn = MagicMock()
    conn.getinfo.return_value = "localhost"
    conn.cursor.return_value = MagicMock()
    return conn


@pytest.fixture
def mock_cursor():
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    cursor.fetchone.return_value = None
    cursor.fetchmany.return_value = []
    return cursor


@pytest.fixture
def mock_mssql_connect(mock_connection):
    with patch("mcp_server_mssql.server.connect", return_value=mock_connection) as mock:
        yield mock


@pytest.fixture
def mock_mssql_python():
    with patch("mcp_server_mssql.server.mssql_python") as mock:
        mock.SQL_SERVER_NAME = 123
        mock.SQL_DATABASE_NAME = 124
        mock.SQL_DRIVER_NAME = 125
        mock.SQL_DRIVER_VER = 126
        mock.SQL_ATTR_CONNECTION_TIMEOUT = 127
        mock.SQL_ATTR_LOGIN_TIMEOUT = 128
        yield mock
