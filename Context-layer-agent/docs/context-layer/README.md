# Context Layer Project Docs

## Contents
- `architecture.md` — Mermaid flowchart and architectural layers
- `sdd.md` — system design document
- `tdd.md` — technical design document
- `project-development-guide.md` — overall development guide and next steps
- `../plans/2026-03-31-context-resolver-poc.md` — implementation plan used for the PoC

## Current PoC Scope
- Customer term support
- Case term support
- user context support
- resolver heuristics
- adapter-based data fetch
- deterministic prompt builder
- test coverage for key paths

## Verification
```bash
python3 -m unittest tests.test_context_resolver -v
```

## Demo
```bash
python3 tools/context_demo.py --user-id sales_manager_demo --query "請分析最近 active customer 的營收與付款狀況"
```
