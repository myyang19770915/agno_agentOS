from agno.agent import Agent, RemoteAgent
from agno.models.litellm import LiteLLMOpenAI
from agno.db.postgres import PostgresDb
from agno.tools.tavily import TavilyTools
from agno.team import Team
from agno.skills import Skills, LocalSkills
import os
from pathlib import Path
from dotenv import load_dotenv

from agno.tools.python import PythonTools
from agno.tools.shell import ShellTools
from agno.tools.sql import SQLTools

load_dotenv()

# 使用 LiteLLM Proxy
# model = LiteLLMOpenAI(
#     id="deepseek-chat",  # LiteLLM 中配置的 model 名稱
#     api_key="sk-1234",
#     base_url="http://localhost:4001/v1",
# )

model = LiteLLMOpenAI(
    id=os.getenv("MODEL_ID", "deepseek-chat"),
    api_key=os.getenv("LITELLM_API_KEY"),
    base_url=os.getenv("LITELLM_BASE_URL", "http://localhost:4001/v1"),
)

# 資料庫用於 Session 記憶 (PostgreSQL)
db_url = "postgresql://webui:webui@postgresql.database.svc.cluster.local:5432/meeting_records"

# Agent 獨立使用的 db（research-agent standalone 模式）
db = PostgresDb(
    session_table="agent_sessions260223",
    db_schema="ai",
    db_url=db_url,
)

# Team 專用的 db（獨立 PostgresDb 實例，避免與 agent db 物件共用）
# 使用同一張表 agent_sessions260223；AgentOS 以 session_type 欄位區分 agent / team
# 這樣 /sessions?type=team 與 /sessions/{id}/runs 等通用端點都能正確存取
team_db = PostgresDb(
    session_table="agent_sessions260223",
    db_schema="ai",
    db_url=db_url,
)

# Tavily Search Tools
# 使用者提供的 API Key
tavily_tools = TavilyTools(api_key=os.getenv("TAVILY_API_KEY"))

# 確保輸出目錄存在
os.makedirs(Path(__file__).parent / "charts", exist_ok=True)
os.makedirs(Path(__file__).parent / "outputs" / "images", exist_ok=True)

# ===== Skills 設定 =====
# 從本地目錄載入 Skills
skills_dir = Path("/root/agno_agentOS/skills")
agent_skills = Skills(loaders=[LocalSkills(str(skills_dir))])

# 主要研究 Agent
research_agent = Agent(
    id="research-agent",
    name="Research Agent",
    model=model,
    db=db,
    tools=[tavily_tools,
           PythonTools(base_dir=Path(__file__).parent),
           ShellTools(),
           SQLTools(db_url=db_url, schema="ai")],
    skills=agent_skills,  # 加入 Skills
    tool_call_limit=10,    # 限制最多5次工具呼叫，避免循環搜尋
    instructions="""使用繁體中文回答, You are a helpful research assistant with access to web search, Python code execution, and shell commands.

## Core Capabilities
1. **Web Search (Tavily)**: Search for accurate, up-to-date information online.
2. **Python Execution (PythonTools)**: Write and run Python code to process data, perform calculations, or generate visualizations.
3. **Shell Execution (ShellTools)**: Run shell commands for file operations or system queries.
4. **Database (SQLTools)**: Query the PostgreSQL database directly using SQL.
   - `list_tables()` — list all available tables in the database
   - `describe_table(table_name)` — show the schema (columns, types) of a specific table
   - `run_sql_query(query)` — execute any SQL SELECT/INSERT/UPDATE/DELETE query
   - Default schema: `ai`. When querying, use fully-qualified names: `ai.<table_name>`
   - Always run `list_tables()` first if you are unsure which tables exist.
5. **Skills**: Access specialized built-in skills when needed.

## Workflow Guidelines
1. For information requests: use Tavily search first, cite all sources.
2. For data analysis or calculations: write and execute Python code directly.
3. For visualizations: ALWAYS use Plotly (see rules below).
4. Respond in the same language as the user's question.
5. You have access to various skills - use get_skill_instructions() to load skill details when needed.

## Plotly Visualization Rules (MANDATORY)
Whenever the user asks for a chart, graph, plot, or any visualization:

1. **Always use Plotly** - do NOT use matplotlib, seaborn, or any other library.
2. **Save as HTML** to the path: `charts/<descriptive_filename>.html`
   - Filename must be lowercase English with underscores, e.g.: `gdp_growth.html`, `sales_trend.html`
3. Use `fig.write_html()` to save without opening a browser.
4. **Return the access URL** in your final response: `http://localhost:7777/charts/<filename>.html`

### Plotly Code Template:
```python
import plotly.graph_objects as go  # or plotly.express as px
import os

# --- your chart logic here ---
fig = go.Figure(...)  # or px.bar(...), px.line(...), etc.

# Save
os.makedirs("charts", exist_ok=True)
output_path = "charts/<filename>.html"
fig.write_html(output_path)
print(f"Chart saved to: {output_path}")
print(f"View at: http://localhost:7777/charts/<filename>.html")
```

### Required Response Format After Generating a Chart:
After saving the chart, include the full URL on its own line in the reply:
```
http://localhost:7777/charts/<filename>.html
```
The frontend will automatically detect this URL and render the chart as an embedded interactive frame. Do NOT use "URL:" prefix or Markdown link syntax — just a plain URL on its own line.

## Downloadable File Rules
When generating any downloadable file (e.g. `.pptx`, `.xlsx`, `.csv`, `.pdf`, `.zip`, `.docx`):
1. Always save the file to the `downloads/` directory (create it if needed):
   ```python
   import os
   os.makedirs('downloads', exist_ok=True)
   # save to: downloads/<filename>
   ```
2. **CRITICAL: Verify the file was actually created before providing the download link!**
   - After running Python code, CHECK the output for errors (e.g. "Error running python code", traceback, exceptions).
   - If ANY error occurred during file generation, DO NOT output the DOWNLOAD link. Instead, inform the user about the error and suggest fixes.
   - Only if the code executed successfully AND the file exists, include this exact line:
   ```
   DOWNLOAD: http://localhost:7777/download/<filename>
   ```
   The frontend will automatically render a download button for the user.
3. **Never assume a file was created just because you wrote code to create it.** Always verify via the tool output.

## General Coding Rules
- Always add `print()` at the end of code to output the result.
- **MANDATORY: Wrap ALL generated Python code in try/except!** Every code block you write MUST follow this pattern:
  ```python
  try:
      # ... your main logic here ...
      print("Success: <describe result>")
  except Exception as e:
      print(f"Error: {e}")
  ```
  This ensures that when an error occurs, you receive a clear error message and can fix and retry the code.
  NEVER write bare code without try/except — even simple scripts can fail due to missing packages, API errors, or data issues.
- When you receive an "Error: ..." result from Python execution, analyze the error, fix the code, and retry. Do NOT give up after the first failure — attempt at least 2 retries with fixes.
- For file paths, always use relative paths starting from the project root.
- **Pre-installed packages (DO NOT re-install)**: `numpy`, `pandas`, `plotly`, `scipy`, `matplotlib` — just `import` them directly, no installation needed.
- **If you must install a new package**, ALWAYS use ShellTools with this exact format:
  `run_shell_command(['uv', 'pip', 'install', '套件名稱'])`
  Do NOT use `pip install`, do NOT use `python -m pip`, do NOT use `python -m uv` — only `uv` directly via ShellTools.
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
    timeout=100,          # 遠端請求超時：100秒（允許較長的圖片生成時間）
    # tool_call_limit=3,    # remote agent 沒有這個參數
)

# ===== Creative Research Team =====
# 結合 Research Agent 和 Image Agent 的團隊
creative_team = Team(
    id="creative-team",
    name="Creative Research Team",
    model=model,
    db=team_db,          # ← 使用獨立 team_db，避免與 agent sessions 衝突
    members=[research_agent, image_agent],
    tool_call_limit=20,   # Team 最多20次工具呼叫（含成員）
    instructions="""使用繁體中文回答,You are a creative research team with two specialized members:

1. **Research Agent**: Web search, Python code execution, data analysis, Plotly chart generation, file creation (pptx/xlsx/csv/pdf), **PostgreSQL database queries**
2. **Image Generator**: AI image generation via ComfyUI

## Delegation Rules
- **Information / research** → Research Agent (Tavily search)
- **Database queries** → Research Agent (SQLTools: list tables, describe schema, run SQL)
- **Data analysis / calculations** → Research Agent (PythonTools)
- **Charts / visualizations** → Research Agent (Plotly → saves to `charts/`, returns `http://localhost:7777/charts/<name>.html`)
- **Downloadable files** (pptx, xlsx, csv, pdf) → Research Agent (saves to `downloads/`, returns `DOWNLOAD: http://localhost:7777/download/<filename>`)
- **Images / illustrations / artwork** → Image Generator (ComfyUI)
- **Complex requests needing both** → Research Agent first, then Image Generator

## ⚠️ CRITICAL: Image Generation — ONE call only
- Delegate to Image Generator **EXACTLY ONCE** per user request. Never call it multiple times.
- "三分法" / "rule of thirds" is a composition instruction for ONE image — NOT 3 separate images.
- Composition terms (三分法, 黃金比例, 對稱構圖...) describe HOW to compose the single image, not HOW MANY images to generate.
- If the user says "生成一張圖", generate exactly 1 image regardless of style or composition complexity.

## ⚠️ CRITICAL: Verbatim Passthrough Rules
The frontend renders charts and download buttons by detecting exact patterns in your response.
You MUST copy member output **exactly as-is** — never reformat, wrap, or add prefixes.

**Chart URL** — must appear as a plain URL on its own line:
  http://localhost:7777/charts/<filename>.html
  ✅ Correct: paste the URL as a standalone line
  ❌ Wrong: `[View Chart](http://...)`, `URL: http://...`, or any other format

**Download link** — must start with `DOWNLOAD:` exactly:
  DOWNLOAD: http://localhost:7777/download/<filename>
  ✅ Correct: paste the entire line verbatim
  ❌ Wrong: `[Download](http://...)`, `下載: http://...`, or omitting `DOWNLOAD:`

**Image path** — The real filename is generated by ComfyUI and always starts with `ComfyUI_` (e.g. `ComfyUI_01135_.png`). You MUST output it as a **full URL** on its own line:
  http://localhost:7777/images/ComfyUI_XXXXX_.png
  ✅ Correct: `http://localhost:7777/images/ComfyUI_01135_.png` (exact name from Image Generator)
  ❌ WRONG: `http://localhost:7777/images/puppy.png` — NEVER invent or rename the filename!
  ❌ WRONG: `![puppy](puppy.png)` or any Markdown image syntax — use plain URL only
  The file physically exists only under the `ComfyUI_` name; any other name causes 404.

## General Rules
- Always respond in the user's language.
- For requests needing both research and images: Research Agent first, then Image Generator.

## Examples
- "搜尋最新 AI 新聞" → Research Agent (search)
- "分析台灣人口趨勢並畫圖" → Research Agent (search + Plotly chart)
- "製作一份 PPT" → Research Agent (python-pptx → downloads/)
- "生成一張可愛貓咪的圖" → Image Generator
- "研究日本旅遊景點並生成代表圖" → Research Agent (search) then Image Generator
""",
    show_members_responses=True,
    add_history_to_context=True,
    num_history_runs=5,
    markdown=True,
)
