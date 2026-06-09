"""
Agent Pipeline — Agno Agent 主入口

使用 Agno Agent Framework 取代原始 context_pipeline.py 中的 if-else 路由，
讓 LLM 動態決定呼叫哪些工具來回答使用者問題。

使用方式：
    cd /root/agno_agentOS/Context-layer-agent
    source /root/agno_agentOS/.venv/bin/activate
    python tools/agent_pipeline.py
"""

from __future__ import annotations

import os
import sys

# 確保可以從專案根目錄匯入 tools 模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.agent import Agent
from agno.models.litellm import LiteLLMOpenAI

from tools.adapters.agno_tools import (
    query_case_system,
    query_crm,
    query_erp,
    resolve_context,
)
from tools.system_prompt_builder import build_agent_system_prompt

# ── LLM 配置 ──────────────────────────────────────────────
model = LiteLLMOpenAI(
    id="TXC-LLM",
    api_key="AI.7u8i(O)P",
    base_url="http://192.168.37.71:32290",
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)

# ── System Prompt ─────────────────────────────────────────
system_prompt = build_agent_system_prompt(default_user_id="sales_manager_demo")

# ── Agent 建置 ────────────────────────────────────────────
agent = Agent(
    model=model,
    tools=[resolve_context, query_crm, query_erp, query_case_system],
    instructions=[system_prompt],
    markdown=True,
)


def run_agent(query: str) -> None:
    """執行 Agent 並印出回答。

    Args:
        query: 使用者的查詢問題
    """
    print("=" * 60)
    print(f"📝 Query: {query}")
    print("=" * 60)
    agent.print_response(query)
    print("\n")


if __name__ == "__main__":
    # ── 範例查詢 ──────────────────────────────────────────
    # 查詢 1：Customer 查詢（應觸發 CRM + ERP）
    run_agent("幫我看最近 active customer 狀況")

    # 查詢 2：Customer + Case 跨 domain 查詢（應觸發 CRM + ERP + CaseSystem）
    run_agent("請分析 active customer 的 open case 狀況")

    # 查詢 3：涉及財務的查詢（應觸發 finance warning）
    run_agent("請分析 active customer 的營收與付款狀況")
