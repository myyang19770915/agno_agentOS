"""
tests/test_database.py — PostgreSQL 功能測試
需要可用的 Postgres 連線。若無可跳過。
"""
import json
import pytest
from unittest.mock import patch, MagicMock

from app.core.database import PostgresDB


class TestPostgresDBUnit:
    """使用 mock 的單元測試（不需要真實 DB）。"""

    def test_keyword_search_builds_correct_sql(self):
        """keyword_search 應構建正確的 ILIKE 查詢。"""
        db = PostgresDB(dsn="postgresql://test:test@localhost/test")
        with patch.object(db, "fetch_ids", return_value=["id1", "id2"]) as mock_fetch:
            result = db.keyword_search("documents", "content", "台北")
            mock_fetch.assert_called_once()
            call_args = mock_fetch.call_args
            sql = call_args[0][0]
            assert "ILIKE" in sql
            assert "%台北%" in call_args[0][1]

    def test_health_check_returns_false_on_error(self):
        """連線失敗時 health_check 應回傳 False。"""
        db = PostgresDB(dsn="postgresql://bad:bad@nonexistent:9999/nope")
        assert db.health_check() is False

    def test_list_tables_builds_information_schema_query(self):
        """list_tables 應查詢 information_schema.tables。"""
        db = PostgresDB(dsn="postgresql://test:test@localhost/test")
        fake_rows = [{"table_schema": "public", "table_name": "documents", "table_type": "BASE TABLE"}]
        with patch.object(db, "execute_query", return_value=fake_rows) as mock_query:
            result = db.list_tables(schema="public", limit=5)
            sql = mock_query.call_args[0][0]
            params = mock_query.call_args[0][1]
            assert "information_schema.tables" in sql
            assert params == ("public", 5)
            assert result == fake_rows

    def test_describe_table_returns_not_exists_when_empty(self):
        """describe_table 在 table 不存在時應回傳 exists=False。"""
        db = PostgresDB(dsn="postgresql://test:test@localhost/test")
        with patch.object(db, "execute_query", return_value=[]):
            result = db.describe_table("missing_table", schema="public")
            assert result["exists"] is False
            assert result["columns"] == []


class TestAnalyticsToolSafety:
    """analytics_tool SQL 安全性測試。"""

    def test_blocks_insert(self):
        from app.tools.analytics_tool import postgres_analytics_tool
        result = json.loads(postgres_analytics_tool("INSERT INTO evil VALUES (1)"))
        assert "error" in result or "禁止" in result.get("error", "")

    def test_blocks_drop(self):
        from app.tools.analytics_tool import postgres_analytics_tool
        result = json.loads(postgres_analytics_tool("DROP TABLE documents"))
        assert "error" in result

    def test_blocks_delete(self):
        from app.tools.analytics_tool import postgres_analytics_tool
        result = json.loads(postgres_analytics_tool("DELETE FROM documents"))
        assert "error" in result

    def test_blocks_update(self):
        from app.tools.analytics_tool import postgres_analytics_tool
        result = json.loads(postgres_analytics_tool("UPDATE documents SET title='hack'"))
        assert "error" in result

    def test_blocks_truncate(self):
        from app.tools.analytics_tool import postgres_analytics_tool
        result = json.loads(postgres_analytics_tool("TRUNCATE documents"))
        assert "error" in result

    def test_blocks_alter(self):
        from app.tools.analytics_tool import postgres_analytics_tool
        result = json.loads(postgres_analytics_tool("ALTER TABLE documents ADD COLUMN evil TEXT"))
        assert "error" in result

    def test_schema_purpose_returns_tables(self):
        from app.tools.analytics_tool import postgres_analytics_tool

        with patch("app.tools.analytics_tool.postgres_db.list_tables") as mock_list_tables, patch(
            "app.tools.analytics_tool.postgres_db.describe_table"
        ) as mock_describe_table:
            mock_list_tables.return_value = [
                {"table_schema": "public", "table_name": "documents", "table_type": "BASE TABLE"}
            ]
            mock_describe_table.return_value = {
                "exists": True,
                "schema": "public",
                "table_name": "documents",
                "columns": [
                    {
                        "column_name": "id",
                        "data_type": "text",
                        "is_nullable": "NO",
                        "is_primary_key": True,
                    }
                ],
                "foreign_keys": [],
            }

            result = json.loads(postgres_analytics_tool(purpose="schema", limit=10))

        assert result["ok"] is True
        assert result["purpose"] == "schema"
        assert result["available_tables"][0]["table_name"] == "documents"

    def test_query_error_returns_retry_payload(self):
        from app.tools.analytics_tool import postgres_analytics_tool

        with patch("app.tools.analytics_tool.postgres_db.execute_query", side_effect=Exception("column foo does not exist")), patch(
            "app.tools.analytics_tool.postgres_db.describe_table"
        ) as mock_describe_table:
            mock_describe_table.return_value = {
                "exists": True,
                "schema": "public",
                "table_name": "documents",
                "columns": [],
                "foreign_keys": [],
            }
            result = json.loads(
                postgres_analytics_tool(
                    sql="SELECT foo FROM documents",
                    purpose="statistics",
                )
            )

        assert result["ok"] is False
        assert result["retryable"] is True
        assert result["failed_sql"] == "SELECT foo FROM documents"
        assert result["schema_context"]["related_schema"][0]["table_name"] == "documents"
