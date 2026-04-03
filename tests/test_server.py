from unittest.mock import MagicMock, patch

import pytest

from mcp_server_mssql import server


class TestConnectTool:
    def test_connect_success(self, mock_mssql_connect, mock_mssql_python):
        result = server.connect_tool("SERVER=localhost;DATABASE=test;")

        assert "connection_id" in result
        assert result["server_name"] == "localhost"
        mock_mssql_connect.assert_called_once_with("SERVER=localhost;DATABASE=test;")

    def test_connect_failure(self):
        with patch(
            "mcp_server_mssql.server.connect",
            side_effect=Exception("Connection failed"),
        ):
            with pytest.raises(ValueError, match="Failed to connect"):
                server.connect_tool("SERVER=localhost;DATABASE=test;")


class TestCloseConnection:
    def test_close_success(self, mock_connection, mock_mssql_python):
        with patch.object(server, "_connections", {"test-id": mock_connection}):
            result = server.close_connection("test-id")

            assert result["status"] == "closed"
            assert result["connection_id"] == "test-id"
            mock_connection.close.assert_called_once()

    def test_close_not_found(self):
        with patch.object(server, "_connections", {}):
            with pytest.raises(ValueError, match="Connection .* not found"):
                server.close_connection("nonexistent")


class TestListConnections:
    def test_list_empty(self):
        with patch.object(server, "_connections", {}):
            result = server.list_connections()
            assert result == []

    def test_list_with_connections(self, mock_connection, mock_mssql_python):
        with patch.object(server, "_connections", {"id1": mock_connection}):
            result = server.list_connections()

            assert len(result) == 1
            assert result[0]["connection_id"] == "id1"


class TestExecuteQuery:
    def test_execute_with_results(
        self, mock_connection, mock_cursor, mock_mssql_python
    ):
        mock_row = MagicMock()
        mock_row._asdict.return_value = {"id": 1, "name": "John"}
        mock_cursor.fetchall.return_value = [mock_row]
        mock_connection.cursor.return_value = mock_cursor

        with patch.object(server, "_connections", {"test-id": mock_connection}):
            result = server.execute_query("test-id", "SELECT * FROM users")

            assert "rows" in result
            assert "cursor_id" in result
            assert result["row_count"] == 1

    def test_execute_with_params(self, mock_connection, mock_cursor, mock_mssql_python):
        mock_connection.cursor.return_value = mock_cursor

        with patch.object(server, "_connections", {"test-id": mock_connection}):
            server.execute_query("test-id", "SELECT * FROM users WHERE id = ?", [1])

            mock_cursor.execute.assert_called_once_with(
                "SELECT * FROM users WHERE id = ?", [1]
            )


class TestExecuteScalar:
    def test_execute_scalar_with_value(
        self, mock_connection, mock_cursor, mock_mssql_python
    ):
        mock_cursor.fetchone.return_value = (42,)
        mock_connection.cursor.return_value = mock_cursor

        with patch.object(server, "_connections", {"test-id": mock_connection}):
            result = server.execute_scalar("test-id", "SELECT COUNT(*) FROM users")

            assert result == 42

    def test_execute_scalar_no_rows(
        self, mock_connection, mock_cursor, mock_mssql_python
    ):
        mock_cursor.fetchone.return_value = None
        mock_connection.cursor.return_value = mock_cursor

        with patch.object(server, "_connections", {"test-id": mock_connection}):
            result = server.execute_scalar("test-id", "SELECT COUNT(*) FROM users")

            assert result is None


class TestFetchResults:
    def test_fetch_all(self, mock_connection, mock_cursor, mock_mssql_python):
        mock_row = MagicMock()
        mock_row._asdict.return_value = {"id": 1}
        mock_cursor.fetchall.return_value = [mock_row]

        with patch.object(server, "_connections", {"test-id": mock_connection}):
            with patch.object(
                server, "_cursors", {"test-id:cursor-id": ("test-id", mock_cursor)}
            ):
                result = server.fetch_results("test-id", "cursor-id", mode="all")

                assert len(result) == 1

    def test_fetch_one(self, mock_connection, mock_cursor, mock_mssql_python):
        mock_row = MagicMock()
        mock_row._asdict.return_value = {"id": 1}
        mock_cursor.fetchone.return_value = mock_row

        with patch.object(server, "_connections", {"test-id": mock_connection}):
            with patch.object(
                server, "_cursors", {"test-id:cursor-id": ("test-id", mock_cursor)}
            ):
                result = server.fetch_results("test-id", "cursor-id", mode="one")

                assert result == {"rows": [{"id": 1}]}

    def test_fetch_many(self, mock_connection, mock_cursor, mock_mssql_python):
        mock_row = MagicMock()
        mock_row._asdict.return_value = {"id": 1}
        mock_cursor.fetchmany.return_value = [mock_row]

        with patch.object(server, "_connections", {"test-id": mock_connection}):
            with patch.object(
                server, "_cursors", {"test-id:cursor-id": ("test-id", mock_cursor)}
            ):
                result = server.fetch_results(
                    "test-id", "cursor-id", mode="many", size=10
                )

                assert len(result) == 1


class TestCallProcedure:
    def test_call_procedure(self, mock_connection, mock_cursor, mock_mssql_python):
        mock_cursor.callproc.return_value = [1, "result"]
        mock_cursor.rowcount = 1
        mock_connection.cursor.return_value = mock_cursor

        with patch.object(server, "_connections", {"test-id": mock_connection}):
            result = server.call_procedure("test-id", "sp_Test", [1])

            assert "result" in result
            assert result["row_count"] == 1


class TestCommit:
    def test_commit_success(self, mock_connection, mock_mssql_python):
        with patch.object(server, "_connections", {"test-id": mock_connection}):
            result = server.commit("test-id")

            assert result["status"] == "committed"
            mock_connection.commit.assert_called_once()


class TestRollback:
    def test_rollback_success(self, mock_connection, mock_mssql_python):
        with patch.object(server, "_connections", {"test-id": mock_connection}):
            result = server.rollback("test-id")

            assert result["status"] == "rolled_back"
            mock_connection.rollback.assert_called_once()


class TestBulkCopy:
    def test_bulk_copy(self, mock_connection, mock_cursor, mock_mssql_python):
        mock_connection.cursor.return_value = mock_cursor

        with patch.object(server, "_connections", {"test-id": mock_connection}):
            result = server.bulk_copy("test-id", "users", [("John", 25), ("Jane", 30)])

            assert result["status"] == "completed"
            assert result["rows_copied"] == 2


class TestGetTables:
    def test_get_tables(self, mock_connection, mock_cursor, mock_mssql_python):
        mock_row = MagicMock()
        mock_row.TABLE_NAME = "users"
        mock_row.TABLE_TYPE = "TABLE"
        mock_row.TABLE_SCHEM = "dbo"
        mock_cursor.fetchall.return_value = [mock_row]
        mock_connection.cursor.return_value = mock_cursor

        with patch.object(server, "_connections", {"test-id": mock_connection}):
            result = server.get_tables("test-id")

            assert len(result) == 1
            assert result[0]["table_name"] == "users"


class TestGetColumns:
    def test_get_columns(self, mock_connection, mock_cursor, mock_mssql_python):
        mock_row = MagicMock()
        mock_row.COLUMN_NAME = "id"
        mock_row.TYPE_NAME = "int"
        mock_row.DATA_TYPE = 4
        mock_row.COLUMN_SIZE = 10
        mock_row.NULLABLE = 0
        mock_row.ORDINAL_POSITION = 1
        mock_cursor.fetchall.return_value = [mock_row]
        mock_connection.cursor.return_value = mock_cursor

        with patch.object(server, "_connections", {"test-id": mock_connection}):
            result = server.get_columns("test-id", "users")

            assert len(result) == 1
            assert result[0]["column_name"] == "id"
            assert result[0]["data_type"] == "int"


class TestGetProcedures:
    def test_get_procedures(self, mock_connection, mock_cursor, mock_mssql_python):
        mock_row = MagicMock()
        mock_row.PROCEDURE_NAME = "sp_Test"
        mock_row.PROCEDURE_SCHEM = "dbo"
        mock_cursor.fetchall.return_value = [mock_row]
        mock_connection.cursor.return_value = mock_cursor

        with patch.object(server, "_connections", {"test-id": mock_connection}):
            result = server.get_procedures("test-id")

            assert len(result) == 1
            assert result[0]["procedure_name"] == "sp_Test"


class TestGetForeignKeys:
    def test_get_foreign_keys(self, mock_connection, mock_cursor, mock_mssql_python):
        mock_row = MagicMock()
        mock_row.FK_NAME = "FK_test"
        mock_row.FKCOLUMN_NAME = "user_id"
        mock_row.PKTABLE_NAME = "users"
        mock_row.PKCOLUMN_NAME = "id"
        mock_cursor.fetchall.return_value = [mock_row]
        mock_connection.cursor.return_value = mock_cursor

        with patch.object(server, "_connections", {"test-id": mock_connection}):
            result = server.get_foreign_keys("test-id", "orders")

            assert len(result) == 1
            assert result[0]["foreign_key_name"] == "FK_test"


class TestGetPrimaryKeys:
    def test_get_primary_keys(self, mock_connection, mock_cursor, mock_mssql_python):
        mock_row = MagicMock()
        mock_row.COLUMN_NAME = "id"
        mock_row.PK_NAME = "PK_users"
        mock_cursor.fetchall.return_value = [mock_row]
        mock_connection.cursor.return_value = mock_cursor

        with patch.object(server, "_connections", {"test-id": mock_connection}):
            result = server.get_primary_keys("test-id", "users")

            assert len(result) == 1
            assert result[0]["column_name"] == "id"


class TestConnectionString:
    def test_parse_connection_string(self, mock_mssql_python):
        result = server.parse_connection_string("SERVER=localhost;DATABASE=test;")
        assert result["parsed"] == "SERVER=localhost;DATABASE=test;"

    def test_build_connection_string(self, mock_mssql_python):
        result = server.build_connection_string(server="localhost", database="test")
        assert "SERVER=localhost" in result
        assert "DATABASE=test" in result


class TestConnectionSettings:
    def test_set_connection_timeout(self, mock_connection, mock_mssql_python):
        with patch.object(server, "_connections", {"test-id": mock_connection}):
            result = server.set_connection_timeout("test-id", 30)

            assert result["status"] == "set"
            mock_connection.set_attr.assert_called_once()

    def test_set_login_timeout(self, mock_connection, mock_mssql_python):
        with patch.object(server, "_connections", {"test-id": mock_connection}):
            result = server.set_login_timeout("test-id", 15)

            assert result["status"] == "set"

    def test_set_autocommit(self, mock_connection, mock_mssql_python):
        with patch.object(server, "_connections", {"test-id": mock_connection}):
            result = server.set_autocommit("test-id", True)

            assert result["status"] == "set"
            mock_connection.setautocommit.assert_called_once_with(True)


class TestGetConnectionInfo:
    def test_get_connection_info(self, mock_connection, mock_mssql_python):
        mock_connection.getinfo.side_effect = [
            "localhost",
            "testdb",
            "ODBC Driver 18",
            "18.0.0",
        ]

        with patch.object(server, "_connections", {"test-id": mock_connection}):
            result = server.get_connection_info("test-id")

            assert result["server_name"] == "localhost"
            assert result["database"] == "testdb"
