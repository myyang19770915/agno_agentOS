from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "context_data"
TERMS_DIR = DATA_DIR / "terms"
USERS_DIR = DATA_DIR / "users"
HEURISTICS_FILE = DATA_DIR / "resolver_heuristics.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _detect_intent(query: str) -> str:
    lowered = query.lower()
    analysis_markers = ["看", "分析", "狀況", "多少", "趨勢", "compare", "analysis"]
    if any(marker in lowered for marker in analysis_markers):
        return "analysis"
    return "general"


def _resolve_terms(query: str, heuristics: dict[str, Any]) -> list[str]:
    lowered = query.lower()
    resolved = []
    for rule in heuristics.get("term_triggers", []):
        if any(keyword.lower() in lowered for keyword in rule.get("keywords", [])):
            resolved.append(rule["term"])
    return list(dict.fromkeys(resolved))


def _load_terms(term_names: list[str]) -> dict[str, Any]:
    terms = {}
    for term_name in term_names:
        slug = term_name.lower().replace(" ", "_")
        path = TERMS_DIR / f"{slug}.json"
        if path.exists():
            terms[term_name] = _load_json(path)
    return terms


def _load_user(user_id: str) -> dict[str, Any]:
    return _load_json(USERS_DIR / f"{user_id}.json")


def resolve_context_package(query: str, user_id: str) -> dict[str, Any]:
    heuristics = _load_json(HEURISTICS_FILE)
    user = _load_user(user_id)
    resolved_terms = _resolve_terms(query, heuristics)
    term_docs = _load_terms(resolved_terms)

    data_sources = []
    warnings = []
    domain_context: dict[str, Any] = {}

    customer = term_docs.get("Customer")
    if customer:
        domain_context["customer_scope"] = customer["term_scope"]
        domain_context["active_rule"] = customer["lifecycle"]["active_rule"]
        domain_context.setdefault("source_authority_rule", {})["Customer"] = customer["source_authority_rule"]
        for source in customer.get("source_systems", []):
            if source not in data_sources:
                data_sources.append(source)

    case = term_docs.get("Case")
    if case:
        domain_context["case_scope"] = case["term_scope"]
        domain_context.setdefault("source_authority_rule", {})["Case"] = case["source_authority_rule"]
        domain_context["case_status_dimensions"] = case.get("status_dimensions", {})
        for source in case.get("source_systems", []):
            if source not in data_sources:
                data_sources.append(source)

    for rule in heuristics.get("cross_domain_rules", []):
        if all(term in resolved_terms for term in rule.get("terms", [])):
            domain_context.setdefault("cross_domain_notes", []).append(rule["note"])

    lowered = query.lower()
    finance_keywords = heuristics.get("finance_keywords", [])
    if any(keyword.lower() in lowered for keyword in finance_keywords):
        if not user["access_context"].get("finance_access_flag"):
            warnings.append("finance access restricted: query may require filtered or denied financial details")

    return {
        "query_context": {
            "original_query": query,
            "intent": _detect_intent(query),
            "resolved_terms": resolved_terms,
        },
        "domain_context": domain_context,
        "user_context": {
            "department": user.get("department"),
            "role": user.get("role"),
            "preferred_metric_lens": user.get("preference_context", {}).get("preferred_metric_lens"),
            "default_customer_scope": user.get("preference_context", {}).get("default_customer_scope"),
            "response_style": user.get("preference_context", {}).get("response_style"),
        },
        "access_context": user.get("access_context", {}),
        "data_sources": data_sources,
        "warnings": warnings,
    }
