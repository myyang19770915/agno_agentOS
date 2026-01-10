# My Agent App - 技術筆記

## FastAPI 靜態檔案掛載

### 用法
```python
from fastapi.staticfiles import StaticFiles

# 將本地目錄掛載為靜態檔案服務
app.mount("/images", StaticFiles(directory=output_dir), name="images")
```

### 說明
- `"/images"` - URL 路徑前綴
- `directory=output_dir` - 本地目錄路徑 (例如 `outputs/images`)
- `name="images"` - 路由名稱，用於在程式內部引用

### 存取方式
假設 `outputs/images/z-image_00461_.png` 存在：
```
GET http://localhost:7777/images/z-image_00461_.png
```

### 注意事項
1. 這個端點**不會**顯示在 Swagger 文檔 (`/docs`) 中
2. 確保目錄存在，否則會報錯
3. 適合用於存放生成的圖片、下載檔案等

---

## 專案架構

### 服務啟動順序
1. 先啟動 `image_agent.py` (port 9999) - 圖片生成服務
2. 再啟動 `main.py` (port 7777) - 主應用程式

### Team 實現模式

#### 模式 1: 原始模式 (`agents.py`)
- Image Agent 使用 `@tool` + `httpx` 調用遠端服務
- 適合需要自訂 HTTP 請求的場景

#### 模式 2: RemoteAgent Wrapper 模式 (`agents_wrapper.py`) ✅ 推薦
- 使用 `RemoteAgent` 連接遠端 image_agent
- 透過 Wrapper Agent 包裝，解決 Team 兼容性問題
- 架構：
  ```
  ┌─────────────────────────────────────┐
  │           Creative Team             │
  ├─────────────────┬───────────────────┤
  │ Research Agent  │ Image Wrapper     │
  │   (local)       │   (local agent)   │
  │                 │        ↓          │
  │                 │  RemoteAgent      │
  │                 │        ↓          │
  │                 │  image_agent:9999 │
  └─────────────────┴───────────────────┘
  ```

### 切換模式
在 `main.py` 中修改 import：
```python
# 模式 1
# from agents import research_agent, creative_team

# 模式 2 (推薦)
from agents_wrapper import research_agent, creative_team
```

---

## API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/agents/research-agent/runs` | POST | 單獨使用研究 Agent |
| `/teams/creative-team/runs` | POST | 使用完整 Team |
| `/images/{filename}` | GET | 存取生成的圖片 |
| `/docs` | GET | Swagger API 文檔 |

---

## 已知問題

### RemoteAgent 無法直接作為 Team 成員
**問題**: `RemoteAgent` 缺少 `knowledge_filters` 和 `output_schema` 屬性
**錯誤**: `AttributeError: 'RemoteAgent' object has no attribute 'knowledge_filters'`
**解決方案**: 使用 Wrapper Agent 包裝 RemoteAgent
**狀態**: 已提交 Issue 報告 (見 `AGNO_ISSUE_REPORT.md`)

---

## 環境設定

### 依賴套件
- `agno>=2.3.24`
- `litellm>=1.80.13`
- `tavily-python`
- `httpx`

### LiteLLM Proxy
- 地址: `http://localhost:4001/v1`
- Model ID: `deepseek-chat`
