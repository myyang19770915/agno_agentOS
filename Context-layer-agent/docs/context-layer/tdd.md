# TDD.md - Technical Design Document

## 1. Purpose
This document describes the technical design of the Context Layer PoC implementation in the workspace.

## 2. Code Structure
### Core orchestration
- `tools/context_resolver.py`
  - loads registries
  - resolves terms
  - applies heuristics
  - builds context package
- `tools/context_pipeline.py`
  - runs end-to-end query pipeline
  - fetches adapter data
  - merges results
  - creates answer draft
  - calls prompt builder
- `tools/prompt_builder.py`
  - builds deterministic LLM prompt

### Adapters
- `tools/adapters/base.py`
- `tools/adapters/mock_crm.py`
- `tools/adapters/mock_erp.py`
- `tools/adapters/mock_case.py`

### Registry data
- `tools/context_data/terms/customer.json`
- `tools/context_data/terms/case.json`
- `tools/context_data/users/sales_manager_demo.json`
- `tools/context_data/resolver_heuristics.json`

### Tests
- `tests/test_context_resolver.py`

## 3. Context Package Schema
Current output shape:
```json
{
  "query_context": {
    "original_query": "string",
    "intent": "analysis|general",
    "resolved_terms": ["Customer", "Case"]
  },
  "domain_context": {
    "customer_scope": "string",
    "active_rule": "string",
    "case_scope": "string",
    "source_authority_rule": {},
    "cross_domain_notes": []
  },
  "user_context": {
    "department": "string",
    "role": "string",
    "preferred_metric_lens": "string",
    "default_customer_scope": "string",
    "response_style": "string"
  },
  "access_context": {},
  "data_sources": [],
  "warnings": []
}
```

## 4. Adapter Contract v1
Each adapter must implement:
```python
class BaseAdapter:
    name: str
    def fetch(self, query: str, context_package: dict) -> dict:
        ...
```

Expected adapter return shape:
```json
{
  "adapter": "mock_crm",
  "domain": "customer",
  "signals": {}
}
```

## 5. Merge Strategy
### Customer-only query
- CRM provides customer count/trend/segments
- ERP provides supporting numeric change signals
- merged metric: `active_customer_status`

### Customer + Case query
- CRM provides customer metrics
- ERP provides supporting change metrics
- Case adapter provides open case metrics
- merged metric: `customer_case_status`

## 6. Prompt Builder Strategy
Prompt builder must include:
- original query
- intent
- relevant domain scopes
- active rule and case scope when applicable
- user role and response style
- key data metrics
- warnings
- instruction to avoid hallucination

## 7. Testing Strategy
### Current tests
- resolve customer active context
- enforce finance warning for restricted user
- ensure JSON serializability
- ensure LLM prompt contains key context fields
- ensure adapter provenance exists
- ensure customer + case multi-domain flow works

### Commands
```bash
python3 -m unittest tests.test_context_resolver -v
python3 tools/context_demo.py --user-id sales_manager_demo --query "請分析最近 active customer 的營收與付款狀況"
```

## 8. Known Technical Gaps
- parser is keyword-based, not model-assisted
- no persistence layer yet
- no real DB/API connectors
- no caching layer
- no ranking / hybrid retrieval for documents
- no fine-grained row-level security

## 9. Recommended Next Technical Steps
1. Add real adapter interfaces for CRM / ERP / Case system
2. Add Employee and Internal Service Customer term cards
3. Add document retrieval for SOP / policy context
4. Add a resolver planner that handles ambiguity explicitly
5. Add prompt templates per intent (analysis / explanation / action)
6. Add evaluation and regression test fixtures
