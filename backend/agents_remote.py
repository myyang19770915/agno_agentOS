from agno.agent import Agent, RemoteAgent
from agno.models.litellm import LiteLLMOpenAI
from agno.db.sqlite import SqliteDb
from agno.tools.tavily import TavilyTools
from agno.team import Team
from agno.skills import Skills, LocalSkills
import os
from pathlib import Path

# 使用 LiteLLM Proxy
model = LiteLLMOpenAI(
    id="deepseek-chat",  # LiteLLM 中配置的 model 名稱
    api_key="sk-1234",
    base_url="http://localhost:4001/v1",
)

# 資料庫用於 Session 記憶
storage_dir = "tmp"
if not os.path.exists(storage_dir):
    os.makedirs(storage_dir)

db = SqliteDb(db_file=f"{storage_dir}/agent.db")

# Tavily Search Tools
# 使用者提供的 API Key
tavily_tools = TavilyTools(api_key="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")

# ===== Skills 設定 =====
# 從本地目錄載入 Skills
skills_dir = Path(r"D:\agy\my_agent_app\.agent\skills")
agent_skills = Skills(loaders=[LocalSkills(str(skills_dir))])

# 主要研究 Agent
research_agent = Agent(
    id="research-agent",
    name="Research Agent",
    model=model,
    db=db,
    tools=[tavily_tools],
    skills=agent_skills,  # 加入 Skills
    instructions="""You are a helpful research assistant with access to specialized skills.
    1. Use Tavily search to find accurate and up-to-date information.
    2. Provide detailed answers based on the search results.
    3. Always cite your sources.
    4. Respond in the same language as the user's question.
    5. You have access to various skills - use get_skill_instructions() to load skill details when needed.
    """,
    add_history_to_context=True,
    num_history_runs=5,
    add_datetime_to_context=True,
    # enable_agentic_memory=True,  # 暫時禁用：DeepSeek 模型有時生成不合規 JSON
    markdown=True,
)

# ===== Image Generation Agent via RemoteAgent =====
# 根據 Agno 文檔，base_url 應該是 AgentOS 的根 URL
image_agent = RemoteAgent(
    base_url="http://localhost:9999",
    agent_id="image-generator",
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
