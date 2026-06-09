# Project Development Guide

## 1. Project Goal
Create a reusable context-layer foundation for enterprise AI so that answers are driven by:
- business term definitions
- user context
- access rules
- adapter-based data retrieval
- prompt construction with provenance

## 2. Current Deliverables
### Documentation
- `docs/context-layer/architecture.md`
- `docs/context-layer/sdd.md`
- `docs/context-layer/tdd.md`
- `docs/context-layer/project-development-guide.md`
- `docs/plans/2026-03-31-context-resolver-poc.md`

### PoC Code
- resolver
- pipeline
- prompt builder
- adapters
- tests

## 3. Working Conventions
### Registry-first
Before adding a new business domain, first define:
- term card
- user impact
- source authority
- access constraints

### Adapter-first integration
Do not connect AI directly to raw external systems. Always go through adapters.

### Compact-context principle
Only inject minimal relevant context into the model.

### Provenance required
Every merged result should preserve adapter/source lineage.

## 4. Recommended Domain Expansion Order
1. Customer ✅
2. Case ✅
3. Employee
4. Internal Service Customer
5. Shipment
6. Policy / SOP / handbook rules

## 5. Recommended Delivery Phases
### Phase 1: Metadata foundation
- finalize term cards
- finalize user context registry
- finalize resolver heuristics

### Phase 2: Retrieval and orchestration
- improve parser and planner
- support more query intents
- add hybrid retrieval for docs

### Phase 3: Real integrations
- CRM adapter
- ERP adapter
- Case adapter
- policy/document adapter

### Phase 4: Governance and evaluation
- review workflow
- definition versioning
- evaluation suite
- regression tests
- answer audit logs

## 6. File Ownership Guidance
### Business-owned content
- term definitions
- lifecycle rules
- non-examples
- governance notes

### Tech-owned content
- adapters
- pipeline
- prompt builder
- tests
- deployment / monitoring

### Shared governance
- resolver heuristics
- access rules
- cross-domain conflict notes

## 7. Suggested Folder Growth
```text
docs/context-layer/
  architecture.md
  sdd.md
  tdd.md
  project-development-guide.md

tools/
  context_resolver.py
  context_pipeline.py
  prompt_builder.py
  adapters/
  context_data/

tests/
  test_context_resolver.py
```

## 8. Development Checklist for New Domain
When adding a new domain, e.g. Employee:
1. Create term card JSON
2. Update resolver heuristics
3. Add adapter
4. Add pipeline merge logic
5. Extend prompt builder
6. Add tests
7. Update docs

## 9. Backup and Release Guidance
After any major milestone:
1. run tests
2. update docs
3. package docs + source
4. sync to cloud backup
5. record milestone in memory or project notes

## 10. Immediate Next Steps
- define real adapter contract v1
- add Employee domain
- add policy / handbook retriever
- support multi-role user cards
- add final answer generator for real LLM call
