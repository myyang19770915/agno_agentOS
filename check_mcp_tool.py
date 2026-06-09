# 在 Python shell 中（需在 async 環境）
import asyncio
import os
from dotenv import load_dotenv

# 自動載入 backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))

from backend.agents_remote import mcp_tools

async def list_tools():
    await mcp_tools.connect()
    tools = [f.name for f in mcp_tools.functions.values()]
    print(f"共 {len(tools)} 個工具：")
    for name in tools:
        print(f"  - {name}")
    await mcp_tools.close()

asyncio.run(list_tools())