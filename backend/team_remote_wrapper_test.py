"""
Team Test: 使用 RemoteAgent Wrapper 方案
將 RemoteAgent 包裝成本地 Agent，解決 Team 兼容性問題

這個方案：
1. RemoteAgent 連接遠端的 image_agent 服務 (localhost:9999)
2. 創建一個本地 Wrapper Agent，透過 Tool 調用 RemoteAgent
3. Wrapper Agent 可以正常加入 Team
"""

from agno.agent import Agent, RemoteAgent
from agno.models.litellm import LiteLLMOpenAI
from agno.db.sqlite import SqliteDb
from agno.tools.tavily import TavilyTools
from agno.tools import tool
from agno.team import Team
import os
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== Model Configuration =====
model = LiteLLMOpenAI(
    id="deepseek-chat",
    api_key="sk-1234",
    base_url="http://localhost:4001/v1",
)

# ===== Database for Session Memory =====
storage_dir = "tmp"
if not os.path.exists(storage_dir):
    os.makedirs(storage_dir)

db = SqliteDb(db_file=f"{storage_dir}/team_remote_wrapper.db")

# ===== Research Agent (本地) =====
tavily_tools = TavilyTools(api_key="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")

research_agent = Agent(
    id="research-agent",
    name="Research Agent",
    model=model,
    tools=[tavily_tools],
    instructions="""You are a helpful research assistant.
    1. Use Tavily search to find accurate and up-to-date information.
    2. Provide detailed answers based on the search results.
    3. Always cite your sources.
    4. Respond in the same language as the user's question.
    """,
    markdown=True,
)

# ===== RemoteAgent 連接遠端 Image Agent =====
remote_image_agent = RemoteAgent(
    base_url="http://localhost:9999",
    agent_id="image-generator",
)

# ===== 創建包裝 Tool 來調用 RemoteAgent =====
@tool(name="generate_image_via_remote")
async def call_remote_image_agent(image_prompt: str) -> str:
    """
    Generate an image using the remote Image Generator Agent.
    
    Args:
        image_prompt: A detailed description of the image to generate.
                     Should be a clear, descriptive prompt in ENGLISH.
    
    Returns:
        The response from the remote agent, including the image path.
    """
    logger.info(f"🎨 Calling RemoteAgent with prompt: {image_prompt[:50]}...")
    
    try:
        response = await remote_image_agent.arun(
            image_prompt,
            user_id="wrapper-agent",
        )
        logger.info(f"✅ RemoteAgent response received")
        return response.content
    except Exception as e:
        logger.error(f"❌ Error calling RemoteAgent: {e}")
        return f"Error calling remote image agent: {str(e)}"


# ===== Image Agent Wrapper (本地) =====
# 這個 Agent 包裝了 RemoteAgent，可以正常加入 Team
image_agent_wrapper = Agent(
    id="image-wrapper",
    name="Image Generator",
    model=model,
    tools=[call_remote_image_agent],
    instructions="""You are an AI image generation assistant.

## Your Workflow:
1. Analyze the user's request to understand what image they want
2. Create an optimal prompt in ENGLISH for image generation
3. Call the generate_image_via_remote tool with the prompt
4. **IMPORTANT: You MUST include the exact image path in your response!**

## Prompt Guidelines:
- Be specific and detailed about visual elements
- Include style descriptors (photorealistic, anime, watercolor, etc.)
- Describe lighting, mood, and composition
- Always use ENGLISH for the image prompt

## CRITICAL OUTPUT FORMAT:
After generating the image, your response MUST include this exact format:

"Image generated successfully! 
Path: outputs/images/[filename].png"

The path MUST be included so the frontend can display the image. Never omit the path!

Respond in the user's language, but always include the English path.
""",
    markdown=True,
)

# ===== Creative Research Team =====
# 使用 Wrapper Agent 而不是直接使用 RemoteAgent
creative_team = Team(
    id="creative-team",
    name="Creative Research Team",
    model=model,
    db=db,
    members=[research_agent, image_agent_wrapper],  # ✅ 使用 wrapper
    instructions="""You are a creative research team with two specialized members:

1. **Research Agent**: Expert at web searching and gathering information using Tavily
2. **Image Generator**: Expert at creating images using a remote AI service

Your workflow:
- When users ask for information or research, delegate to Research Agent
- When users want images, illustrations, or visual content, delegate to Image Generator
- For complex requests requiring both, coordinate between members

IMPORTANT: When the Image Generator creates an image, make sure to include the image path in your final response!
The path format should be: outputs/images/[filename].png

Always respond in the user's language. Be creative and helpful!

Examples:
- "搜尋最新的 AI 新聞" → Delegate to Research Agent
- "生成一張可愛貓咪的圖" → Delegate to Image Generator
- "研究日本旅遊景點並生成代表圖" → Use Research Agent first, then Image Generator
""",
    show_members_responses=True,
    markdown=True,
)


# ===== Test Functions (Async Stream Mode) =====
async def test_research_only():
    """測試單獨的研究功能 (Stream 輸出)"""
    print("\n" + "=" * 60)
    print("🔬 Test 1: Research Agent Only (Stream)")
    print("=" * 60)
    
    await creative_team.aprint_response(
        "搜尋 2025 年人工智慧最新發展趨勢",
        user_id="test-user",
        stream=True,
    )


async def test_image_only():
    """測試單獨的圖片生成功能 (透過 RemoteAgent Wrapper, Stream 輸出)"""
    print("\n" + "=" * 60)
    print("🎨 Test 2: Image Generator via RemoteAgent Wrapper (Stream)")
    print("=" * 60)
    
    await creative_team.aprint_response(
        "生成一張可愛的3D皮克斯風格貓咪圖片",
        user_id="test-user",
        stream=True,
    )


async def test_combined():
    """測試結合研究和圖片生成的任務 (Stream 輸出)"""
    print("\n" + "=" * 60)
    print("🚀 Test 3: Combined Research + Image Generation (Stream)")
    print("=" * 60)
    
    await creative_team.aprint_response(
        "先網路蒐集 Elon Musk 的人物特徵，然後畫一張他的肖像畫",
        user_id="test-user",
        stream=True,
    )


async def test_remote_agent_directly():
    """直接測試 RemoteAgent 是否連接正常"""
    print("\n" + "=" * 60)
    print("🔌 Test 0: Direct RemoteAgent Connection")
    print("=" * 60)
    
    try:
        response = await remote_image_agent.arun(
            "A cute 3D Pixar-style cat",
            user_id="direct-test",
        )
        print(f"\n✅ RemoteAgent Response:\n{response.content}")
    except Exception as e:
        print(f"\n❌ RemoteAgent Error: {e}")


def main():
    print("=" * 60)
    print("🧪 Testing Team with RemoteAgent Wrapper (Stream Mode)")
    print("=" * 60)
    print("\n📋 Architecture:")
    print("   ┌─────────────────────────────────────┐")
    print("   │           Creative Team             │")
    print("   ├─────────────────┬───────────────────┤")
    print("   │ Research Agent  │ Image Wrapper     │")
    print("   │   (local)       │   (local agent)   │")
    print("   │                 │        ↓          │")
    print("   │                 │  RemoteAgent      │")
    print("   │                 │        ↓          │")
    print("   │                 │  image_agent:9999 │")
    print("   └─────────────────┴───────────────────┘")
    
    print("\n選擇測試項目:")
    print("0. Direct RemoteAgent Connection Test")
    print("1. Research Agent Only (Stream)")
    print("2. Image Generator via Wrapper (Stream)")
    print("3. Combined - Research + Image (Stream)")
    print("4. Run All Tests")
    
    choice = input("\n請輸入選項 (0-4): ").strip()
    
    if choice == "0":
        asyncio.run(test_remote_agent_directly())
    elif choice == "1":
        asyncio.run(test_research_only())
    elif choice == "2":
        asyncio.run(test_image_only())
    elif choice == "3":
        asyncio.run(test_combined())
    elif choice == "4":
        asyncio.run(run_all_tests())
    else:
        print("無效選項，執行 Image Generator via Wrapper 測試...")
        asyncio.run(test_image_only())
    
    print("\n" + "=" * 60)
    print("✅ Test Completed!")
    print("=" * 60)


async def run_all_tests():
    """執行所有測試"""
    await test_remote_agent_directly()
    await test_research_only()
    await test_image_only()
    await test_combined()


if __name__ == "__main__":
    main()
