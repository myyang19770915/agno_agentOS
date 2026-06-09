from __future__ import annotations

from typing import Any


def build_llm_prompt(context_package: dict[str, Any], data_result: dict[str, Any]) -> str:
    query = context_package["query_context"]["original_query"]
    intent = context_package["query_context"]["intent"]
    domain = context_package.get("domain_context", {})
    customer_scope = domain.get("customer_scope")
    case_scope = domain.get("case_scope")
    active_rule = domain.get("active_rule")
    cross_domain_notes = domain.get("cross_domain_notes", [])
    user_role = context_package.get("user_context", {}).get("role")
    response_style = context_package.get("user_context", {}).get("response_style")
    data_sources = ", ".join(context_package.get("data_sources", []))
    warnings = context_package.get("warnings", [])

    result = data_result.get("result", {})
    active_customer_count = result.get("active_customer_count")
    trend = result.get("trend")
    change_pct = result.get("change_pct")
    open_case_count = result.get("open_case_count")
    high_priority_open_cases = result.get("high_priority_open_cases")

    warning_text = "；".join(warnings) if warnings else "無"
    cross_notes_text = "；".join(cross_domain_notes) if cross_domain_notes else "無"

    return f"""你是一個企業 AI 助理。請根據以下 context package 與資料結果回答問題。

[User Query]
{query}

[Intent]
{intent}

[Domain Context]
- Customer scope: {customer_scope}
- Case scope: {case_scope}
- Active rule: {active_rule}
- Data sources: {data_sources}
- Cross-domain notes: {cross_notes_text}

[User Context]
- Role: {user_role}
- Response style: {response_style}

[Data Result]
- active_customer_count: {active_customer_count}
- open_case_count: {open_case_count}
- high_priority_open_cases: {high_priority_open_cases}
- trend: {trend}
- change_pct: {change_pct}

[Warnings]
- {warning_text}

[Instructions]
1. 先用符合 {response_style} 的方式回答。
2. 說明數字口徑時，必須引用 active customer 定義；若涉及 open case，也要說明 case scope。
3. 若有 warning，先在回答中標記限制。
4. 不要捏造 context package 與 data result 之外的事實。
"""
