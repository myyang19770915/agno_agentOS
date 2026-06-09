
## 1. 系統規格 (System Specifications)

### A. 技術棧 (Tech Stack)

- **Framework:** Agno (Python)
    
- **Relational DB:** PostgreSQL (用於結構化數據與統計)
    
- **Vector DB:** Qdrant (用於 Hybrid Search: Dense + Sparse)
    
- **LLM:** GPT-4o 或 Claude 3.5 Sonnet
    
- **Embedding:** OpenAI `text-embedding-3-small` 或 `BGE-M3`
    
- **Orchestrator:** FastAPI (用於 API 封裝)
    

### B. 資料對齊要求 (Data Alignment)

- 所有存入 Qdrant 的 `Payload` 必須包含 `pg_id` (Postgres UUID/PK)。
    
- Qdrant 必須啟用 `Hybrid Search`（需配置 `Sparse Vector` 索引）。
    

---

## 2. 專案架構 (File Structure)

Plaintext

```
hybrid-rag-agent/
├── app/
│   ├── core/
│   │   ├── database.py       # Postgres 連線與 SQL 執行
│   │   ├── vector_db.py     # Qdrant 連線與 Hybrid 檢索邏輯
│   │   └── rrf.py           # RRF 融合演算法
│   ├── tools/
│   │   ├── analytics_tool.py # SQL 統計工具 (Text-to-SQL)
│   │   └── retrieval_tool.py # 混合檢索工具 (SQL + Qdrant + RRF)
│   ├── agents/
│   │   └── router_agent.py   # 主編排 Agent (Agno)
│   └── main.py              # FastAPI 入口
├── data/                    # 資料清洗與 Ingestion 腳本
├── requirements.txt
└── .env
```

---

## 3. 核心實作代碼框架 (Code Framework)

### A. RRF 融合邏輯 (`app/core/rrf.py`)

Python

```
def reciprocal_rank_fusion(results_list: list[list[str]], k: int = 60):
    """
    results_list: 包含多個已排序 ID 列表的列表
    回傳: 排序後的 (ID, Score) 列表
    """
    scores = {}
    for results in results_list:
        for rank, doc_id in enumerate(results, start=1):
            if doc_id not in scores:
                scores[doc_id] = 0
            scores[doc_id] += 1 / (k + rank)
    
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

### B. 混合檢索工具 (`app/tools/retrieval_tool.py`)

此工具封裝了 **「全都要」** 的邏輯：

Python

```
from agno.agent import Agent
from app.core.rrf import reciprocal_rank_fusion

def unified_hybrid_search(query: str, top_k: int = 5):
    """
    1. 執行 Qdrant Hybrid Search (Vector + BM25)
    2. 執行 Postgres 關鍵字匹配 (SQL LIKE/tsvector)
    3. 執行 RRF 融合並回傳 Context
    """
    # 這裡實作雙路檢索邏輯
    # qdrant_ids = vector_db.hybrid_search(query)
    # sql_ids = postgres_db.keyword_search(query)
    
    # final_ids = reciprocal_rank_fusion([qdrant_ids, sql_ids])
    # return fetch_content_by_ids(final_ids[:top_k])
```

### C. Agno Agent 配置 (`app/agents/router_agent.py`)

Python

```
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from app.tools.analytics_tool import postgres_analytics_tool
from app.tools.retrieval_tool import unified_hybrid_search

retriever_agent = Agent(
    name="Hybrid Intelligence Agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[postgres_analytics_tool, unified_hybrid_search],
    instructions=[
        "意圖識別優先級：",
        "1. 若問題涉及計算、總和、平均、統計、或特定結構化篩選（如：某日期的訂單），請調用 postgres_analytics_tool。",
        "2. 若問題涉及概念描述、原因分析、建議、或需要參考文檔，請調用 unified_hybrid_search。",
        "3. 若問題涉及兩者，請先調用工具1獲取數據，再調用工具2獲取背景，最後綜合回答。",
        "4. 針對 Edge Case（如問題模糊），請先反思（Thought）並向使用者確認，不要盲目搜尋。"
    ],
    show_tool_calls=True,
    markdown=True
)
```

---

## 4. 給 Coding Agent 的開發指令 (Prompt for AI)

> **"請根據以下規格開發一個基於 Agno 框架的 AI Agent 系統：**
> 
> 1. **實作目標：** 建立一個能自動路由『統計查詢』與『知識檢索』的 Agent。
>     
> 2. **核心元件：**
>     
>     - 使用 **Qdrant** 進行 `Dense + Sparse` 混合搜尋。
>         
>     - 使用 **PostgreSQL** 進行數據統計與精確過濾。
>         
>     - 實作 **RRF 演算法**，將 Qdrant 與 Postgres 的檢索結果進行融合。
>         
> 3. **路由邏輯：**
>     
>     - 當用戶詢問數字/趨勢時，生成 SQL 執行。
>         
>     - 當用戶詢問內容時，執行 RRF 混合檢索。
>         
> 4. **邊緣案例處理：** > * 加入 Pydantic 模型驗證 Tool 的輸入參數。
>     
>     - 實作 ReAct 邏輯，讓 Agent 在檢索結果不滿意時能自動重試。



**「帶約束的鏈式檢索 (Chained & Constrained Retrieval)」**。

這種做法能解決向量搜尋最常見的「撈過界」問題。例如：使用者問「台北分公司的合約風險」，如果不先從 SQL 篩選出 `branch='Taipei'` 的 ID，向量資料庫可能會撈出「台中分公司」但語意極度相似的合約。

以下是針對 **「意圖拆解 + SQL 篩選連動」** 修正後的架構與開發規格。

---

## 1. 修正後的系統工作流 (Workflow)

這個流程要求 Agent 必須具備 **「多步推理」** 的能力，而不是單次路由。

1. **意圖分析 (Decomposition):** Agent 判斷問題是否包含「結構化過濾條件」（如時間、地區、特定對象）。
    
2. **第一步：精確過濾 (SQL Filter):** 調用 SQL 工具，僅回傳符合條件的 `pk_ids` (Primary Keys)。
    
3. **第二步：約束檢索 (Constrained Search):** 將 `pk_ids` 作為 `Filter` 參數傳給 Qdrant 進行語意搜尋。
    
4. **第三步：融合結果 (Fusion):** 執行 RRF，並將最終精煉後的 Context 給 LLM。
    

---

## 2. 核心代碼架構更新

### A. 支援過濾的檢索工具 (`app/tools/retrieval_tool.py`)

我們需要修改 `retrieval_tool`，讓它能接收來自 SQL 的 ID 列表。

Python

```
from typing import Optional, List
from qdrant_client import models

def unified_hybrid_search(
    query: str, 
    filter_ids: Optional[List[str]] = None, # 接收來自 SQL 的 PK
    top_k: int = 5
):
    """
    執行帶約束的混合檢索。
    :param filter_ids: 由 SQL 工具預先篩選出的 Primary Keys
    """
    # 構建 Qdrant 過濾器
    qdrant_filter = None
    if filter_ids:
        qdrant_filter = models.Filter(
            must=[
                models.HasIDCondition(has_id=filter_ids) # 強制搜尋範圍
            ]
        )

    # 執行 Qdrant 內部 Hybrid Search (Dense + Sparse + Filter)
    # search_results = qdrant_client.search(
    #     collection_name="docs",
    #     query_vector=get_embedding(query),
    #     query_filter=qdrant_filter,
    #     limit=top_k
    # )
    
    return "已過濾並檢索到的相關內容..."
```

### B. Agent 指令集更新 (`app/agents/router_agent.py`)

這是靈魂所在，我們必須引導 Agent 學會「先過濾、再檢索」。

Python

```
agent_instructions = [
    "你是一個具備『精確過濾』能力的檢索專家。請遵循以下思維鏈 (Chain of Thought)：",
    "1. **拆解問題**：分析用戶問題中是否包含明確的分類、日期、狀態或 ID 等屬性。",
    "2. **執行 SQL 預篩選**：如果存在上述屬性，必須先調用 `postgres_analytics_tool` 獲取符合條件的 ID 列表。",
    "3. **執行約束檢索**：將獲取的 ID 列表作為 `filter_ids` 傳入 `unified_hybrid_search`。",
    "4. **優點整合**：透過 SQL 縮小範圍確保『準確度』，透過向量搜尋確保『相關性』。",
    "5. **邊緣情況**：若 SQL 篩選出的 ID 過多（例如 > 500 個），請提示用戶縮小範圍，或改採分段檢索。"
]
```

---

## 3. 給 Coding Agent 的補充規格需求

請將以下這段話直接餵給你的 Coding Agent：

> **「補充開發任務：實作『SQL-to-Vector』連動邏輯」**
> 
> 1. **工具間通訊：** 確保 `postgres_analytics_tool` 能回傳一個純 ID 的 List。
>     
> 2. **Qdrant 條件整合：** 在調用 Qdrant API 時，必須將 `filter_ids` 轉換為 `qdrant_client.models.Filter` 對象，並使用 `must` 或 `should` 子句進行硬性約束。
>     
> 3. **異步優化：** 如果問題不包含結構化條件，應支援並行 (Parallel) 執行 SQL 統計與 Qdrant 檢索；如果包含條件，則必須採用順序 (Sequential) 執行。
>     
> 4. **動態 Prompt 更新：** Agent 必須在 `Thought` 階段顯式寫出：『我發現用戶指定了台北地區，我將先查詢 SQL 取得台北地區的資料 ID，再進行語意搜尋。』
>     

---

## 4. 完整的實作待辦清單 (For Developer)

|**階段**|**任務內容**|**完成標準**|
|---|---|---|
|**Data Layer**|在 Qdrant Payload 中建立 `pg_id` 索引。|搜尋速度不因 Filter 增加而下降。|
|**Logic Layer**|實作 RRF 融合，且支援 `Empty Result` 處理。|當 SQL 過濾後無結果時，Agent 應回報而非報錯。|
|**Agent Layer**|配置 Agno 的 `ToolCall` 依賴關係。|Agent 能自動將 Tool A 的 Output 餵給 Tool B。|
|**Validation**|測試 Edge Case：SQL 過濾出 0 筆資料 vs 10000 筆資料。|系統需有分頁或截斷機制。|
