# Context Layer Architecture

## Mermaid Flowchart

```mermaid
flowchart TD
    U[User Query] --> QP[Query Parser / Intent Detector]
    QP --> RT[Resolved Terms]
    QP --> RI[Resolved Intent]
    QP --> UID[User Identity]

    RT --> TR[Term Registry]
    UID --> UR[User Context Registry]
    RT --> RH[Resolver Heuristics]
    RI --> RH
    UR --> AF[Access Filter]

    TR --> CP[Context Package Builder]
    RH --> CP
    UR --> CP
    AF --> CP

    CP --> DS[Data Source Planner]
    DS --> CRM[CRM Adapter]
    DS --> ERP[ERP Adapter]
    DS --> CASE[Case Adapter]
    DS --> DOCS[Document / Policy Retriever]

    CRM --> MR[Merge / Normalize Results]
    ERP --> MR
    CASE --> MR
    DOCS --> MR

    CP --> PB[Prompt Builder]
    MR --> PB
    PB --> LLM[LLM / AI Layer]
    LLM --> ANS[Answer / Action Draft]

    MR --> PR[Provenance Log]
    CP --> PR
    PB --> PR

    ANS --> GUARD[Output Guardrails / Access Check]
    GUARD --> OUT[User Response]
```

## Layer Summary

1. **Query Parser / Intent Detector**
   - Extracts intent, time windows, and candidate terms from natural language.
2. **Term Registry**
   - Stores definitions like Customer, Case, lifecycle rules, source authority, and cross-domain notes.
3. **User Context Registry**
   - Stores role, department, access scope, response preferences, and metric lens.
4. **Resolver Heuristics**
   - Determines what context must be injected for a given query pattern.
5. **Context Package Builder**
   - Produces a compact context bundle instead of sending the full registry to the model.
6. **Data Source Planner + Adapters**
   - Selects and queries CRM / ERP / Case / documents using adapters.
7. **Merge / Normalize Results**
   - Produces a single domain result plus provenance.
8. **Prompt Builder**
   - Assembles a deterministic LLM prompt from query + context + data.
9. **Guardrails**
   - Prevents leaking restricted domains and enforces access.

## Current PoC Files

- `tools/context_resolver.py`
- `tools/context_pipeline.py`
- `tools/prompt_builder.py`
- `tools/adapters/base.py`
- `tools/adapters/mock_crm.py`
- `tools/adapters/mock_erp.py`
- `tools/adapters/mock_case.py`
- `tools/context_data/terms/customer.json`
- `tools/context_data/terms/case.json`
- `tools/context_data/users/sales_manager_demo.json`
- `tools/context_data/resolver_heuristics.json`
- `tests/test_context_resolver.py`
