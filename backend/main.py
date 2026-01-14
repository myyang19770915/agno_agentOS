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
import os

# ============================================================================
# 選擇使用的模式 (取消註解要使用的模式)
# ============================================================================

# ----- 模式 1: 原始模式 (httpx Tool 調用遠端 image_agent 服務) -----
# from agents import research_agent, creative_team

# ----- 模式 2: RemoteAgent Wrapper 模式 -----
# from agents_wrapper import research_agent, creative_team

# ----- 模式 3: Native RemoteAgent 模式 (推薦，需要 agno 2.3.26+) -----
# 直接使用 RemoteAgent 作為 Team 成員，無需 Wrapper
from agents_remote import research_agent, creative_team


# ============================================================================
# 確保圖片輸出目錄存在
# ============================================================================
output_dir = os.path.join(os.path.dirname(__file__), "outputs", "images")
if not os.path.exists(output_dir):
    os.makedirs(output_dir)


# ============================================================================
# 建立 AgentOS
# ============================================================================
agent_os = AgentOS(
    name="Creative Research AgentOS",
    description="Agent with session memory, web search, and image generation via RemoteAgent",
    agents=[research_agent],
    teams=[creative_team],
    a2a_interface=True,  # 啟用 A2A 協定
)

# 取得 FastAPI app
app = agent_os.get_app()

# 掛載圖片輸出目錄為靜態檔案
app.mount("/images", StaticFiles(directory=output_dir), name="images")


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Creative Research AgentOS")
    print("=" * 60)
    print()
    print("📋 Current Mode: Native RemoteAgent (agno 2.3.26+)")
    print("   (RemoteAgent 直接作為 Team 成員)")
    print()
    print(f"🌐 Server: http://localhost:7777")
    print(f"📚 API Docs: http://localhost:7777/docs")
    print()
    print("Available endpoints:")
    print("  - POST /agents/research-agent/runs  (Single Agent)")
    print("  - POST /teams/creative-team/runs    (Team Mode)")
    print("  - GET  /images/{filename}           (Generated Images)")
    print()
    print("⚠️  Make sure image_agent.py is running on port 9999!")
    print("=" * 60)
    
    agent_os.serve(app="main:app", host="0.0.0.0", port=7777, reload=True)

