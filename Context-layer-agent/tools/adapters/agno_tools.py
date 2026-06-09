"""
Agno Tool Functions — 將現有 Adapter 與 Context Resolver 封裝為 Agno @tool

這些 tool 函式供 Agent 動態呼叫，取代原本 context_pipeline.py 中的硬編碼 if-else 路由。
"""

from __future__ import annotations

import json
import os
import sys

# 確保可以從專案根目錄匯入 tools 模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agno.tools import tool

from tools.adapters.mock_case import MockCaseAdapter
from tools.adapters.mock_crm import MockCRMAdapter
from tools.adapters.mock_erp import MockERPAdapter
from tools.context_resolver import resolve_context_package


@tool
def resolve_context(query: str, user_id: str) -> str:
    """解析使用者的情境資訊，包含權限、商業名詞定義、資料口徑與可用資料源等。

    此工具必須在查詢任何資料之前優先呼叫，以獲取正確的 context package。
    回傳內容包含：
    - query_context：意圖分析與解析出的商業名詞
    - domain_context：名詞定義（scope, active_rule 等）
    - user_context：使用者角色與偏好
    - access_context：權限控管資訊
    - data_sources：建議查詢的資料系統清單
    - warnings：任何存取限制警告

    Args:
        query: 使用者的原始查詢問題
        user_id: 使用者 ID，用於查詢權限與偏好設定

    Returns:
        JSON 格式的 context package
    """
    package = resolve_context_package(query=query, user_id=user_id)
    return json.dumps(package, ensure_ascii=False, indent=2)


@tool
def query_crm(query: str) -> str:
    """查詢 CRM 系統以獲取客戶相關資料。

    可取得的資料包含：active customer 數量、客戶趨勢、客戶分群（top segments）等。
    當使用者問題涉及 customer（客戶）相關分析時呼叫此工具。

    Args:
        query: 使用者的查詢問題，用於篩選 CRM 資料

    Returns:
        JSON 格式的 CRM 查詢結果，包含 adapter 名稱、domain 與 signals
    """
    adapter = MockCRMAdapter()
    result = adapter.fetch(query=query, context_package={})
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def query_erp(query: str) -> str:
    """查詢 ERP 系統以獲取訂單、出貨與業務數據變化等資料。

    可取得的資料包含：change_pct（數據變動百分比）、supporting_sources（資料來源）等。
    當需要補充業務數據趨勢、訂單或出貨資訊時呼叫此工具。

    Args:
        query: 使用者的查詢問題，用於篩選 ERP 資料

    Returns:
        JSON 格式的 ERP 查詢結果，包含 adapter 名稱、domain 與 signals
    """
    adapter = MockERPAdapter()
    result = adapter.fetch(query=query, context_package={})
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def query_case_system(query: str) -> str:
    """查詢案件管理系統以獲取 open case 數量、高優先案件、案件分類等資料。

    可取得的資料包含：open_case_count、high_priority_open_cases、top_case_categories 等。
    當使用者問題涉及 case（案件）相關分析時呼叫此工具。

    Args:
        query: 使用者的查詢問題，用於篩選案件資料

    Returns:
        JSON 格式的案件系統查詢結果，包含 adapter 名稱、domain 與 signals
    """
    adapter = MockCaseAdapter()
    result = adapter.fetch(query=query, context_package={})
    return json.dumps(result, ensure_ascii=False, indent=2)
