# Context Resolver PoC Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a minimal working PoC that dynamically assembles a context package from term registry, user context registry, and lightweight resolver heuristics.

**Architecture:** Use JSON files as the first registry backend and a small Python resolver module to keep the PoC lightweight. The resolver will identify terms from a query, apply heuristics, merge user context and access filters, and output a deterministic context package plus optional data-source hints.

**Tech Stack:** Python 3, JSON, unittest

---

### Task 1: Create failing resolver test

**Files:**
- Create: `tests/test_context_resolver.py`
- Create: `tools/context_resolver.py`
- Create: `tools/context_data/terms/customer.json`
- Create: `tools/context_data/users/sales_manager_demo.json`
- Create: `tools/context_data/resolver_heuristics.json`

**Step 1: Write the failing test**
- Test that a query mentioning `active customer` by a sales manager resolves:
  - `Customer` term
  - `active_rule`
  - user context
  - access context
  - suggested source systems

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest tests.test_context_resolver -v`
Expected: FAIL because resolver module or implementation is missing.

**Step 3: Write minimal implementation**
- Implement term matching, heuristic matching, user loading, and package assembly.

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest tests.test_context_resolver -v`
Expected: PASS.

### Task 2: Add access-filter behavior test

**Files:**
- Modify: `tests/test_context_resolver.py`
- Modify: `tools/context_resolver.py`

**Step 1: Write the failing test**
- Test that finance-related query flags access restriction for a user without finance access.

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest tests.test_context_resolver -v`
Expected: FAIL with missing access filter behavior.

**Step 3: Write minimal implementation**
- Add domain keyword detection and access warning generation.

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest tests.test_context_resolver -v`
Expected: PASS.

### Task 3: Add CLI demo runner

**Files:**
- Create: `tools/context_demo.py`
- Modify: `tools/context_resolver.py`

**Step 1: Write the failing test**
- Test CLI helper indirectly by verifying resolver output can be serialized to JSON.

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest tests.test_context_resolver -v`
Expected: FAIL if serialization or output fields are incomplete.

**Step 3: Write minimal implementation**
- Add a tiny CLI that accepts user id + query and prints JSON package.

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest tests.test_context_resolver -v`
Expected: PASS.

### Task 4: Add end-to-end mock query pipeline

**Files:**
- Modify: `tests/test_context_resolver.py`
- Create: `tools/context_pipeline.py`
- Create: `tools/context_data/mock_metrics/customer_metrics.json`

**Step 1: Write the failing test**
- Test that a query for active customer status returns a full payload containing:
  - context package
  - mock data results
  - answer draft metadata

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest tests.test_context_resolver -v`
Expected: FAIL because the pipeline module or answer assembly does not exist.

**Step 3: Write minimal implementation**
- Add a pipeline function that:
  - resolves context package
  - selects mock data source(s)
  - returns a simple answer payload ready for an LLM layer

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest tests.test_context_resolver -v`
Expected: PASS.

### Task 5: Add LLM prompt builder

**Files:**
- Modify: `tests/test_context_resolver.py`
- Create: `tools/prompt_builder.py`
- Modify: `tools/context_pipeline.py`

**Step 1: Write the failing test**
- Test that the end-to-end pipeline includes an `llm_prompt` string containing:
  - the original query
  - active customer definition
  - mock metric result
  - response style hint

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest tests.test_context_resolver -v`
Expected: FAIL because prompt builder is missing.

**Step 3: Write minimal implementation**
- Add prompt builder logic that creates a deterministic prompt from context package + data result.

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest tests.test_context_resolver -v`
Expected: PASS.

### Task 6: Add adapter layer v1

**Files:**
- Modify: `tests/test_context_resolver.py`
- Create: `tools/adapters/base.py`
- Create: `tools/adapters/mock_crm.py`
- Create: `tools/adapters/mock_erp.py`
- Modify: `tools/context_pipeline.py`

**Step 1: Write the failing test**
- Test that the pipeline reports adapter names and data provenance from CRM/ERP adapters instead of direct JSON-only fetch.

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest tests.test_context_resolver -v`
Expected: FAIL because adapter metadata is missing.

**Step 3: Write minimal implementation**
- Add simple adapter classes and route customer query fetch through them.

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest tests.test_context_resolver -v`
Expected: PASS.

### Task 7: Add Case domain support

**Files:**
- Modify: `tests/test_context_resolver.py`
- Create: `tools/context_data/terms/case.json`
- Create: `tools/adapters/mock_case.py`
- Modify: `tools/context_data/resolver_heuristics.json`
- Modify: `tools/context_resolver.py`
- Modify: `tools/context_pipeline.py`
- Modify: `tools/prompt_builder.py`

**Step 1: Write the failing test**
- Test that a query mentioning customer + case resolves both terms and returns case metrics plus conflict notes.

**Step 2: Run test to verify it fails**
Run: `python3 -m unittest tests.test_context_resolver -v`
Expected: FAIL because Case support is missing.

**Step 3: Write minimal implementation**
- Add Case term card, adapter, resolver domain context, and merged pipeline output.

**Step 4: Run test to verify it passes**
Run: `python3 -m unittest tests.test_context_resolver -v`
Expected: PASS.
