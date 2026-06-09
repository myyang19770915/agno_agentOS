# OpenAPI -> FastMCP Server

## 目的
把任意 `openapi.json` 轉成可直接提供 MCP tools 的 FastMCP server。

## 檔案
- `backend/openapi_fastmcp_server.py`

## 安裝
```bash
pip install -r requirements.txt
```

## 啟動（你這次的 API）
```bash
python backend/openapi_fastmcp_server.py \
  --openapi-url "https://test4.txcaix.com/deepseekocr/openapi.json" \
  --transport "streamable-http" \
  --host "0.0.0.0" \
  --port 8014 \
  --mcp-path "/mcp"
```

## 之後改別的 OpenAPI
只要換 `--openapi-url`：
```bash
python backend/openapi_fastmcp_server.py --openapi-url "<你的openapi.json>" --transport "streamable-http" --port 8014
```

如果環境暫時不能連外，也可以先下載後用本地檔：
```bash
python backend/openapi_fastmcp_server.py \
  --openapi-file "/path/to/openapi.json" \
  --openapi-url "https://example.com/openapi.json" \
  --transport "streamable-http" \
  --host "0.0.0.0" \
  --port 8014 \
  --mcp-path "/mcp"
```

## K8s Ingress 前綴路徑
如果你要掛同一個網域下的子路徑，例如 `/agent-a/mcp`，直接設定：
```bash
python backend/openapi_fastmcp_server.py \
  --transport "streamable-http" \
  --host "0.0.0.0" \
  --port 8015 \
  --mcp-path "/agent-a/mcp"
```

## 備註
- 使用 `FastMCP.from_openapi(...)` 直接把 OpenAPI 註冊成 MCP tools（簡化版）。
- tool 的輸入/輸出結構由 OpenAPI schema 自動推導。
