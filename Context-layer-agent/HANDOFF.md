# Context Layer 開發交接文件

> 產生時間：2026-03-31 14:21

---

## 1. 專案概述

本專案是一個**企業 AI 語意情境層 (Semantic & Context Layer)** 雛型，核心功能是在將使用者問題送給 LLM 之前，先根據使用者身分、權限及商業名詞定義，組裝完整的 context package 與 structured prompt。

---

## 2. 現有專案結構

```
context-layer-docs-2026-03-31/
├── docs/                           # 文件（context-layer, plans）
├── tests/
│   └── test_context_resolver.py    # 現有單元測試（7 個 test cases）
└── tools/
    ├── adapters/
    │   ├── base.py                 # 抽象基底類別 BaseAdapter
    │   ├── mock_crm.py             # Mock CRM adapter（回傳 active_customer_count 等）
    │   ├── mock_erp.py             # Mock ERP adapter（回傳 change_pct 等）
    │   └── mock_case.py            # Mock Case adapter（回傳 open_case_count 等）
    ├── context_data/
    │   ├── resolver_heuristics.json # 名詞觸發規則、跨 domain 規則、finance keywords
    │   ├── terms/
    │   │   ├── customer.json       # Customer term card（scope, active_rule, source_authority）
    │   │   └── case.json           # Case term card（status_dimensions, cross_domain_notes）
    │   └── users/
    │       └── sales_manager_demo.json  # 測試用 user profile（權限、偏好）
    ├── context_resolver.py         # 核心：根據 query + user_id 解析 context package
    ├── prompt_builder.py           # 將 context + data 組裝為 LLM prompt
    └── context_pipeline.py         # 主流程：串接 resolver → adapters → prompt builder
```

---

## 3. 已完成的工作

### ✅ Bug Fix
- `context_pipeline.py` 加入 `sys.path.append` 修正 `ModuleNotFoundError`

### ✅ 架構分析（見 `architecture_analysis.md`）
**優點：**
- 名詞定義解耦（Semantic Layer）符合資料治理需求
- 有權限控管機制（access_context + finance warning）
- Adapter Pattern 可擴充

**需改善：**
1. **硬編碼路由 (if-else)**：應改用 Agent Tool Calling
2. **同步阻塞**：多 adapter 應平行呼叫
3. **靜態 JSON**：企業應接 AD/SSO 及 Data Catalog
4. **缺 Output Guardrails**：需加事實查核層

---

## 4. 待實作計畫（已核准）

### 目標
用 **Agno Agent Framework** 取代 if-else 路由，讓 LLM 動態決定呼叫哪些工具。

### 需安裝的依賴

```bash
pip install agno litellm rich
```

### LLM 配置

```python
from agno.agent import Agent
from agno.models.litellm import LiteLLMOpenAI

model = LiteLLMOpenAI(
    id="TXC-LLM",
    api_key="AI.7u8i(O)P",
    base_url="http://192.168.37.71:32290",
    extra_body={
        'chat_template_kwargs': {'enable_thinking': False}
    },
)
```

### 需新增的 3 個檔案

#### 📄 `tools/adapters/agno_tools.py`
將現有 3 個 Adapter + context_resolver 包裝成 agno `@tool` 函式：
- `resolve_context(query, user_id)` → 呼叫 `context_resolver.resolve_context_package()`
- `query_crm(query)` → 呼叫 `MockCRMAdapter().fetch()`
- `query_erp(query)` → 呼叫 `MockERPAdapter().fetch()`
- `query_case_system(query)` → 呼叫 `MockCaseAdapter().fetch()`

每個 tool function 需附帶清晰的中文 docstring，讓 LLM 知道何時呼叫。

#### 📄 `tools/system_prompt_builder.py`
Agent 專用 system prompt，包含：
- 行為準則：必須先 resolve context、遵守 access control
- 引用規範：回答需引用 term card 定義
- Output guardrails：只能引用工具返回的數據，不捏造

#### 📄 `tools/agent_pipeline.py`
主入口，建立 Agno `Agent`，掛載上述 tools，執行 `agent.print_response(query)`。

### 專案結構（改善後）

```
tools/
├── adapters/
│   ├── base.py              # 保留
│   ├── mock_crm.py          # 保留
│   ├── mock_erp.py          # 保留
│   ├── mock_case.py         # 保留
│   └── agno_tools.py        # [NEW]
├── context_data/            # 不變
├── context_resolver.py      # 不變
├── prompt_builder.py        # 保留（非 Agent fallback）
├── context_pipeline.py      # 保留（非 Agent fallback）
├── system_prompt_builder.py # [NEW]
└── agent_pipeline.py        # [NEW] 主入口
```

---

## 5. 測試指令

```bash
# 現有測試（從專案根目錄執行）
python -m pytest tests/test_context_resolver.py -v

# 原始 pipeline 手動測試
python tools/context_pipeline.py

# 新 Agent pipeline（實作完成後）
python tools/agent_pipeline.py
```

---

## 6. 關鍵設計決策備忘

| 決策 | 結論 |
|------|------|
| LLM 是否支援 Tool Calling | ✅ 使用者確認 Qwen3.5 支援 |
| Agent 框架 | agno + LiteLLMOpenAI |
| 是否保留原始 pipeline | ✅ 保留作為 fallback |
| 原有 adapter 是否修改 | ❌ 不修改，新增 agno_tools.py 封裝 |
