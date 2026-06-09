"""
app/main.py — FastAPI 入口
提供 /chat (SSE streaming)、/health、/api/db/* 等 API 端點。
"""
from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.router_agent import router_agent
from app.core.database import postgres_db
from app.core.vector_db import vector_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ---- Lifespan ----
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Hybrid RAG Agent starting up...")
    vector_db.ensure_collection()
    yield
    logger.info("🛑 Shutting down.")


app = FastAPI(
    title="Hybrid RAG Agent API",
    description="整合 Postgres (SQL) + Qdrant (Vector + BM25) + RRF 融合的 AI Agent",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Request / Response 模型 ----
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="使用者查詢")
    session_id: Optional[str] = Field(default=None, description="會話 ID")


class ChatResponse(BaseModel):
    answer: str
    session_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    postgres: bool
    qdrant: bool


# ---- Helper：SSE 格式化 ----
def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


# ---- Chat (SSE streaming) ----
@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """與 Agent 對話，透過 SSE 串流回傳 tool_call / content / done 事件。"""

    def _generate():
        try:
            response_stream = router_agent.run(
                req.message,
                stream=True,
                stream_events=True,
                session_id=req.session_id,
            )
            for event in response_stream:
                event_type = getattr(event, "event", None)

                if event_type == "ToolCallStarted":
                    tool = event.tool
                    yield _sse("tool_start", {
                        "tool_call_id": tool.tool_call_id,
                        "tool_name": tool.tool_name,
                        "tool_args": tool.tool_args,
                    })

                elif event_type == "ToolCallCompleted":
                    tool = event.tool
                    # 截斷過長的 result
                    raw_result = tool.result or ""
                    try:
                        parsed = json.loads(raw_result)
                    except (json.JSONDecodeError, TypeError):
                        parsed = raw_result
                    yield _sse("tool_done", {
                        "tool_call_id": tool.tool_call_id,
                        "tool_name": tool.tool_name,
                        "result": parsed,
                        "error": tool.tool_call_error,
                    })

                elif event_type == "RunContentEvent":
                    content = event.content
                    if content:
                        yield _sse("content", {"delta": str(content)})

                elif event_type == "RunCompleted":
                    final_content = getattr(event, "content", None)
                    if final_content:
                        yield _sse("content", {"delta": str(final_content)})

            yield _sse("done", {"status": "ok"})

        except Exception as exc:
            logger.exception("Chat stream error")
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """與 Hybrid Intelligence Agent 對話（非串流）。"""
    try:
        response = router_agent.run(req.message)
        answer = response.content if response.content else "Agent 無法產生回應"
        return ChatResponse(answer=answer, session_id=req.session_id)
    except Exception as exc:
        logger.exception("Chat error")
        raise HTTPException(status_code=500, detail=str(exc))


# ---- Database Browser API ----
@app.get("/api/db/tables")
async def db_tables(schema: Optional[str] = Query(default=None)):
    """列出資料庫中的 tables / views。"""
    try:
        tables = postgres_db.list_tables(schema=schema, limit=200)
        return {"ok": True, "tables": tables}
    except Exception as exc:
        logger.exception("db_tables error")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/db/tables/{table_name}/schema")
async def db_table_schema(table_name: str, schema: Optional[str] = Query(default=None)):
    """回傳資料表的欄位、主鍵、外鍵。"""
    try:
        desc = postgres_db.describe_table(table_name=table_name, schema=schema)
        return {"ok": True, **desc}
    except Exception as exc:
        logger.exception("db_table_schema error")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/db/tables/{table_name}/rows")
async def db_table_rows(
    table_name: str,
    schema: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """預覽資料表前 N 筆資料（唯讀）。"""
    # 防止 SQL injection：只允許合法識別符
    import re
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
        raise HTTPException(status_code=400, detail="Invalid table name")
    if schema and not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", schema):
        raise HTTPException(status_code=400, detail="Invalid schema name")

    qualified = f'"{schema}"."{table_name}"' if schema else f'"{table_name}"'
    try:
        count_rows = postgres_db.execute_query(f"SELECT COUNT(*) AS total FROM {qualified}")
        total = count_rows[0]["total"] if count_rows else 0
        rows = postgres_db.execute_query(
            f"SELECT * FROM {qualified} LIMIT %s OFFSET %s",
            (limit, offset),
        )
        return {"ok": True, "rows": rows, "total": total, "limit": limit, "offset": offset}
    except Exception as exc:
        logger.exception("db_table_rows error")
        raise HTTPException(status_code=500, detail=str(exc))


# ---- Health / Root ----
@app.get("/health", response_model=HealthResponse)
async def health():
    """健康檢查端點。"""
    pg_ok = postgres_db.health_check()
    qd_ok = vector_db.health_check()
    status = "healthy" if (pg_ok and qd_ok) else "degraded"
    return HealthResponse(status=status, postgres=pg_ok, qdrant=qd_ok)


@app.get("/")
async def root():
    return {
        "service": "Hybrid RAG Agent",
        "version": "1.0.0",
        "docs": "/docs",
    }
