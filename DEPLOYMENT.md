# Agno AgentOS — 對外部署指南

> 更新日期：2026-02-25

---

## 目錄

1. [整體架構](#整體架構)
2. [服務一覽](#服務一覽)
3. [請求流向圖](#請求流向圖)
4. [路徑設計說明](#路徑設計說明)
5. [環境需求](#環境需求)
6. [啟動步驟](#啟動步驟)
7. [環境變數](#環境變數)
8. [Nginx 反向代理設定](#nginx-反向代理設定)
9. [前端設定說明](#前端設定說明)
10. [後端設定說明](#後端設定說明)
11. [修改過的檔案清單](#修改過的檔案清單)
12. [常見問題排查](#常見問題排查)

---

## 整體架構

```
外部使用者
    │
    ▼
Nginx (反向代理)
    │
    └── /agentplatform/  ──────────────▶  Vite Dev / Preview  :8014
                                              │
                                              │  /agentplatform/api/* (Vite proxy)
                                              │         strip prefix: /agentplatform/api
                                              ▼
                                     Main AgentOS (FastAPI)  :8013
                                              │
                                              │  內部 A2A 呼叫 (localhost only)
                                              ▼
                                     Image Agent (FastAPI)  :9999
                                              │
                                              │  HTTP 呼叫
                                              ▼
                                     ComfyUI  192.168.37.71:30631
```

> **關鍵設計原則**：所有外部請求統一走 `/agentplatform/` 前綴，透過同一條 Nginx 規則，  
> 由 Vite proxy 在內部分流 API 到後端，避免跨 location 的路由問題。

---

## 服務一覽

| 服務 | Port | 程式進入點 | 對外路徑 | 說明 |
|------|------|-----------|----------|------|
| **Frontend (Vite)** | `8014` | `frontend/` | `/agentplatform/` | React UI，含 Vite proxy |
| **Main AgentOS (FastAPI)** | `8013` | `backend/main.py` | (透過 Vite proxy) | API + 靜態資源 |
| **Image Agent (A2A)** | `9999` | `backend/image_agent.py` | **不對外** | 純內部 A2A 服務 |
| **ComfyUI** | `30631` (遠端) | 外部服務 | **不對外** | 圖片生成引擎 |

---

## 請求流向圖

### API 請求（以送出訊息為例）

```
瀏覽器
  POST /agentplatform/api/agents/research-agent/runs
      │
      ▼
Nginx
  location /agentplatform/ → proxy_pass http://localhost:8014/agentplatform/
      │
      ▼
Vite :8014
  proxy rule: /agentplatform/api → http://localhost:8013
  rewrite: strip /agentplatform/api
      │  請求變成
      ▼  POST /agents/research-agent/runs
Main AgentOS :8013
  FastAPI 處理，回傳 SSE stream
      │
      ▼
瀏覽器接收 Server-Sent Events
```

### 生圖請求

```
瀏覽器
  POST /agentplatform/api/teams/creative-team/runs
      │  (之後流程同上)
      ▼
Main AgentOS :8013
  Team Leader 委派給 Image Agent
      │ 內部 A2A (localhost:9999)，不經過 Nginx
      ▼
Image Agent :9999
      │ HTTP POST to ComfyUI
      ▼
ComfyUI 192.168.37.71:30631
      │ 回傳圖片，存到 backend/outputs/images/
      ▼
Image Agent 回傳路徑 "outputs/images/xxx.png"
      │
      ▼
Main AgentOS 將路徑包在 SSE 回應中
      │
      ▼
瀏覽器 Message.jsx 解析路徑
  outputs/images/xxx.png
  → /agentplatform/api/images/xxx.png   ← config.js IMAGES_BASE
      │
      ▼
Vite proxy → Main AgentOS :8013/images/xxx.png (StaticFiles)
      │
      ▼
瀏覽器顯示圖片
```

---

## 路徑設計說明

### 為什麼把 API 放在 `/agentplatform/api` 下？

初版設定使用兩個獨立前綴：

```
/agentplatform/  → Vite:8014  (前端)
/agentapi/       → 後端:8013  (API)   ← ❌ Nginx 需要第二條規則
```

問題：若 Nginx 只設定一條 `/agentplatform/` 規則，則 `/agentapi/` 的 API 請求直接打到 Nginx，因 location 不存在而 **404**。

改為：

```
/agentplatform/        → Vite:8014  (前端靜態)
/agentplatform/api/    → Vite:8014  → Vite proxy → 後端:8013  ← ✅ 同一條 Nginx 規則搞定
```

Nginx 只需一條規則，Vite 內部用 `proxy` 做 API 分流，**開發與生產環境行為一致**。

### 路徑對照表

| 瀏覽器看到的路徑 | 實際打到的服務 | 說明 |
|----------------|--------------|------|
| `/agentplatform/` | Vite:8014/前端 dist | UI 頁面 |
| `/agentplatform/api/agents` | AgentOS:8013/agents | Agent 列表 |
| `/agentplatform/api/sessions` | AgentOS:8013/sessions | Session 管理 |
| `/agentplatform/api/teams/*` | AgentOS:8013/teams/* | Team 模式 SSE |
| `/agentplatform/api/images/*.png` | AgentOS:8013/images/*.png | 生成圖片 |
| `/agentplatform/api/charts/*.html` | AgentOS:8013/charts/*.html | Plotly 圖表 |
| `/agentplatform/api/downloads/*` | AgentOS:8013/downloads/* | 可下載檔案 |

---

## 環境需求

```bash
# Python 環境
Python 3.10+
uv (套件管理)

# Node.js
Node.js 18+
npm 9+

# 外部服務
PostgreSQL (session & tracing 用)
ComfyUI (圖片生成用，192.168.37.71:30631)
LiteLLM Proxy (LLM 閘道，port 4001)
Tavily API Key (搜尋功能)
```

---

## 啟動步驟

### 方式一：一鍵部署腳本

```bash
cd /root/agno_agentOS
chmod +x deploy.sh
./deploy.sh
```

腳本會自動：
1. 建置前端靜態資源 (`npm run build`)
2. 啟動 Image Agent (port 9999)
3. 啟動 Main AgentOS (port 8013)
4. 啟動 Frontend dev server (port 8014)
5. 輸出各服務存取位址

按 `Ctrl+C` 停止所有服務。

---

### 方式二：手動分步啟動

```bash
cd /root/agno_agentOS
source .venv/bin/activate

# Step 1: 啟動 Image Agent
cd backend
python image_agent.py &
# 等待 port 9999 就緒

# Step 2: 啟動 Main AgentOS
python main.py &
# 等待 port 8013 就緒

# Step 3: 啟動前端
cd ../frontend
npm run dev
# 監聽 port 8014
```

---

### 方式三：生產環境（靜態建置 + preview）

```bash
# 建置前端
cd /root/agno_agentOS/frontend
npm run build
# 輸出到 frontend/dist/

# 以 preview 模式服務靜態檔（帶 Vite proxy 功能）
npm run preview
# 監聽 port 8014（由 vite.config.js preview.port 設定）

# 後端與 image agent 同方式二
```

---

## 環境變數

後端可透過環境變數覆寫預設值，建議建立 `backend/.env` 或在啟動指令前設定：

| 變數名稱 | 預設值 | 說明 |
|---------|--------|------|
| `ROOT_PATH` | `/agentapi` | FastAPI `root_path`，供 OpenAPI docs 用（不影響實際路由） |
| `BACKEND_PORT` | `8013` | 後端 uvicorn 監聽 port |
| `LITELLM_API_KEY` | — | LiteLLM Proxy API 金鑰 |
| `LITELLM_BASE_URL` | `http://localhost:4001/v1` | LiteLLM Proxy 位址 |
| `MODEL_ID` | `deepseek-chat` | 使用的 LLM 模型 ID |
| `IMAGE_AGENT_URL` | `http://localhost:9999` | Image Agent A2A URL（agents_remote.py 使用） |

範例 `.env`：

```bash
ROOT_PATH=/agentapi
BACKEND_PORT=8013
MODEL_ID=gpt-5-mini
LITELLM_API_KEY=sk-xxxx
LITELLM_BASE_URL=http://localhost:4001/v1
```

---

## Nginx 反向代理設定

### 開發環境（Vite dev server，proxy 內建）

只需一條 Nginx 規則，API 由 Vite dev proxy 轉發：

```nginx
server {
    listen 443 ssl;
    server_name test4.txcaix.com;

    # SSL 設定（略）

    # 全部走前端 Vite，Vite proxy 負責分流 /agentplatform/api/ → :8013
    location /agentplatform/ {
        proxy_pass          http://localhost:8014/agentplatform/;
        proxy_http_version  1.1;
        proxy_set_header    Host              $host;
        proxy_set_header    Upgrade           $http_upgrade;
        proxy_set_header    Connection        "upgrade";
        proxy_set_header    X-Real-IP         $remote_addr;
        proxy_set_header    X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header    X-Forwarded-Proto $scheme;

        # SSE 串流必須關閉 buffering
        proxy_buffering     off;
        proxy_cache         off;
        proxy_read_timeout  300s;
    }
}
```

### 生產環境（靜態 dist + 後端直連，兩條規則）

```nginx
server {
    listen 443 ssl;
    server_name test4.txcaix.com;

    # SSL 設定（略）

    # ① API 路徑（更具體的規則，Nginx 優先匹配）
    location /agentplatform/api/ {
        proxy_pass          http://localhost:8013/;
        proxy_http_version  1.1;
        proxy_set_header    Host              $host;
        proxy_set_header    X-Real-IP         $remote_addr;
        proxy_set_header    X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header    X-Forwarded-Proto $scheme;

        # SSE 串流必須關閉 buffering
        proxy_buffering     off;
        proxy_cache         off;
        proxy_read_timeout  300s;
    }

    # ② 前端靜態資源
    location /agentplatform/ {
        alias /root/agno_agentOS/frontend/dist/;
        try_files $uri $uri/ /agentplatform/index.html;
        expires 1h;
        add_header Cache-Control "public, must-revalidate";
    }
}
```

> **注意**：生產環境的 Nginx 規則中，`/agentplatform/api/` 必須寫在 `/agentplatform/` **前面**（或使用 `location ^~`），確保 Nginx 優先匹配 API 路徑。

---

## 前端設定說明

### `frontend/vite.config.js`

```javascript
export default defineConfig({
  base: '/agentplatform',       // 所有靜態資源路徑前綴，對應 Nginx location
  server: {
    port: 8014,
    proxy: {
      '/agentplatform/api': {
        target: 'http://localhost:8013',  // 後端 AgentOS
        changeOrigin: true,
        // strip /agentplatform/api → 後端看到的是 /agents, /sessions 等
        rewrite: (path) => path.replace(/^\/agentplatform\/api/, ''),
      }
    }
  },
  preview: { port: 8014 }
})
```

### `frontend/src/config.js`

集中管理所有後端 API 路徑，單一改這個檔案即可影響全前端：

```javascript
export const API_BASE      = '/agentplatform/api';
export const IMAGES_BASE   = `${API_BASE}/images`;
export const CHARTS_BASE   = `${API_BASE}/charts`;
export const DOWNLOADS_BASE = `${API_BASE}/downloads`;
export const DOWNLOAD_BASE  = `${API_BASE}/download`;
```

---

## 後端設定說明

### `backend/main.py`

```python
ROOT_PATH    = os.getenv("ROOT_PATH", "/agentapi")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8013"))

# ...
app = agent_os.get_app()
app.root_path = ROOT_PATH   # 讓 OpenAPI /docs 產生正確的 server URL
```

`root_path` 用途是讓 FastAPI Swagger UI 的「Try it out」按鈕使用正確路徑。  
**不影響實際 API 路由**，路由仍由 Vite proxy / Nginx 決定。

### `backend/image_agent.py`

port 9999 **純內部服務**，不需要設定 `root_path`，不需要 Nginx 代理。  
唯一依賴：`backend/image.py` 中的 `COMFYUI_URL = "http://192.168.37.71:30631"` 需可連通。

---

## 修改過的檔案清單

本次對外部署調整涉及以下檔案：

| 檔案 | 主要變更 |
|------|---------|
| `backend/main.py` | 新增 `ROOT_PATH`、`BACKEND_PORT` 環境變數；`app.root_path` 設定；port `7777` → `8013` |
| `frontend/vite.config.js` | `base: '/agentplatform'`；port `3001` → `8014`；proxy `/agentplatform/api` → `:8013`（含 rewrite） |
| `frontend/src/config.js` | **新增** — 集中 `API_BASE`（`/agentplatform/api`）及靜態資源路徑常數 |
| `frontend/src/services/api.js` | 所有 `fetch()` 路徑加上 `API_BASE` 前綴 |
| `frontend/src/components/Message.jsx` | 引入 `config.js`；`http://localhost:7777` 替換為 `API_BASE`/`IMAGES_BASE`/`CHARTS_BASE` |
| `deploy.sh` | **新增** — 一鍵部署腳本（build + 三服務啟動 + Ctrl+C 清理） |

---

## 常見問題排查

### API 回傳 404

```bash
# 確認後端是否在 8013 上運行
curl http://localhost:8013/agents

# 確認 Vite proxy 是否正確轉發
curl http://localhost:8014/agentplatform/api/agents
```

若 `8013` 正常但 `8014` 404，表示 Vite proxy 設定有誤，  
確認 `vite.config.js` 的 proxy key 為 `/agentplatform/api`。

---

### 圖片無法顯示

```bash
# 確認圖片已生成到本地
ls backend/outputs/images/*.png | head -5

# 確認靜態檔案路由正常
TESTIMG=$(ls backend/outputs/images/*.png | head -1 | xargs basename)
curl -I http://localhost:8013/images/$TESTIMG
curl -I http://localhost:8014/agentplatform/api/images/$TESTIMG
```

若兩個都 200，問題在前端路徑轉換，確認 `Message.jsx` 有正確引入 `IMAGES_BASE`。

---

### 生圖失敗（image agent 無回應）

```bash
# 確認 image_agent 進程
ps aux | grep image_agent

# 確認 port 9999
curl http://localhost:9999/agents

# 確認 ComfyUI 可連通（最常見問題）
curl --max-time 5 http://192.168.37.71:30631
```

ComfyUI 若連線失敗（回傳 `000`），表示 ComfyUI 服務未啟動或 IP/Port 有變動，  
需修改 `backend/image.py` 第 4 行的 `COMFYUI_URL`：

```python
COMFYUI_URL = "http://<新IP>:<新Port>"
```

---

### SSE 串流在 Nginx 後面被截斷

確認 Nginx 有設定以下三行（缺一不可）：

```nginx
proxy_buffering    off;
proxy_cache        off;
proxy_read_timeout 300s;
```

---

### 服務埠口快速檢查

```bash
curl -s -o /dev/null -w "Frontend  :8014 → %{http_code}\n" http://localhost:8014/agentplatform/
curl -s -o /dev/null -w "API proxy :8014 → %{http_code}\n" http://localhost:8014/agentplatform/api/agents
curl -s -o /dev/null -w "Backend   :8013 → %{http_code}\n" http://localhost:8013/agents
curl -s -o /dev/null -w "ImgAgent  :9999 → %{http_code}\n" http://localhost:9999/agents
curl -s -o /dev/null -w "ComfyUI        → %{http_code}\n" --max-time 5 http://192.168.37.71:30631
```

全部 200 表示服務鏈路正常。

---

### 停止所有服務

```bash
pkill -f 'python main.py'
pkill -f 'python image_agent.py'
pkill -f 'npm run dev'
pkill -f 'vite'
```

或直接在 `deploy.sh` 執行中按 `Ctrl+C`，腳本會自動清理所有子進程。
