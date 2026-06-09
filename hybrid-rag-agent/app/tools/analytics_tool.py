"""
app/tools/analytics_tool.py — SQL 統計工具 (Text-to-SQL style)
供 Agno Agent 調用，回傳結構化統計結果或 ID 列表。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.core.database import postgres_db

logger = logging.getLogger(__name__)


# ---- Pydantic 輸入模型 ----
class SQLQueryInput(BaseModel):
    sql: str = Field(default="", description="要執行的 SELECT SQL 語句；purpose='schema' 時可留空")
    purpose: str = Field(
        default="statistics",
        description="查詢目的：'statistics' 回傳完整結果, 'filter_ids' 僅回傳 ID 列表, 'schema' 查詢資料表 schema",
    )
    id_column: str = Field(
        default="id",
        description="當 purpose='filter_ids' 時，要提取的 ID 欄位名稱",
    )
    table_name: Optional[str] = Field(
        default=None,
        description="當 purpose='schema' 時，可指定要檢視的資料表名稱",
    )
    schema_name: Optional[str] = Field(
        default=None,
        description="可選的 schema 名稱；未提供時會使用資料庫中的實際 schema",
    )
    limit: Optional[int] = Field(
        default=500,
        description="結果上限，超過此數將截斷並提示使用者縮小範圍",
    )


ALLOWED_SQL_PREFIXES = ("SELECT", "WITH")
FORBIDDEN_SQL_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
)
TABLE_REFERENCE_PATTERN = re.compile(
    r'\b(?:FROM|JOIN)\s+(["\w\.]+)',
    flags=re.IGNORECASE,
)


def _normalize_limit(limit: Optional[int], default: int = 500, maximum: int = 500) -> int:
    if limit is None:
        return default
    return max(1, min(limit, maximum))


def _clean_table_reference(table_ref: str) -> tuple[Optional[str], str]:
    normalized = table_ref.strip().strip(',').replace('"', "")
    if "." in normalized:
        schema_name, table_name = normalized.split(".", 1)
        return schema_name or None, table_name
    return None, normalized


def _extract_referenced_tables(sql: str) -> List[Dict[str, Optional[str]]]:
    seen: set[tuple[Optional[str], str]] = set()
    tables: List[Dict[str, Optional[str]]] = []
    for raw_table in TABLE_REFERENCE_PATTERN.findall(sql):
        schema_name, table_name = _clean_table_reference(raw_table)
        key = (schema_name, table_name)
        if table_name and key not in seen:
            seen.add(key)
            tables.append({"schema": schema_name, "table_name": table_name})
    return tables


def _build_schema_overview(limit: int, schema_name: Optional[str] = None) -> Dict[str, Any]:
    tables = postgres_db.list_tables(schema=schema_name, limit=min(limit, 25))
    table_summaries = []

    for table in tables:
        description = postgres_db.describe_table(
            table_name=table["table_name"],
            schema=table["table_schema"],
        )
        table_summaries.append(
            {
                "schema": description["schema"],
                "table_name": description["table_name"],
                "table_type": table["table_type"],
                "columns": [
                    {
                        "name": column["column_name"],
                        "type": column["data_type"],
                        "nullable": column["is_nullable"],
                        "primary_key": bool(column["is_primary_key"]),
                    }
                    for column in description["columns"]
                ],
            }
        )

    return {
        "available_tables": table_summaries,
        "count": len(table_summaries),
        "guidance": [
            "先確認 table 與 column 是否存在，再生成 SQL。",
            "若不確定資料表，先呼叫 purpose='schema' 並不帶 table_name 取得總覽。",
        ],
    }


def _build_schema_payload(
    table_name: Optional[str],
    schema_name: Optional[str],
    limit: int,
) -> Dict[str, Any]:
    if table_name:
        description = postgres_db.describe_table(table_name=table_name, schema=schema_name)
        return {
            "ok": description["exists"],
            "purpose": "schema",
            "schema": description,
            "guidance": [
                "依照欄位名稱與型別生成 SELECT SQL。",
                "若 exists=false，先查看 available_tables 確認正確資料表名稱。",
            ],
            "available_tables": [] if description["exists"] else postgres_db.list_tables(schema=schema_name, limit=min(limit, 10)),
        }

    return {
        "ok": True,
        "purpose": "schema",
        **_build_schema_overview(limit=limit, schema_name=schema_name),
    }


def _validate_read_only_sql(sql: str) -> Optional[Dict[str, Any]]:
    stripped_sql = sql.strip()
    if not stripped_sql:
        return {"error": "sql 不可為空"}

    sql_upper = stripped_sql.upper()
    for keyword in FORBIDDEN_SQL_KEYWORDS:
        if sql_upper.startswith(keyword):
            return {"error": f"禁止執行 {keyword} 類型的 SQL 語句"}

    if not sql_upper.startswith(ALLOWED_SQL_PREFIXES):
        return {"error": "僅允許執行 SELECT 或 WITH 開頭的唯讀 SQL"}

    if ";" in stripped_sql.rstrip(";"):
        return {"error": "禁止一次執行多條 SQL 語句"}

    return None


def _format_exception_details(exc: Exception) -> Dict[str, Any]:
    diag = getattr(exc, "diag", None)
    return {
        "type": exc.__class__.__name__,
        "message": str(exc),
        "sqlstate": getattr(exc, "sqlstate", None),
        "detail": getattr(diag, "message_detail", None),
        "hint": getattr(diag, "message_hint", None),
        "schema_name": getattr(diag, "schema_name", None),
        "table_name": getattr(diag, "table_name", None),
        "column_name": getattr(diag, "column_name", None),
        "position": getattr(diag, "statement_position", None),
    }


def _build_error_payload(
    sql: str,
    purpose: str,
    id_column: str,
    limit: int,
    exc: Exception,
) -> Dict[str, Any]:
    referenced_tables = _extract_referenced_tables(sql)
    related_schema = []

    for table_ref in referenced_tables[:5]:
        try:
            related_schema.append(
                postgres_db.describe_table(
                    table_name=table_ref["table_name"],
                    schema=table_ref["schema"],
                )
            )
        except Exception:
            logger.warning("Failed to inspect schema for %s", table_ref, exc_info=True)

    fallback_tables: List[Dict[str, Any]] = []
    if not related_schema:
        try:
            fallback_tables = postgres_db.list_tables(limit=min(limit, 10))
        except Exception:
            logger.warning("Failed to inspect available tables after SQL error", exc_info=True)

    return {
        "ok": False,
        "purpose": purpose,
        "retryable": True,
        "failed_sql": sql,
        "id_column": id_column,
        "error": _format_exception_details(exc),
        "schema_context": {
            "referenced_tables": referenced_tables,
            "related_schema": related_schema,
            "available_tables": fallback_tables,
        },
        "retry_instructions": [
            "依 error 與 schema_context 修正 table/column 名稱後重試。",
            "若不確定 schema，先呼叫 purpose='schema' 取得總覽或指定 table_name 查看欄位。",
            "重試時保持唯讀 SQL，且只使用 SELECT 或 WITH。",
        ],
    }


# ---- Tool 函式（供 Agno Agent 使用）----
def postgres_analytics_tool(
    sql: str = "",
    purpose: str = "statistics",
    id_column: str = "id",
    table_name: Optional[str] = None,
    schema_name: Optional[str] = None,
    limit: int = 500,
) -> str:
    """
    PostgreSQL 統計與篩選工具。

    使用方式：
    - purpose='schema'：查詢資料表與欄位 schema，供生成 SQL 前參考
    - purpose='statistics'：執行 SQL 並回傳完整結果（dict list as JSON）
    - purpose='filter_ids'：執行 SQL 並僅回傳指定欄位的 ID 列表（供後續 Qdrant Filter）

    注意事項：
    - 只允許 SELECT / WITH 開頭的唯讀 SQL
    - 結果超過 limit 筆時會截斷
    - 查詢失敗時會回傳結構化錯誤與 schema 線索，供 Agent 修正後 retry
    """
    limit = _normalize_limit(limit)

    if purpose == "schema":
        try:
            return json.dumps(
                _build_schema_payload(
                    table_name=table_name,
                    schema_name=schema_name,
                    limit=limit,
                ),
                ensure_ascii=False,
                default=str,
            )
        except Exception as exc:
            logger.exception("postgres_analytics_tool schema error")
            return json.dumps(
                {
                    "ok": False,
                    "purpose": "schema",
                    "retryable": True,
                    "error": _format_exception_details(exc),
                    "retry_instructions": [
                        "稍後重試 schema 查詢。",
                        "若有指定 schema_name 或 table_name，請確認名稱是否正確。",
                    ],
                },
                ensure_ascii=False,
                default=str,
            )

    validation_error = _validate_read_only_sql(sql)
    if validation_error:
        return json.dumps(
            {
                "ok": False,
                "purpose": purpose,
                "retryable": True,
                "failed_sql": sql,
                **validation_error,
                "retry_instructions": [
                    "改成 SELECT 或 WITH 開頭的唯讀 SQL。",
                    "若不確定欄位名稱，先用 purpose='schema' 查看 schema。",
                ],
            },
            ensure_ascii=False,
        )

    try:
        if purpose == "filter_ids":
            ids = postgres_db.fetch_ids(sql, id_col=id_column)
            if len(ids) > limit:
                return json.dumps(
                    {
                        "ok": True,
                        "purpose": purpose,
                        "warning": f"篩選結果 ({len(ids)} 筆) 超過上限 {limit}，請縮小查詢範圍",
                        "ids": ids[:limit],
                        "count": len(ids),
                        "truncated": True,
                    },
                    ensure_ascii=False,
                )
            return json.dumps(
                {
                    "ok": True,
                    "purpose": purpose,
                    "ids": ids,
                    "count": len(ids),
                },
                ensure_ascii=False,
            )

        if purpose != "statistics":
            return json.dumps(
                {
                    "ok": False,
                    "purpose": purpose,
                    "retryable": True,
                    "error": f"不支援的 purpose: {purpose}",
                    "retry_instructions": [
                        "請使用 'schema'、'statistics' 或 'filter_ids'。",
                    ],
                },
                ensure_ascii=False,
            )

        rows = postgres_db.execute_query(sql)
        if len(rows) > limit:
            return json.dumps(
                {
                    "ok": True,
                    "purpose": purpose,
                    "warning": f"結果 ({len(rows)} 筆) 超過上限 {limit}，已截斷",
                    "data": rows[:limit],
                    "count": len(rows),
                    "truncated": True,
                },
                ensure_ascii=False,
                default=str,
            )
        return json.dumps(
            {
                "ok": True,
                "purpose": purpose,
                "data": rows,
                "count": len(rows),
            },
            ensure_ascii=False,
            default=str,
        )

    except Exception as exc:
        logger.exception(
            "postgres_analytics_tool error | purpose=%s | sql=%s | table_name=%s | schema_name=%s",
            purpose,
            sql,
            table_name,
            schema_name,
        )
        return json.dumps(
            _build_error_payload(
                sql=sql,
                purpose=purpose,
                id_column=id_column,
                limit=limit,
                exc=exc,
            ),
            ensure_ascii=False,
            default=str,
        )
