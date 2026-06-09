# Hybrid RAG Agent

> **Agno (AgentOS) 架構** — 整合 PostgreSQL (SQL) 與 Qdrant (Vector + BM25)，  
> 透過 Intent Routing 與 Qdrant 原生 RRF 融合 + Cross-Encoder Reranker 實現精準混合檢索。

---

## 架構總覽

```mermaid
flowchart TB
    subgraph User["👤 使用者"]
        Q["自然語言查詢"]
    end

    subgraph API["FastAPI Server"]
        EP["/chat endpoint"]
    end

    subgraph Agent["🤖 Agno Router Agent<br/>(LiteLLMOpenAI — TXC-LLM / Qwen3.5)"]
        IR["Intent Routing<br/>Chain-of-Thought"]
    end

    subgraph Tools["🔧 工具層"]
        AT["postgres_analytics_tool<br/>SQL 統計 / ID 篩選"]
        RT["unified_hybrid_search<br/>混合檢索 + Rerank"]
    end

    subgraph Embedding["🧠 Embedding 服務"]
        DE["Dense Embedding<br/>BAAI/bge-m3 (1024d)<br/>via vLLM"]
        SE["Sparse Embedding<br/>BM25 (fastembed)"]
    end

    subgraph Storage["💾 儲存層"]
        PG["PostgreSQL<br/>結構化資料<br/>(id, title, content,<br/>branch, category, date)"]
        QD["Qdrant<br/>Named Vectors:<br/>dense + sparse"]
    end

    subgraph Qdrant_Search["🔍 Qdrant Server-Side"]
        PF1["Prefetch: Dense Search"]
        PF2["Prefetch: Sparse BM25"]
        FQ["FusionQuery<br/>Reciprocal Rank Fusion"]
    end

    subgraph Rerank["🎯 Reranker"]
        RR["BAAI/bge-reranker-v2-m3<br/>via vLLM /score API"]
    end

    Q --> EP --> IR

    IR -->|"統計/聚合查詢"| AT
    IR -->|"語意搜尋"| RT
    IR -->|"先過濾再搜尋"| AT
    AT -->|"filter_ids"| RT

    AT --> PG
    RT --> DE & SE

    DE --> PF1
    SE --> PF2
    PF1 & PF2 --> FQ
    FQ -->|"RRF 候選 top_k×3"| RT
    RT -->|"取回完整內容"| PG
    RT -->|"Cross-Encoder 重排"| RR
    RR -->|"最終 top_k 結果"| IR
    IR -->|"回答"| EP --> Q

    style Agent fill:#e8f0fe,stroke:#1a73e8
    style Qdrant_Search fill:#fef3e0,stroke:#f9a825
    style Rerank fill:#fce4ec,stroke:#e91e63
    style Storage fill:#e8f5e9,stroke:#4caf50
```

## 核心流程

```mermaid
sequenceDiagram
    participant U as 使用者
    participant A as Router Agent
    participant SQL as postgres_analytics_tool
    participant HS as unified_hybrid_search
    participant EMB as Embedding (bge-m3 + BM25)
    participant QD as Qdrant (RRF Fusion)
    participant PG as PostgreSQL
    participant RR as Reranker (bge-reranker)

    U->>A: 自然語言查詢
    A->>A: Intent Routing (CoT)

    alt 純統計查詢
        A->>SQL: SQL (purpose=statistics)
        SQL->>PG: SELECT ... GROUP BY ...
        PG-->>SQL: 統計結果
        SQL-->>A: JSON 回傳
    else 純語意搜尋
        A->>HS: query, top_k
        HS->>EMB: Dense + Sparse Embedding
        EMB-->>HS: vectors
        HS->>QD: prefetch(dense) + prefetch(sparse) → RRF Fusion
        QD-->>HS: 候選文件 (top_k×3)
        HS->>PG: SELECT * WHERE id IN (...)
        PG-->>HS: 完整內容
        HS->>RR: Cross-Encoder Rerank
        RR-->>HS: 排序後結果
        HS-->>A: top_k 結果
    else 先過濾再搜尋 (Chained)
        A->>SQL: SQL (purpose=filter_ids)
        SQL->>PG: SELECT id WHERE branch='Taipei'
        PG-->>SQL: ID 列表
        SQL-->>A: ids: [id1, id2, ...]
        A->>HS: query + filter_ids
        HS->>EMB: Dense + Sparse Embedding
        HS->>QD: Hybrid Search + pg_id Filter
        QD-->>HS: 過濾後候選
        HS->>PG: 取回內容
        HS->>RR: Rerank
        RR-->>HS: 最終結果
        HS-->>A: top_k 結果
    end

    A-->>U: 綜合回答 (標注資料來源)
```

---

## 專案結構

```
hybrid-rag-agent/
├── .env                          # 環境設定 (PG, Qdrant, LLM, Embedding, Reranker)
├── requirements.txt              # Python 套件依賴
│
├── app/
│   ├── core/
│   │   ├── config.py             # 集中環境設定 (Settings 類別)
│   │   ├── database.py           # PostgreSQL 連線 (psycopg 3, dict_row)
│   │   ├── vector_db.py          # Qdrant 連線 + Named Vectors Hybrid Search
│   │   ├── embeddings.py         # Dense (bge-m3 via vLLM) + Sparse (BM25 via fastembed)
│   │   ├── reranker.py           # Cross-Encoder Reranker (bge-reranker via vLLM /score)
│   │   └── rrf.py                # Python-side RRF 工具函式 (備用)
│   │
│   ├── tools/
│   │   ├── analytics_tool.py     # SQL 統計/篩選工具 (安全檢查, 防 SQL Injection)
│   │   └── retrieval_tool.py     # 混合檢索工具 (Qdrant RRF + Rerank 全流程)
│   │
│   ├── agents/
│   │   └── router_agent.py       # Agno Router Agent (Intent Routing + CoT)
│   │
│   └── main.py                   # FastAPI 入口 (/chat, /health, /)
│
├── data/
│   ├── ingest.py                 # 資料寫入腳本 (PG + Qdrant 雙寫)
│   └── generate_100_docs.py      # 隨機生成 100 筆測試文件
│
└── tests/
    ├── test_api.py               # API endpoint 單元測試 (5)
    ├── test_database.py          # PostgreSQL + SQL 安全測試 (8)
    ├── test_embeddings.py        # Embedding 測試 (5)
    ├── test_reranker.py          # Reranker 單元測試 (7)
    ├── test_rrf.py               # RRF 演算法測試 (11)
    ├── test_vector_db.py         # Qdrant 向量搜尋測試 (14+)
    └── test_integration.py       # 端對端整合測試 (29)
```

---

## 技術棧

| 元件 | 技術 | 說明 |
|------|------|------|
| **Agent 框架** | Agno 2.5.3 | Agent 編排、Tool Calling、Intent Routing |
| **LLM** | TXC-LLM (Qwen3.5) via LiteLLMOpenAI | 推理引擎，base_url 指向 vLLM |
| **Dense Embedding** | BAAI/bge-m3 (1024d) | vLLM OpenAI-compatible API |
| **Sparse Embedding** | fastembed BM25 | 本地端 Qdrant/bm25 模型 |
| **Reranker** | BAAI/bge-reranker-v2-m3 | vLLM /score API (Cross-Encoder) |
| **向量資料庫** | Qdrant 1.13.5 | Named Vectors + 原生 RRF Fusion |
| **關聯式資料庫** | PostgreSQL | 結構化資料 + SQL 篩選 |
| **Web 框架** | FastAPI 0.131.0 | REST API 伺服器 |
| **Python** | 3.13.2 | 執行環境 |

---

## 環境設定

### `.env` 設定範例

```env
# LLM (LiteLLMOpenAI — TXC-LLM via vLLM)
LLM_MODEL=TXC-LLM
LLM_API_KEY=your-api-key
LLM_BASE_URL=http://your-llm-host:port

# PostgreSQL
POSTGRES_HOST=your-pg-host
POSTGRES_PORT=5432
POSTGRES_DB=hybrid_rag
POSTGRES_USER=your-user
POSTGRES_PASSWORD=your-password

# Qdrant (支援 http://host:port 或純 hostname)
QDRANT_HOST=http://your-qdrant-host:port
QDRANT_PORT=6333
QDRANT_COLLECTION=your-collection-name

# Embedding (BAAI/bge-m3 via vLLM OpenAI-compatible)
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DIM=1024
EMBEDDING_BASE_URL=http://your-embedding-host:port/v1
EMBEDDING_API_KEY=your-key

# Reranker (BAAI/bge-reranker-v2-m3 via vLLM)
RERANKER_BASE_URL=http://your-reranker-host:port
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
RERANKER_TOP_N=5
```

---

## 快速開始

### 1. 安裝依賴

```bash
cd hybrid-rag-agent
pip install -r requirements.txt
```

### 2. 建立資料庫（首次）

```bash
python -c "
import psycopg
conn = psycopg.connect('postgresql://user:pass@host:5432/postgres', autocommit=True)
conn.execute('CREATE DATABASE hybrid_rag')
conn.close()
"
```

### 3. 寫入測試資料 (100 筆)

```bash
python data/generate_100_docs.py
```

輸出範例：
```
Generated 100 random documents
Branch distribution: {'Taipei': 16, 'Kaohsiung': 14, 'HQ': 17, 'Tainan': 32, 'Taichung': 21}
Category distribution: {'strategy': 20, 'security': 12, 'marketing': 9, 'finance': 17, 'tech': 19, 'risk': 6, 'hr': 6, 'operations': 11}
Postgres: 100 rows | Qdrant: 100 points
```

### 4. 啟動 API 伺服器

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5. 測試 API

```bash
# 健康檢查
curl http://localhost:8000/health

# 聊天查詢
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "台北分公司的營收狀況如何？"}'
```

---

## 測試指令

### 執行全部測試 (79 項)

```bash
# 全部：50 單元測試 + 29 整合測試
python -m pytest tests/ -v
```

### 僅執行單元測試 (50 項，不需真實服務)

```bash
python -m pytest tests/ -v --ignore=tests/test_integration.py
```

### 僅執行整合測試 (29 項，需真實服務)

```bash
python -m pytest tests/test_integration.py -v
```

### 執行特定測試類別

```bash
# 服務連通性
python -m pytest tests/test_integration.py::TestServiceHealth -v

# 資料完整性
python -m pytest tests/test_integration.py::TestDataIntegrity -v

# Embedding 品質
python -m pytest tests/test_integration.py::TestEmbeddingQuality -v

# Qdrant 搜尋
python -m pytest tests/test_integration.py::TestQdrantSearch -v

# Reranker 整合
python -m pytest tests/test_integration.py::TestRerankerIntegration -v

# 端對端 Retrieval Tool
python -m pytest tests/test_integration.py::TestRetrievalToolE2E -v

# Analytics Tool
python -m pytest tests/test_integration.py::TestAnalyticsToolE2E -v

# 跨服務一致性
python -m pytest tests/test_integration.py::TestCrossServiceConsistency -v
```

---

## 整合測試涵蓋範圍

| 測試類別 | 數量 | 驗證內容 |
|----------|------|----------|
| **ServiceHealth** | 5 | PG / Qdrant / Dense Embedding / Sparse Embedding / Reranker 連通性 |
| **DataIntegrity** | 5 | 100 筆資料正確寫入 PG + Qdrant，分支/類別分佈完整 |
| **EmbeddingQuality** | 3 | Batch 一致性、Cosine Similarity 方向驗證 |
| **QdrantSearch** | 4 | Dense / Sparse / Hybrid / Filtered Hybrid 搜尋 |
| **RerankerIntegration** | 2 | 真實文件重排序、相關性提升 |
| **RetrievalToolE2E** | 4 | 完整 Hybrid Search + Rerank 流程、帶約束搜尋 |
| **AnalyticsToolE2E** | 4 | SQL 統計、ID 篩選、SQL Injection 防護 |
| **CrossServiceConsistency** | 2 | PG ↔ Qdrant 資料一致性驗證 |

---

## 關鍵設計決策

### 1. Qdrant 原生 Hybrid Search (Server-Side RRF)

不使用 Python 端 RRF 融合，而是利用 Qdrant 的 `prefetch` + `FusionQuery(Fusion.RRF)` 在 Server 端完成 Dense + Sparse 融合，減少網路往返與計算負擔。

### 2. Named Vectors (dense + sparse)

在同一個 Collection 中使用 Named Vectors 儲存 Dense (bge-m3, 1024d) 和 Sparse (BM25) 兩種向量，避免維護多個 Collection。

### 3. Two-Stage Ranking (RRF → Rerank)

- **Stage 1**: Qdrant RRF 融合取出 `top_k × 3` 候選
- **Stage 2**: Cross-Encoder Reranker (bge-reranker-v2-m3) 精排至最終 `top_k`

### 4. Chained & Constrained Retrieval (鏈式約束檢索)

Agent 透過 Intent Routing 自動判斷是否需要「先 SQL 過濾、再向量搜尋」，確保結構化條件（branch, category, date）被精確滿足。

### 5. URL-Compatible Qdrant Connection

`VectorDB` 自動偵測 `QDRANT_HOST` 是否為完整 URL (`http://...`)，若是則使用 `QdrantClient(url=...)` 連線，否則使用 `host + port` 傳統方式。


# 啟動方式
# 後端
cd hybrid-rag-agent
uvicorn app.main:app --reload --port 8000

# 前端（另一個 terminal）
cd hybrid-rag-agent/frontend
npm run dev