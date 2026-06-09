# Context Layer 架構改善 — 導入 Agno Agent Framework

將現有硬編碼的 if-else pipeline 改為 **Agno Agent 驅動的動態工具呼叫架構**，讓 LLM 自行決定該呼叫哪些資料源 Adapter。

## Proposed Changes

### 1. 安裝依賴

```bash
pip install agno litellm
```

---

### 2. Adapter → Agno Tool Functions

#### [MODIFY] [base.py](file:///d:/my_note/_300-A主題/Agent/context-layer-docs-2026-03-31/tools/adapters/base.py)
- 保留 [BaseAdapter](file:///d:/my_note/_300-A%E4%B8%BB%E9%A1%8C/Agent/context-layer-docs-2026-03-31/tools/adapters/base.py#7-13) 作為底層抽象類別（向後相容）

#### [NEW] [agno_tools.py](file:///d:/my_note/_300-A主題/Agent/context-layer-docs-2026-03-31/tools/adapters/agno_tools.py)
- 將 [MockCRMAdapter](file:///d:/my_note/_300-A%E4%B8%BB%E9%A1%8C/Agent/context-layer-docs-2026-03-31/tools/adapters/mock_crm.py#8-21)、[MockERPAdapter](file:///d:/my_note/_300-A%E4%B8%BB%E9%A1%8C/Agent/context-layer-docs-2026-03-31/tools/adapters/mock_erp.py#8-20)、[MockCaseAdapter](file:///d:/my_note/_300-A%E4%B8%BB%E9%A1%8C/Agent/context-layer-docs-2026-03-31/tools/adapters/mock_case.py#8-21) 各自封裝成 agno `@tool` 函式
- 每個 tool function 附帶清晰的 docstring，讓 LLM 能理解何時該呼叫
- 新增一個 [resolve_context](file:///d:/my_note/_300-A%E4%B8%BB%E9%A1%8C/Agent/context-layer-docs-2026-03-31/tools/context_resolver.py#49-105) tool，讓 Agent 可以自行查詢情境資訊

```python
from agno.tools import tool

@tool
def query_crm(query: str) -> str:
    """查詢 CRM 系統以獲取客戶相關資料，如 active customer 數量、趨勢、客戶分群等。
    當使用者問題涉及 customer（客戶）相關分析時呼叫此工具。"""
    ...

@tool
def query_erp(query: str) -> str:
    """查詢 ERP 系統以獲取訂單、出貨、業務數據變化等資料。
    當需要補充 change_pct 或 supporting_sources 等資訊時呼叫此工具。"""
    ...

@tool
def query_case_system(query: str) -> str:
    """查詢案件管理系統以獲取 open case 數量、高優先案件、案件分類等資料。
    當使用者問題涉及 case（案件）相關分析時呼叫此工具。"""
    ...

@tool
def resolve_context(query: str, user_id: str) -> str:
    """解析使用者情境，包含權限、商業名詞定義、資料口徑等。
    此工具必須在查詢資料前呼叫，以獲取正確的 context package。"""
    ...
```

---

### 3. Agent 主程式

#### [NEW] [agent_pipeline.py](file:///d:/my_note/_300-A主題/Agent/context-layer-docs-2026-03-31/tools/agent_pipeline.py)
核心檔案，用 Agno `Agent` 取代原本的 [context_pipeline.py](file:///D:/my_note/_300-A%E4%B8%BB%E9%A1%8C/Agent/context-layer-docs-2026-03-31/tools/context_pipeline.py) 的 if-else 路由邏輯：

```python
from agno.agent import Agent
from agno.models.litellm import LiteLLMOpenAI

model = LiteLLMOpenAI(
    id="TXC-LLM",
    api_key="AI.7u8i(O)P",
    base_url="http://192.168.37.71:32290",
    extra_body={'chat_template_kwargs': {'enable_thinking': False}},
)

agent = Agent(
    model=model,
    tools=[resolve_context, query_crm, query_erp, query_case_system],
    instructions=[system_prompt],  # 從 context_resolver 動態產生
    show_tool_calls=True,
    markdown=True,
)
```

Agent 的執行流程：
1. 先自動呼叫 [resolve_context](file:///d:/my_note/_300-A%E4%B8%BB%E9%A1%8C/Agent/context-layer-docs-2026-03-31/tools/context_resolver.py#49-105) 取得 context package（含權限、term 定義）
2. 根據 context package 中的 `data_sources` 與使用者問題，LLM **自行決定**呼叫哪些資料 tools
3. 將所有資料彙整後，由 LLM 生成最終回答

---

### 4. System Prompt 改善

#### [NEW] [system_prompt_builder.py](file:///d:/my_note/_300-A主題/Agent/context-layer-docs-2026-03-31/tools/system_prompt_builder.py)
- 基於原本的 [prompt_builder.py](file:///d:/my_note/_300-A%E4%B8%BB%E9%A1%8C/Agent/context-layer-docs-2026-03-31/tools/prompt_builder.py) 改寫，專為 Agent 模式設計
- System prompt 規範 Agent 的行為準則：必須先 resolve context、遵守 access control、引用 term card 定義等
- 加入 **output guardrails** 指令，要求 LLM 在回答中只引用工具返回的數據

---

### 5. 保留原始 Pipeline（向後相容）

#### [MODIFY] [context_pipeline.py](file:///d:/my_note/_300-A主題/Agent/context-layer-docs-2026-03-31/tools/context_pipeline.py)
- 原始檔案**不刪除**，保留作為非 Agent 模式的 fallback
- 底部的 [run_query_pipeline](file:///d:/my_note/_300-A%E4%B8%BB%E9%A1%8C/Agent/context-layer-docs-2026-03-31/tools/context_pipeline.py#95-106) 測試呼叫移除

---

### 6. 專案結構（改善後）

```
tools/
├── adapters/
│   ├── base.py              # 保留（向後相容）
│   ├── mock_crm.py          # 保留（底層 adapter）
│   ├── mock_erp.py          # 保留
│   ├── mock_case.py         # 保留
│   └── agno_tools.py        # [NEW] — agno @tool 封裝
├── context_data/            # 不變
├── context_resolver.py      # 不變
├── prompt_builder.py        # 保留（向後相容）
├── context_pipeline.py      # 保留（原始 pipeline, 非 Agent 模式 fallback）
├── system_prompt_builder.py # [NEW] — Agent 專用 system prompt
└── agent_pipeline.py        # [NEW] — 主入口：Agno Agent pipeline
```

## User Review Required

> [!IMPORTANT]
> **LLM 連線**：Agent 會連接 `http://192.168.37.71:32290` 呼叫 TXC-LLM。請確認此服務目前可以正常存取，且模型支援 **Tool Calling / Function Calling** 功能（Qwen3.5 需要確認是否支援）。

> [!NOTE]
> 原始的 [context_pipeline.py](file:///D:/my_note/_300-A%E4%B8%BB%E9%A1%8C/Agent/context-layer-docs-2026-03-31/tools/context_pipeline.py) 和所有現有 adapters **完全保留**，不會受到影響。新架構是**新增**而非取代。

## Verification Plan

### Automated Tests

1. **現有測試**：從專案根目錄執行（確保 `sys.path` 正確）：
   ```bash
   cd d:\my_note\_300-A主題\Agent\context-layer-docs-2026-03-31
   python -m pytest tests/test_context_resolver.py -v
   ```
   驗證原始 pipeline 未被破壞。

2. **新增 Agent 測試** `tests/test_agent_pipeline.py`：
   - 測試 agno tools 是否能獨立執行並返回正確格式
   - 測試 [resolve_context](file:///d:/my_note/_300-A%E4%B8%BB%E9%A1%8C/Agent/context-layer-docs-2026-03-31/tools/context_resolver.py#49-105) tool 是否正確返回 context package
   - 若 LLM 服務不可用，tool functions 仍可單獨以 unit test 驗證

### Manual Verification
1. 執行 `python tools/agent_pipeline.py`，觀察 Agent 的 tool calling 過程（`show_tool_calls=True` 會輸出每一步呼叫了什麼工具）
2. 與原始 pipeline 的輸出對比，確認數據一致性
