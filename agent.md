# Agent 架構設計指南

本文件記錄將 OpenAPI 服務整合為 MCP Tool 的完整架構模式，以及在此過程中發現並修正的關鍵技術問題，供後續 agent 設計、coding 時參考。

---

## 一、系統架構總覽

```
[Agent 本機]
  ├── agno Agent (research_agent)
  │     └── MultiMCPTools → 連接 MCP Hub
  ├── openapi_fastmcp_server.py (port 8015, /agent01/mcp)
  │     └── 將外部 OpenAPI spec 轉成 MCP Tools（使用 fastmcp）
  └── uploads/   ← 前端上傳的圖片暫存於此

[LiteLLM 機器] 192.168.37.71:32290/mcp
  └── MCP Hub：集合多台機器的 MCP server，統一對外提供

[OCR API 遠端] https://test4.txcaix.com/ocrapi/ocr
  └── FastAPI，POST /ocr，multipart/form-data，UploadFile
```

### 資料流（OCR 場景完整流程）

```
1. 前端上傳圖片
   → POST /upload-image (backend/main.py)
   → 儲存至 backend/uploads/<uuid>.jpg
   → 回傳 { path, url, filename }

2. 前端在 message 附加提示
   → [IMAGE_FILE name="xxx.jpg" path="/root/.../uploads/abc.jpg"]

3. Agent (LLM) 收到訊息
   → 解析 path
   → 呼叫 MCP tool: ocr-ocr_image_ocr_post(file="/root/.../uploads/abc.jpg")

4. agno → MCP JSON-RPC (call_tool)
   → LiteLLM MCP Hub (192.168.37.71:32290/mcp)
   → 本機 openapi_fastmcp_server.py (test4.txcaix.com/agent01/mcp)

5. fastmcp RequestDirector.build()  ← 此處為關鍵修改點
   → 偵測 route Content-Type = multipart/form-data
   → _resolve_binary_value("/root/.../uploads/abc.jpg")
      ① 識別為本機路徑 → open(path, "rb") 讀取 bytes
   → 建構 httpx multipart/form-data 請求

6. httpx POST → https://test4.txcaix.com/ocrapi/ocr
   → OCR API 收到完整的 binary stream（與直接上傳相同）
   → 回傳 { raw_text, success, error }
```

**重點：OCR API 遠端機器永遠不需要存取 Agent 本機的檔案系統。binary bytes 已嵌入 multipart HTTP body 中傳送。**

---

## 二、關鍵問題與修正：fastmcp `director.py`

### 問題根源

`fastmcp 3.1.0`（套件路徑：`.venv/lib/python3.13/site-packages/fastmcp/utilities/openapi/director.py`）的 `RequestDirector.build()` 有個缺陷：

```python
# 舊版（有問題）
if isinstance(body, dict | list):
    json_body = body   # ← 無論 Content-Type 為何，dict 一律用 json= 傳送
```

這導致 `multipart/form-data` endpoint（如 FastAPI `UploadFile`）永遠收到 `application/json` 請求，回傳 `422 Validation Error`。

### 修正方案

修改 `director.py`，偵測 route 的 Content-Type，對 `multipart/form-data` 做特殊處理：

```python
# 修改後邏輯（Step 4）
if isinstance(body, dict) and route_content_type == "multipart/form-data":
    body_schema = route.request_body.content_schema.get(route_content_type, {})
    props = body_schema.get("properties", {})
    _files, _form = {}, {}
    for key, value in body.items():
        if props.get(key, {}).get("format") == "binary":
            raw, filename = self._resolve_binary_value(value, key)
            mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            _files[key] = (filename, raw, mime)
        else:
            _form[key] = str(value)
    files = _files or None
    form_data = _form or None
```

### `_resolve_binary_value()` — 二進位欄位解析器

這是最關鍵的設計：對 `format: binary` 欄位，LLM 只能傳字串（路徑、URL 或 base64），由 MCP server 端自行解析並讀取實際 bytes。

```python
@staticmethod
def _resolve_binary_value(value: Any, field_name: str) -> tuple[bytes, str]:
    """
    接受三種輸入，統一轉換為 (raw_bytes, filename)：
      1. 本機檔案路徑  /root/.../uploads/abc.jpg
      2. HTTP(S) URL   http://host/uploads/abc.jpg
      3. Base64 字串   iVBOR...（fallback）
    """
    if isinstance(value, bytes):
        return value, field_name

    if isinstance(value, str):
        # 1) 本機路徑
        if os.path.isfile(value):
            with open(value, "rb") as fh:
                return fh.read(), os.path.basename(value)

        # 2) HTTP URL
        parsed = urlparse(value)
        if parsed.scheme in ("http", "https"):
            resp = httpx.get(value, timeout=60, follow_redirects=True)
            resp.raise_for_status()
            return resp.content, os.path.basename(parsed.path) or field_name

        # 3) Base64 fallback
        try:
            raw = base64.b64decode(value)
            if raw:
                return raw, field_name
        except Exception:
            pass

    return str(value).encode(), field_name
```

**此修改讓所有使用同一套 `.venv` 的 MCP server 自動受益，無需個別修改各 agent。**

---

## 三、前端圖片上傳整合

### backend/main.py — 圖片預上傳端點

```python
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

@app.post("/upload-image")
async def upload_image_endpoint(file: UploadFile = File(...)):
    data = await file.read()
    ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOADS_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(data)
    return {
        "url": f"http://localhost:{BACKEND_PORT}/uploads/{filename}",
        "path": file_path,           # ← Agent 用此 path 呼叫 MCP OCR
        "filename": filename,
        "original_name": file.filename,
    }

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
```

### frontend/src/services/api.js — 上傳並附加提示

```javascript
// prepareMessageAndFiles() 中
if (imageFile) {
    const formData = new FormData();
    formData.append("file", imageFile);
    const resp = await axios.post("/upload-image", formData);
    const { path, original_name } = resp.data;
    uploadHints.push(`[IMAGE_FILE name="${original_name}" path="${path}"]`);
}
finalMessage = finalMessage + '\n\n' + uploadHints.join('\n');
// 圖片仍照常作為 imageFiles 傳給 agno /runs（讓 LLM 視覺理解）
```

---

## 四、Agent Instructions 設計模式

### OCR Workflow 指令（agents_remote.py）

```
## OCR Workflow (IMPORTANT)
    When the user uploads an image and you see `[IMAGE_FILE name="..." path="..."]` in the message:
    1. Extract the `path` value from the hint.
    2. Call the MCP tool `ocr-ocr_image_ocr_post` directly, passing the **file path** as the `file` parameter:
       - `file`: the local path string (e.g. `/root/agno_agentOS/backend/uploads/abc123.jpg`)
       - `user_prompt`: (optional) custom OCR prompt text
    3. The MCP server will read the file from the path and send it to the OCR API automatically.
    4. The API returns JSON: `raw_text` (文字), `success` (bool), `error` (str|null).
    5. Present `result["raw_text"]` to the user.
```

**設計原則：LLM 只傳字串（路徑），不讀檔、不 encode。複雜的 I/O 留給 server 端處理。**

---

## 五、MCP Tools 設定模式

### agents_remote.py

```python
from agno.tools.mcp import MultiMCPTools, StreamableHTTPClientParams

mcp_tools = MultiMCPTools(
    server_params_list=[
        StreamableHTTPClientParams(
            url=os.getenv("MCP_SERVER_URL", "http://192.168.37.71:32290/mcp"),
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', '')}"},
        )
    ],
    timeout_seconds=15,
    refresh_connection=False,    # 重要：False = startup event 管理生命週期，避免每次 run 重建
    allow_partial_failure=True,
    include_tools=["ocr-ocr_image_ocr_post", "markitdown-convert_to_markdown"],
)
```

### main.py — MCP 生命週期管理

```python
from agents_remote import mcp_tools

@app.on_event("startup")
async def startup_mcp():
    await mcp_tools.connect()    # 應用啟動時建立連線

@app.on_event("shutdown")
async def shutdown_mcp():
    await mcp_tools.close()      # 應用關閉時釋放連線
```

### backend/.env

```
MCP_SERVER_URL=http://192.168.37.71:32290/mcp
OPENAI_API_KEY=<LiteLLM API Key>   # 同時作為 MCP Hub 的 Authorization header
```

---

## 六、openapi_fastmcp_server.py 設計模式

將任意 OpenAPI spec 轉成 MCP server：

```python
from fastmcp import FastMCP
import httpx

spec = httpx.get("https://remote-api.com/openapi.json").json()
# 修正相對路徑的 servers URL
_normalize_openapi_servers(spec, openapi_url)

mcp = FastMCP.from_openapi(spec, name="My API MCP")
mcp.run(transport="streamable-http", host="0.0.0.0", port=8015, path="/agent01/mcp")
```

**注意事項：**
- `fastmcp.from_openapi` 需要 `servers[].url` 為絕對 URL，必須在傳入前正規化
- 工具名稱格式為 `{server_name}-{operationId}`，例如：`ocr-ocr_image_ocr_post`
- MCP server 重啟後才會載入修改後的套件程式碼

---

## 七、常見坑與解決方案

| 問題 | 原因 | 解決方式 |
|------|------|----------|
| MCP 連線 500 錯誤 | LiteLLM Hub 需要 Authorization header | `headers={"Authorization": "Bearer <key>"}` |
| 前端 response 很慢 | `refresh_connection=True` 每次 run 重建 MCP 連線 | 改為 `False`，用 startup/shutdown 管理 |
| 只有 1 個工具出現 | `include_tools` 工具名稱前綴錯誤 | 工具名稱格式：`{server}-{operationId}` 如 `ocr-ocr_image_ocr_post` |
| OCR API 回 422 | fastmcp 把 multipart body 用 `json=` 傳送 | 修改 `director.py` 加入 multipart 偵測邏輯 |
| LLM 無法傳 binary 給 MCP | LLM tool call 只能傳字串，不能傳 bytes | 傳本地路徑字串，由 MCP server 端讀檔 |
| OCR 找不到圖片 | MCP server 和 Agent server 在同機，但路徑不對 | 確認 uploads/ 的絕對路徑正確 |

---

## 八、新 OpenAPI→MCP 服務接入 Checklist

新增一個透過 OpenAPI 接入的 MCP service 時，依序確認：

- [ ] 1. 取得 `openapi.json` URL，確認 `servers[].url` 是絕對路徑
- [ ] 2. 啟動 `openapi_fastmcp_server.py --openapi-url <url> --port <port> --mcp-path /agent01/mcp`
- [ ] 3. 在 LiteLLM Hub 設定此 MCP server 的連線
- [ ] 4. 呼叫 `check_mcp_tool.py` 確認工具出現，記下完整工具名稱（含前綴）
- [ ] 5. 若有 `multipart/form-data` + `format:binary` 欄位，確認 `director.py` 已修改
- [ ] 6. 在 `include_tools` 加入工具名稱
- [ ] 7. 在 agent `instructions` 加入對應的 Workflow 說明
- [ ] 8. 若需要前端上傳檔案，實作 `/upload-{type}` 端點並更新前端 `prepareMessageAndFiles()`
- [ ] 9. 重啟 MCP server（讓套件修改生效）
- [ ] 10. 測試：前端上傳 → Agent OCR → 回傳結果

---

## 九、相關檔案索引

| 檔案 | 說明 |
|------|------|
| `backend/agents_remote.py` | Agent 定義（mcp_tools, instructions） |
| `backend/main.py` | FastAPI 入口（MCP lifecycle, /upload-image） |
| `backend/openapi_fastmcp_server.py` | OpenAPI → MCP server 轉換器 |
| `frontend/src/services/api.js` | 前端 API 層（prepareMessageAndFiles） |
| `backend/.env` | 環境變數（MCP_SERVER_URL, OPENAI_API_KEY） |
| `.venv/lib/.../fastmcp/utilities/openapi/director.py` | **已修改**：multipart/form-data + binary field 支援 |
