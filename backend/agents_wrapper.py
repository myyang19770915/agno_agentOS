"""
Agents Wrapper Module - 使用 RemoteAgent Wrapper 模式

這個模組將 RemoteAgent 包裝成本地 Agent，解決 RemoteAgent 無法直接作為 Team 成員的問題。

架構：
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
"""

from agno.agent import Agent, RemoteAgent
from agno.models.litellm import LiteLLMOpenAI
from agno.db.postgres import PostgresDb
from agno.tools.tavily import TavilyTools
from agno.tools import tool
from agno.team import Team
from dotenv import load_dotenv
import os
import logging

# 載入環境變數
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== Model Configuration =====
model = LiteLLMOpenAI(
    id=os.getenv("MODEL_ID", "deepseek-chat"),
    api_key=os.getenv("LITELLM_API_KEY"),
    base_url=os.getenv("LITELLM_BASE_URL", "http://localhost:4001/v1"),
)

# ===== Database for Session Memory (PostgreSQL) =====
db_url = "postgresql://webui:webui@postgresql.database.svc.cluster.local:5432/meeting_records"

db = PostgresDb(
    session_table="agent_sessions260223",
    db_schema="ai",
    db_url=db_url,
)

# ===== Research Agent (本地) =====
tavily_tools = TavilyTools(api_key=os.getenv("TAVILY_API_KEY"))

research_agent = Agent(
    id="research-agent",
    name="Research Agent",
    model=model,
    db=db,
    tools=[tavily_tools],
    tool_call_limit=5,    # 限制最夹5次工具呼叫，避免循環搜尋
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

# ===== RemoteAgent 連接遠端 Image Agent (port 9999) =====
remote_image_agent = RemoteAgent(
    base_url=os.getenv("IMAGE_AGENT_URL", "http://localhost:9999"),
    agent_id="image-generator",
)

# ===== 創建包裝 Tool 來調用 RemoteAgent =====
@tool(name="generate_image_via_remote")
async def call_remote_image_agent(
    image_prompt: str,
    width: int = 1024,
    height: int = 1024
) -> str:
    """
    使用遠端 Image Generator Agent 生成圖片。
    
    Args:
        image_prompt: 詳細的圖片描述提示詞，應為清晰的英文描述。
        width: 圖片寬度，範圍 512-2048，預設 1024。
        height: 圖片高度，範圍 512-2048，預設 1024。
    
    Returns:
        遠端 Agent 的回應，包含圖片路徑。
    """
    logger.info(f"🎨 Calling RemoteAgent with prompt: {image_prompt[:50]}... Size: {width}x{height}")
    
    try:
        # 將尺寸資訊包含在訊息中
        message = f"Please generate an image with size {width}x{height} using the following prompt: {image_prompt}"
        response = await remote_image_agent.arun(
            message,
            user_id="wrapper-agent",
        )
        logger.info(f"✅ RemoteAgent response received")
        return response.content
    except Exception as e:
        logger.error(f"❌ Error calling RemoteAgent: {e}")
        return f"Error calling remote image agent: {str(e)}"


# ===== Image Agent Wrapper (本地) =====
# 這個 Agent 包裝了 RemoteAgent，可以正常加入 Team
image_agent = Agent(
    id="image-agent",
    name="Image Generator",
    model=model,
    tools=[call_remote_image_agent],
    instructions="""You are an AI image generation assistant.

## Your Workflow:
1. Analyze the user's request to understand what image they want
2. Create an optimal prompt in ENGLISH for image generation
3. Determine the appropriate image size:
   - Square (1024x1024): General purpose, portraits - BEST QUALITY
   - Landscape (1280x720): Scenery, banners
   - Portrait (720x1280): Mobile wallpapers, posters
4. Call the generate_image_via_remote tool with the prompt AND size parameters
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
# 使用 Wrapper Agent 而不是直接使用 RemoteAgent
creative_team = Team(
    id="creative-team",
    name="Creative Research Team",
    model=model,
    db=db,
    members=[research_agent, image_agent],  # ✅ 使用 wrapper
    tool_call_limit=10,   # 整個 Team 最多10次工具呼叫
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
    add_history_to_context=True,
    num_history_runs=3,
    markdown=True,
)
