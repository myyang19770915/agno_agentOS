"""
app/agents/router_agent.py — 主編排 Agent (Agno)
實作 Intent Routing：自動判斷使用者意圖後分派至 SQL 統計 / 混合檢索。
支援「先過濾、再檢索」的鏈式推理。
使用 LiteLLMOpenAI 連接 TXC-LLM (Qwen3.5) 模型。
"""
from __future__ import annotations

from typing import Any, Optional

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.models.litellm import LiteLLMOpenAI

from app.core.config import settings
from app.tools.analytics_tool import postgres_analytics_tool
from app.tools.retrieval_tool import unified_hybrid_search

# ---- Agent 指令集 ----
AGENT_INSTRUCTIONS = [
    "你是一個具備『精確過濾』能力的混合檢索專家，同時支援 SQL 統計分析與語意搜尋。",
    "",
    "## 思維鏈 (Chain of Thought)",
    "1. **先確認 schema**：只要要生成 SQL，先呼叫 postgres_analytics_tool(purpose='schema') 檢查可用 tables/columns；若已有明確 table，也可帶 table_name 精查欄位。",
    "2. **拆解問題**：分析用戶問題中是否包含明確的分類、日期、狀態、地區或 ID 等結構化屬性。",
    "3. **判斷路由**：",
    "   - 若問題涉及『計算、總和、平均、統計、排名、趨勢』→ 使用 postgres_analytics_tool (purpose='statistics')",
    "   - 若問題涉及『概念描述、原因分析、建議、知識查詢』→ 使用 unified_hybrid_search",
    "   - 若問題『同時涉及結構化條件 + 語意搜尋』→ 先用 postgres_analytics_tool (purpose='filter_ids') 取得 ID 列表，再將 ID 傳給 unified_hybrid_search 的 filter_ids 參數",
    "4. **執行 SQL 預篩選**：如果存在結構化屬性，必須先調用 postgres_analytics_tool 獲取符合條件的 ID 列表。",
    "5. **執行約束檢索**：將獲取的 ID 列表以逗號分隔字串形式傳入 unified_hybrid_search 的 filter_ids。",
    "6. **綜合回答**：透過 SQL 縮小範圍確保『準確度』，透過向量搜尋確保『相關性』。",
    "",
    "## 邊緣情況處理",
    "- 若 postgres_analytics_tool 回傳 ok=false 且 retryable=true，必須根據 error 與 schema_context 修正 SQL 後至少重試一次。",
    "- 若 SQL 報欄位不存在或資料表不存在，先重新呼叫 purpose='schema' 確認正確欄位/資料表名稱。",
    "- 若 SQL 篩選出的 ID 超過 500 個，提示用戶縮小範圍。",
    "- 若檢索結果為空，明確告知用戶並建議調整查詢。",
    "- 若問題模糊不清，先向使用者確認意圖，不要盲目搜尋。",
    "- 始終在回答中標注數據來源（SQL 統計 / 語意檢索 / 混合）。",
]

def build_router_agent(
    model: Optional[Any] = None,
    tools: Optional[list[Any]] = None,
    db: Optional[Any] = None,
    debug_mode: bool = True,
) -> Agent:
    """建立 Router Agent，方便在測試中注入 fake model/tools。"""
    if model is None:
        model = LiteLLMOpenAI(
            id=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            extra_body={
                "chat_template_kwargs": {"enable_thinking": False},
            },
        )

    return Agent(
        name="Hybrid Intelligence Agent",
        model=model,
        tools=tools or [postgres_analytics_tool, unified_hybrid_search],
        instructions=AGENT_INSTRUCTIONS,
        db=db,
        add_history_to_context=True,
        num_history_runs=5,
        markdown=True,
        debug_mode=debug_mode,
    )


# ---- Agent Session DB（歷史持久化）----
_agent_db = PostgresDb(
    db_url=settings.AGENT_DB_URL,
    session_table=settings.AGENT_SESSION_TABLE,
    db_schema=settings.AGENT_DB_SCHEMA,
    create_schema=True,
)

# ---- 建立 Agent ----
router_agent = build_router_agent(db=_agent_db)
