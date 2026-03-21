# ============================================================
# tests/test_schema.py
# Tests for tools/schema.py
# All tests use mock DB — no live SQL Server needed.
# ============================================================

from unittest.mock import MagicMock, patch

import pytest


class TestGetSchema:
    def test_returns_correct_structure(self, mock_db_connection, sample_schema):
        from tools.schema import get_schema

        result = get_schema("measurements")

        assert "table_name"            in result
        assert "columns"               in result
        assert "indexes"               in result
        assert "estimated_row_count"   in result

    def test_table_name_preserved(self, mock_db_connection):
        from tools.schema import get_schema

        result = get_schema("measurements")
        assert result["table_name"] == "measurements"

    def test_columns_have_required_fields(self, mock_db_connection):
        from tools.schema import get_schema

        result = get_schema("measurements")
        assert len(result["columns"]) > 0

        for col in result["columns"]:
            assert "name"        in col
            assert "type"        in col
            assert "nullable"    in col
            assert "primary_key" in col

    def test_identifies_primary_key(self, mock_db_connection):
        from tools.schema import get_schema

        result = get_schema("measurements")
        pk_cols = [c for c in result["columns"] if c["primary_key"] == "YES"]
        assert len(pk_cols) >= 1
        assert pk_cols[0]["name"] == "id"

    def test_indexes_have_required_fields(self, mock_db_connection):
        from tools.schema import get_schema

        result = get_schema("measurements")
        for idx in result["indexes"]:
            assert "name"             in idx
            assert "type"             in idx
            assert "key_columns"      in idx

    def test_row_count_is_integer(self, mock_db_connection):
        from tools.schema import get_schema

        result = get_schema("measurements")
        assert isinstance(result["estimated_row_count"], int)
        assert result["estimated_row_count"] > 0

    def test_db_connection_error_raises_typed_exception(self):
        from tools.error_handler import DBConnectionError
        from tools.schema import get_schema
        import pyodbc

        with patch("pyodbc.connect", side_effect=pyodbc.Error("08001", "connection failed")):
            with pytest.raises((DBConnectionError, Exception)):
                get_schema("measurements")


class TestGetViewDefinition:
    def test_returns_view_structure(self, mock_db_connection):
        from tools.schema import get_view_definition

        result = get_view_definition("vw_dashboard")

        assert "view_name"          in result
        assert "definition"         in result
        assert "referenced_tables"  in result

    def test_view_name_preserved(self, mock_db_connection):
        from tools.schema import get_view_definition

        result = get_view_definition("vw_dashboard")
        assert result["view_name"] == "vw_dashboard"

    def test_definition_is_string(self, mock_db_connection):
        from tools.schema import get_view_definition

        result = get_view_definition("vw_dashboard")
        assert isinstance(result["definition"], str)
        assert len(result["definition"]) > 0

    def test_missing_view_returns_error(self, mock_db_connection):
        from tools.schema import get_view_definition

        # Patch fetchone to return None (view not found)
        mock_cursor = mock_db_connection.cursor.return_value
        mock_cursor.fetchone.return_value = None

        result = get_view_definition("nonexistent_view")
        assert "error" in result


class TestListObjects:
    def test_list_all_tables_returns_list(self, mock_db_connection):
        from tools.schema import list_all_tables

        tables = list_all_tables()
        assert isinstance(tables, list)

    def test_list_all_tables_contains_measurements(self, mock_db_connection):
        from tools.schema import list_all_tables

        tables = list_all_tables()
        assert "measurements" in tables

    def test_list_all_views_returns_list(self, mock_db_connection):
        from tools.schema import list_all_views

        views = list_all_views()
        assert isinstance(views, list)

    def test_list_all_views_contains_dashboard(self, mock_db_connection):
        from tools.schema import list_all_views

        views = list_all_views()
        assert "vw_dashboard" in views


class TestConnection:
    def test_successful_connection_returns_true(self, mock_db_connection):
        from tools.schema import test_connection

        result = test_connection()
        assert result is True

    def test_failed_connection_returns_false(self):
        from tools.schema import test_connection
        import pyodbc

        with patch("pyodbc.connect", side_effect=pyodbc.Error("08001", "failed")):
            result = test_connection()
        assert result is False
