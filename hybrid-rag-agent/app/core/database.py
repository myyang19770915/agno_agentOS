"""
app/core/database.py — PostgreSQL 連線與 SQL 執行
支援同步查詢，並自動管理連線池。
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import psycopg
from psycopg.rows import dict_row

from app.core.config import settings

logger = logging.getLogger(__name__)


class PostgresDB:
    """輕量 Postgres 封裝，使用 psycopg 3 同步連線。"""

    def __init__(self, dsn: Optional[str] = None):
        self._dsn = dsn or settings.pg_dsn

    # ---- 連線管理 ----
    @contextmanager
    def _conn(self):
        conn = psycopg.connect(self._dsn, row_factory=dict_row)
        try:
            yield conn
        finally:
            conn.close()

    # ---- 公開 API ----
    def execute_query(
        self, sql: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """執行 SELECT 查詢，回傳 dict 列表。"""
        logger.info("SQL ▸ %s | params=%s", sql, params)
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()

    def execute_write(
        self, sql: str, params: Optional[tuple] = None
    ) -> int:
        """執行 INSERT/UPDATE/DELETE，回傳受影響行數。"""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                conn.commit()
                return cur.rowcount

    def fetch_ids(
        self, sql: str, params: Optional[tuple] = None, id_col: str = "id"
    ) -> List[str]:
        """執行 SQL 並僅回傳指定欄位的 ID 列表（供 Qdrant Filter 使用）。"""
        rows = self.execute_query(sql, params)
        return [str(r[id_col]) for r in rows if id_col in r]

    def list_tables(
        self,
        schema: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """列出可查詢的資料表。"""
        filters = [
            "table_schema NOT IN ('pg_catalog', 'information_schema')",
            "table_type IN ('BASE TABLE', 'VIEW')",
        ]
        params: List[Any] = []

        if schema:
            filters.append("table_schema = %s")
            params.append(schema)

        params.append(limit)
        sql = f"""
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE {' AND '.join(filters)}
            ORDER BY
                CASE WHEN table_schema = 'public' THEN 0 ELSE 1 END,
                table_schema,
                table_name
            LIMIT %s
        """
        return self.execute_query(sql, tuple(params))

    def describe_table(
        self,
        table_name: str,
        schema: Optional[str] = None,
    ) -> Dict[str, Any]:
        """回傳資料表欄位、主鍵與外鍵資訊。"""
        schema_filter = "AND c.table_schema = %s" if schema else ""
        params: List[Any] = [table_name]
        if schema:
            params.append(schema)

        columns = self.execute_query(
            f"""
            SELECT
                c.table_schema,
                c.table_name,
                c.column_name,
                c.data_type,
                c.udt_name,
                c.is_nullable,
                c.column_default,
                CASE WHEN pk.column_name IS NOT NULL THEN TRUE ELSE FALSE END AS is_primary_key
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT
                    kcu.table_schema,
                    kcu.table_name,
                    kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
            ) pk
              ON pk.table_schema = c.table_schema
             AND pk.table_name = c.table_name
             AND pk.column_name = c.column_name
            WHERE c.table_name = %s
              {schema_filter}
            ORDER BY c.ordinal_position
            """,
            tuple(params),
        )

        if not columns:
            return {
                "exists": False,
                "schema": schema,
                "table_name": table_name,
                "columns": [],
                "foreign_keys": [],
            }

        foreign_keys = self.execute_query(
            f"""
            SELECT
                kcu.column_name,
                ccu.table_schema AS foreign_table_schema,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_name = %s
              {"AND tc.table_schema = %s" if schema else ""}
            ORDER BY kcu.column_name
            """,
            tuple(params),
        )

        return {
            "exists": True,
            "schema": columns[0]["table_schema"],
            "table_name": columns[0]["table_name"],
            "columns": columns,
            "foreign_keys": foreign_keys,
        }

    def keyword_search(
        self,
        table: str,
        column: str,
        keyword: str,
        id_col: str = "id",
        limit: int = 200,
    ) -> List[str]:
        """以 ILIKE 進行關鍵字搜尋，回傳 ID 列表。"""
        sql = f"""
            SELECT {id_col} FROM {table}
            WHERE {column} ILIKE %s
            LIMIT %s
        """
        return self.fetch_ids(sql, (f"%{keyword}%", limit), id_col=id_col)

    def health_check(self) -> bool:
        """回傳 True 表示連線正常。"""
        try:
            self.execute_query("SELECT 1 AS ok")
            return True
        except Exception as exc:
            logger.warning("Postgres health check failed: %s", exc)
            return False


# 模組級單例
postgres_db = PostgresDB()
