"""
Creative Research AgentOS - Main Entry Point

提供三種 Team 實現模式：
1. 原始模式 (agents.py): Image Agent 使用 httpx Tool 調用遠端服務
2. RemoteAgent Wrapper 模式 (agents_wrapper.py): Image Agent 使用 RemoteAgent + Wrapper
3. Native RemoteAgent 模式 (agents_remote.py): 直接使用 RemoteAgent 作為 Team 成員 (agno 2.3.26+)

可以透過修改下方的 import 來切換模式
"""

from agno.os import AgentOS
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import HTTPException, Query
from fastapi.middleware.gzip import GZipMiddleware
from typing import Optional
import os
import httpx
from agno.db.postgres import PostgresDb

# ============================================================================
# 部署設定：root_path 與 port（可透過環境變數覆寫）
# ============================================================================
ROOT_PATH = os.getenv("ROOT_PATH", "/agentapi")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8013"))
IMAGE_AGENT_URL = os.getenv("IMAGE_AGENT_URL", "http://localhost:9999")


# 資料庫用於 Session 記憶 (PostgreSQL)
db_url = "postgresql://webui:webui@postgresql.database.svc.cluster.local:5432/meeting_records"

# tracing_db 用於 OpenTelemetry Tracing 的 span 記錄，與 session_db 分開，避免衝突
tracing_db = PostgresDb(
    session_table="tracing_spans260223",
    db_schema="ai",
    db_url=db_url,
)
# ============================================================================
# 選擇使用的模式 (取消註解要使用的模式)
# ============================================================================

# ----- 模式 1: 原始模式 (httpx Tool 調用遠端 image_agent 服務) -----
# from agents import research_agent, creative_team

# ----- 模式 2: RemoteAgent Wrapper 模式 -----
# from agents_wrapper import research_agent, creative_team

# ----- 模式 3: Native RemoteAgent 模式 (推薦，需要 agno 2.3.26+) -----
# 直接使用 RemoteAgent 作為 Team 成員，無需 Wrapper
from agents_remote import research_agent, creative_team, image_agent


# ============================================================================
# 確保圖片輸出目錄存在
# ============================================================================
output_dir = os.path.join(os.path.dirname(__file__), "outputs", "images")
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

CHARTS_DIR = os.path.join(os.path.dirname(__file__), "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


# ============================================================================
# 建立 AgentOS
# ============================================================================
agent_os = AgentOS(
    name="Creative Research AgentOS",
    description="Agent with session memory, web search, and image generation via RemoteAgent",
    agents=[research_agent, image_agent],
    teams=[creative_team],
    a2a_interface=True,  # 啟用 A2A 協定
    tracing=True,  # 啟用 OpenTelemetry Tracing
    db=tracing_db,  # 使用獨立的資料庫記錄 tracing spans
)

# 取得 FastAPI app，並設定 root_path（反向代理用）
app = agent_os.get_app()
app.root_path = ROOT_PATH

# 啟用 GZip 壓縮中間件 — 對所有 >= 1KB 的回應進行壓縮
# 現有 4.7MB 圖表 HTML 壓縮後約 1.2MB；新圖表使用 CDN 模式後則 <100KB
app.add_middleware(GZipMiddleware, minimum_size=1024)

# 掛載圖片輸出目錄為靜態檔案
app.mount("/images", StaticFiles(directory=output_dir), name="images")

# 掛載 charts/ 静態目錄，讓 Plotly HTML 圖表可透過 /charts/ 路徑存取
app.mount("/charts", StaticFiles(directory=CHARTS_DIR, html=True), name="charts")

# 提供可下載的檔案（帶 Content-Disposition: attachment，瀏覽器直接觸發下載）
# 注意：使用 api_route 同時支援 GET 和 HEAD，因為 AgentOS 不會自動為 GET 路由啟用 HEAD
@app.api_route("/download/{filename}", methods=["GET", "HEAD"])
async def download_file(filename: str):
    file_path = os.path.join(DOWNLOADS_DIR, filename)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

# 也支援複數形式的路由 /downloads/
@app.api_route("/downloads/{filename}", methods=["GET", "HEAD"])
async def download_file_plural(filename: str):
    file_path = os.path.join(DOWNLOADS_DIR, filename)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ============================================================================
# Image Agent Session Proxy
# ============================================================================
# Image Agent 使用獨立的 session table (image_agent_sessions260223)，
# 避免 team 委派時 session_type 被覆寫。
# 以下 proxy 路由讓主 AgentOS 能查詢 Image Agent 的 sessions，
# 前端會合併兩個來源的結果。

@app.api_route("/image-agent/sessions", methods=["GET", "HEAD"])
async def proxy_image_agent_sessions(
    limit: int = Query(default=100, ge=1),
    user_id: Optional[str] = Query(default=None),
):
    """Proxy to image agent's sessions endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            params = {"type": "agent", "limit": limit}
            if user_id:
                params["user_id"] = user_id
            resp = await client.get(f"{IMAGE_AGENT_URL}/sessions", params=params)
            return resp.json()
    except Exception:
        # Image agent 可能未啟動，回傳空結果
        return {"data": [], "meta": {"page": 1, "limit": limit, "total_count": 0, "total_pages": 0}}


@app.api_route("/image-agent/sessions/{session_id}/runs", methods=["GET", "HEAD"])
async def proxy_image_agent_session_runs(session_id: str):
    """Proxy to image agent's session runs endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{IMAGE_AGENT_URL}/sessions/{session_id}/runs",
                params={"type": "agent"},
            )
            return resp.json()
    except Exception:
        return {"runs": []}


@app.delete("/image-agent/sessions/{session_id}")
async def proxy_delete_image_agent_session(session_id: str):
    """Proxy delete to image agent's session endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.delete(
                f"{IMAGE_AGENT_URL}/sessions/{session_id}",
                params={"type": "agent"},
            )
            if resp.status_code == 200:
                try:
                    return resp.json()
                except Exception:
                    return {"success": True}
        return {"success": True}
    except Exception:
        raise HTTPException(status_code=502, detail="Image agent is not available")


@app.post("/image-agent/sessions/{session_id}/rename")
async def proxy_rename_image_agent_session(session_id: str):
    """Proxy rename to image agent's session endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{IMAGE_AGENT_URL}/sessions/{session_id}/rename",
                params={"type": "agent"},
            )
            return resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail="Image agent is not available")


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Creative Research AgentOS")
    print("=" * 60)
    print()
    print("📋 Current Mode: Native RemoteAgent (agno 2.3.26+)")
    print("   (RemoteAgent 直接作為 Team 成員)")
    print()
    print(f"🌐 Server: http://localhost:{BACKEND_PORT}")
    print(f"📚 API Docs: http://localhost:{BACKEND_PORT}{ROOT_PATH}/docs")
    print(f"📂 Root Path: {ROOT_PATH}")
    print()
    print("Available endpoints (behind reverse proxy):")
    print(f"  - POST {ROOT_PATH}/agents/research-agent/runs  (Single Agent)")
    print(f"  - POST {ROOT_PATH}/agents/image-agent/runs  (Single Agent)")
    print(f"  - POST {ROOT_PATH}/teams/creative-team/runs    (Team Mode)")
    print(f"  - GET  {ROOT_PATH}/images/{{filename}}           (Generated Images)")
    print(f"  - GET  {ROOT_PATH}/download/{{filename}}         (Download Generated Files)")
    print(f"  - GET  {ROOT_PATH}/image-agent/sessions          (Image Agent Sessions Proxy)")
    print()
    print("⚠️  Make sure image_agent.py is running on port 9999!")
    print("=" * 60)
    
    agent_os.serve(app="main:app", host="0.0.0.0", port=BACKEND_PORT, reload=True)

