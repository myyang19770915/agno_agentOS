"""
Team Test: 純原生 Agno Agent 組成的 Team
將 Image Agent 和 Research Agent 整合在同一個檔案中測試

這個版本不使用 RemoteAgent，而是直接在本地定義兩個 Agent 組成 Team
"""

from agno.agent import Agent
from agno.models.litellm import LiteLLMOpenAI
from agno.db.sqlite import SqliteDb
from agno.tools.tavily import TavilyTools
from agno.tools import tool
from agno.team import Team
import os
import asyncio
import logging

from image import generate_image  # 引入本地的圖片生成函數

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

db = SqliteDb(db_file=f"{storage_dir}/team_native.db")

# ===== Research Agent =====
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

# ===== Image Generation Tool =====
@tool(name="generate_image_with_comfyui")
async def generate_image_tool(
    image_prompt: str,
    width: int = 1024,
    height: int = 1024
) -> str:
    """
    使用 ComfyUI 根據提示詞生成圖片。
    
    Args:
        image_prompt: 詳細的英文圖片描述提示詞。
        width: 圖片寬度，範圍 512-2048，預設 1024。
        height: 圖片高度，範圍 512-2048，預設 1024。
    
    Returns:
        生成圖片的檔案路徑，若失敗則返回錯誤訊息。
    """
    logger.info(f"🎨 Generating image with prompt: {image_prompt[:50]}... Size: {width}x{height}")
    
    try:
        result = await generate_image(image_prompt, width=width, height=height)
        if result:
            logger.info(f"✅ Image generated successfully: {result}")
            return f"Image generated successfully. Size: {width}x{height}. Path: {result}"
        else:
            return "Failed to generate image. Please try again with a different prompt."
    except Exception as e:
        logger.error(f"❌ Error generating image: {e}")
        return f"Error generating image: {str(e)}"

# ===== Image Agent =====
image_agent = Agent(
    id="image-agent",
    name="Image Generator",
    model=model,
    tools=[generate_image_tool],
    instructions="""You are an AI image generation assistant powered by ComfyUI.

## Your Workflow:
1. Analyze the user's request to understand what image they want
2. Create an optimal prompt in ENGLISH for image generation
3. Determine the appropriate image size:
   - Square (1024x1024): General purpose, portraits - BEST QUALITY
   - Landscape (1280x720): Scenery, banners
   - Portrait (720x1280): Mobile wallpapers, posters
4. Call the generate_image_with_comfyui tool with the prompt AND size parameters
5. **IMPORTANT: You MUST include the exact image path in your response!**

## Image Size Guidelines:
- Valid range: 512 to 2048 pixels
- **Optimal: 1024x1024** for best quality

## Prompt Guidelines:
- Be specific and detailed about visual elements
- Include style descriptors (photorealistic, anime, watercolor, etc.)
- Describe lighting, mood, and composition
- Always use ENGLISH for the image prompt

## CRITICAL OUTPUT FORMAT:
After generating the image, your response MUST include this exact format:

"Image generated successfully! 
Size: [width]x[height]
Path: outputs/images/[filename].png"

The path MUST be included so the frontend can display the image. Never omit the path!

Respond in the user's language, but always include the English path.
""",
    markdown=True,
)

# ===== Creative Research Team =====
creative_team = Team(
    id="creative-team",
    name="Creative Research Team",
    model=model,
    db=db,
    members=[research_agent, image_agent],
    instructions="""You are a creative research team with two specialized members:

1. **Research Agent**: Expert at web searching and gathering information using Tavily
2. **Image Generator**: Expert at creating images using ComfyUI

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


# ===== Test Functions =====
async def test_research_only():
    """測試單獨的研究功能"""
    print("\n" + "=" * 60)
    print("🔬 Test 1: Research Agent Only")
    print("=" * 60)
    
    response = await creative_team.arun(
        "搜尋 2025 年人工智慧最新發展趨勢",
        user_id="test-user",
    )
    print(f"\n📝 Response:\n{response.content}")


async def test_image_only():
    """測試單獨的圖片生成功能"""
    print("\n" + "=" * 60)
    print("🎨 Test 2: Image Generator Only")
    print("=" * 60)
    
    response = await creative_team.arun(
        "生成一張可愛的3D皮克斯風格貓咪圖片",
        user_id="test-user",
    )
    print(f"\n📝 Response:\n{response.content}")


async def test_combined():
    """測試結合研究和圖片生成的任務"""
    print("\n" + "=" * 60)
    print("🚀 Test 3: Combined Research + Image Generation")
    print("=" * 60)
    
    response = await creative_team.arun(
        "先網路蒐集 Elon Musk 的人物特徵，然後畫一張他的肖像畫",
        user_id="test-user",
    )
    print(f"\n📝 Response:\n{response.content}")


async def main():
    print("=" * 60)
    print("🧪 Testing Native Agno Team (No RemoteAgent)")
    print("=" * 60)
    
    # 選擇要執行的測試
    print("\n選擇測試項目:")
    print("1. Research Agent Only")
    print("2. Image Generator Only")
    print("3. Combined (Research + Image)")
    print("4. Run All Tests")
    
    choice = input("\n請輸入選項 (1-4): ").strip()
    
    if choice == "1":
        await test_research_only()
    elif choice == "2":
        await test_image_only()
    elif choice == "3":
        await test_combined()
    elif choice == "4":
        await test_research_only()
        await test_image_only()
        await test_combined()
    else:
        print("無效選項，執行 Image Generator Only 測試...")
        await test_image_only()
    
    print("\n" + "=" * 60)
    print("✅ Test Completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
