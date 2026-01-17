from agno.agent import Agent
from agno.models.litellm import LiteLLMOpenAI
from agno.db.sqlite import SqliteDb
from agno.tools.tavily import TavilyTools
from agno.tools import tool
from agno.team import Team
from dotenv import load_dotenv
import os
import httpx
import json

# 載入環境變數
load_dotenv()

# 使用 LiteLLM Proxy
model = LiteLLMOpenAI(
    id=os.getenv("MODEL_ID", "deepseek-chat"),
    api_key=os.getenv("LITELLM_API_KEY"),
    base_url=os.getenv("LITELLM_BASE_URL", "http://localhost:4001/v1"),
)

# 資料庫用於 Session 記憶
storage_dir = "tmp"
if not os.path.exists(storage_dir):
    os.makedirs(storage_dir)

db = SqliteDb(db_file=f"{storage_dir}/agent.db")

# Tavily Search Tools
tavily_tools = TavilyTools(api_key=os.getenv("TAVILY_API_KEY"))

# 主要研究 Agent
research_agent = Agent(
    id="research-agent",
    name="Research Agent",
    model=model,
    db=db,
    tools=[tavily_tools],
    instructions="""You are a helpful research assistant.
    1. Use Tavily search to find accurate and up-to-date information.
    2. Provide detailed answers based on the search results.
    3. Always cite your sources.
    4. Respond in the same language as the user's question.
    """,
    add_history_to_context=True,
    num_history_runs=5,
    add_datetime_to_context=True,
    enable_agentic_memory=True,
    markdown=True,
)

# ===== Image Generation Tool (透過 A2A 呼叫遠端服務) =====
IMAGE_AGENT_URL = os.getenv("IMAGE_AGENT_URL", "http://localhost:9999")

@tool(name="generate_image")
async def call_image_agent(
    prompt: str,
    width: int = 1024,
    height: int = 1024
) -> str:
    """
    使用 A2A 協定呼叫遠端 Image Generator Agent 生成圖片。
    
    Args:
        prompt: 圖片描述，應具體說明風格、顏色和構圖。
        width: 圖片寬度，範圍 512-2048，預設 1024。
        height: 圖片高度，範圍 512-2048，預設 1024。
    
    Returns:
        生成圖片的路徑，或錯誤訊息。
    """
    try:
        timeout = httpx.Timeout(120.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            # 呼叫遠端 Agent 的 runs endpoint，包含尺寸資訊
            message = f"Please generate an image with size {width}x{height} using the following prompt: {prompt}"
            response = await client.post(
                f"{IMAGE_AGENT_URL}/agents/image-generator/runs",
                data={
                    "message": message,
                    "stream": "False"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                result = response.json()
                # 嘗試從結果中提取內容
                content = result.get("content", result.get("output", str(result)))
                return content
            else:
                return f"Error calling Image Agent: HTTP {response.status_code}"
                
    except Exception as e:
        return f"Error connecting to Image Agent: {str(e)}"

# 本地 Image Agent (使用 Tool 呼叫遠端服務)
image_agent = Agent(
    id="image-agent",
    name="Image Generator",
    model=model,
    tools=[call_image_agent],
    instructions="""You are an AI image generation assistant.

## Your Workflow:
1. Analyze the user's request to understand what image they want
2. Create an optimal prompt in ENGLISH for image generation
3. Determine the appropriate image size:
   - Square (1024x1024): General purpose, portraits - BEST QUALITY
   - Landscape (1280x720): Scenery, banners
   - Portrait (720x1280): Mobile wallpapers, posters
4. Call the generate_image tool with the prompt AND size parameters
5. **CRITICAL: You MUST include the image path from the tool response in your final answer!**

## Image Size Guidelines:
- Valid range: 512 to 2048 pixels
- **Optimal: 1024x1024** for best quality

## Prompt Guidelines:
- Be specific and detailed about visual elements
- Include style descriptors (photorealistic, anime, watercolor, etc.)
- Describe lighting, mood, and composition
- Always use ENGLISH for the image prompt

## CRITICAL OUTPUT FORMAT:
After the image is generated, you MUST include the path in your response like this:

"Image generated successfully!
Size: [width]x[height]
Path: outputs/images/[filename].png"

The image path from the tool output MUST be included in your response. 
This is required for the frontend to display the image. Never omit it!

Respond in the user's language, but always include the English path.
""",
    markdown=True,
)

# ===== Creative Research Team =====
# 結合 Research Agent 和 Image Agent 的團隊
creative_team = Team(
    id="creative-team",
    name="Creative Research Team",
    model=model,
    db=db,
    members=[research_agent, image_agent],
    instructions="""You are a creative research team with two specialized members:

1. **Research Agent**: Expert at web searching and gathering information
2. **Image Generator**: Expert at creating images using AI

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
    add_history_to_context=True,
    num_history_runs=3,
    markdown=True,
)
