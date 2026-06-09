from __future__ import annotations

import os
import sys

# Ensure the project root is in sys.path so 'tools' can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Any

from tools.adapters.mock_case import MockCaseAdapter
from tools.adapters.mock_crm import MockCRMAdapter
from tools.adapters.mock_erp import MockERPAdapter
from tools.context_resolver import resolve_context_package
from tools.prompt_builder import build_llm_prompt


def _fetch_mock_data(context_package: dict[str, Any], query: str) -> dict[str, Any]:
    lowered = query.lower()
    has_customer = "customer" in lowered or "客戶" in lowered
    has_case = "case" in lowered or "案件" in lowered

    if has_customer and has_case:
        adapters = [MockCRMAdapter(), MockERPAdapter(), MockCaseAdapter()]
        adapter_results = [adapter.fetch(query=query, context_package=context_package) for adapter in adapters]
        crm_result = next(item for item in adapter_results if item["adapter"] == "mock_crm")
        erp_result = next(item for item in adapter_results if item["adapter"] == "mock_erp")
        case_result = next(item for item in adapter_results if item["adapter"] == "mock_case")
        return {
            "metric_name": "customer_case_status",
            "result": {
                "active_customer_count": crm_result["signals"]["active_customer_count"],
                "open_case_count": case_result["signals"]["open_case_count"],
                "high_priority_open_cases": case_result["signals"]["high_priority_open_cases"],
                "trend": crm_result["signals"]["trend"],
                "change_pct": erp_result["signals"]["change_pct"],
                "top_case_categories": case_result["signals"]["top_case_categories"],
            },
            "source_systems": ["CRM", "ERP", "CaseSystem"],
            "provenance": adapter_results,
            "notes": [
                "示範用 customer + case adapter-based mock data",
                "查詢同時套用 customer scope 與 case scope"
            ]
        }

    if has_customer:
        adapters = [MockCRMAdapter(), MockERPAdapter()]
        adapter_results = [adapter.fetch(query=query, context_package=context_package) for adapter in adapters]
        crm_result = next(item for item in adapter_results if item["adapter"] == "mock_crm")
        erp_result = next(item for item in adapter_results if item["adapter"] == "mock_erp")
        return {
            "metric_name": "active_customer_status",
            "result": {
                "active_customer_count": crm_result["signals"]["active_customer_count"],
                "trend": crm_result["signals"]["trend"],
                "change_pct": erp_result["signals"]["change_pct"],
                "top_segments": crm_result["signals"]["top_segments"],
            },
            "source_systems": ["CRM", "ERP"],
            "provenance": adapter_results,
            "notes": [
                "示範用 adapter-based mock data",
                "active customer 口徑依 Customer term card：最近 180 天內至少一項有效互動"
            ]
        }
    return {
        "metric_name": "unknown",
        "result": {},
        "provenance": [],
        "notes": ["no mock datasource matched"]
    }


def _build_answer_draft(context_package: dict[str, Any], data_result: dict[str, Any]) -> dict[str, Any]:
    result = data_result.get("result", {})
    metric_name = data_result.get("metric_name")
    if metric_name == "customer_case_status":
        summary = (
            f"目前 active customer 共 {result.get('active_customer_count')} 家，"
            f"open case 共 {result.get('open_case_count')} 件，其中高優先 {result.get('high_priority_open_cases')} 件。"
        )
    else:
        summary = f"目前 active customer 共 {result.get('active_customer_count')} 家，趨勢為 {result.get('trend')}。"
    return {
        "summary": summary,
        "explanation_hints": [
            "使用 term card 中的定義解釋數字口徑",
            "優先引用 context package 中的 source_authority_rule",
            "若涉及財務敏感資訊，先檢查 warnings",
        ],
    }


def run_query_pipeline(query: str, user_id: str) -> dict[str, Any]:
    context_package = resolve_context_package(query=query, user_id=user_id)
    data_result = _fetch_mock_data(context_package=context_package, query=query)
    answer_draft = _build_answer_draft(context_package=context_package, data_result=data_result)
    llm_prompt = build_llm_prompt(context_package=context_package, data_result=data_result)
    return {
        "context_package": context_package,
        "data_result": data_result,
        "answer_draft": answer_draft,
        "llm_prompt": llm_prompt,
    }



from rich import print as rprint

payload = run_query_pipeline("幫我看最近 active customer 狀況", "sales_manager_demo")
rprint(payload)