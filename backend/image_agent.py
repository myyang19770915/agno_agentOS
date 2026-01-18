"""
Image Generation Agent with A2A Interface

This agent generates images using ComfyUI based on user prompts.
It runs as a separate A2A-enabled service on port 9999.
"""

from agno.agent import Agent
from agno.models.litellm import LiteLLMOpenAI
from agno.os import AgentOS
from agno.tools import tool
from dotenv import load_dotenv
import os
import logging

from image import generate_image
from agno.db.sqlite import SqliteDb

# 載入環境變數
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 使用 LiteLLM Proxy (從環境變數載入)
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

# 圖片輸出目錄
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs", "images")
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Image generation tool
@tool(name="generate_image_with_comfyui")
async def generate_image_tool(
    image_prompt: str,
    width: int = 1024,
    height: int = 1024
) -> str:
    """
    使用 ComfyUI 根據提示詞生成圖片。
    
    Args:
        image_prompt: 詳細的圖片描述提示詞，應清晰描述想要生成的圖片內容。
        width: 圖片寬度，範圍 512-2048，預設 1024。建議使用 1024 以獲得最佳效果。
        height: 圖片高度，範圍 512-2048，預設 1024。建議使用 1024 以獲得最佳效果。
    
    Returns:
        生成圖片的檔案路徑，若失敗則返回錯誤訊息。
    """
    logger.info(f"Generating image with prompt: {image_prompt[:50]}... Size: {width}x{height}")
    
    try:
        result = await generate_image(image_prompt, width=width, height=height)
        if result:
            logger.info(f"Image generated successfully: {result}")
            return f"Image generated successfully. Size: {width}x{height}. Path: {result}"
        else:
            return "Failed to generate image. Please try again with a different prompt."
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        return f"Error generating image: {str(e)}"


# Image Generator Agent
image_generator = Agent(
    id="image-generator",
    name="Image Generator",
    model=model,
    db=db,
    add_history_to_context=True,
    num_history_runs=5,
    add_datetime_to_context=True,
    # enable_agentic_memory=True,  # 暫時禁用：DeepSeek 模型有時生成不合規 JSON
    tools=[generate_image_tool],
    instructions="""You are an AI image generation assistant powered by ComfyUI.

## Your Workflow:
1. Analyze the user's request to understand what image they want
2. Create an optimal prompt in ENGLISH for image generation
3. Determine the appropriate image size based on the content:
   - Square images (1024x1024): General purpose, portraits, icons - BEST QUALITY
   - Landscape (1280x720 or 1024x768): Scenery, banners, wallpapers
   - Portrait (720x1280 or 768x1024): Mobile wallpapers, portraits, posters
4. Call the generate_image_with_comfyui tool with the prompt AND size parameters
5. **IMPORTANT: You MUST include the exact image path in your response!**

## Image Size Guidelines:
- Valid range: 512 to 2048 pixels for both width and height
- **Optimal size: 1024x1024** - Provides the best quality output
- For landscapes/banners: 1280x720 or 1024x768
- For portraits/mobile: 720x1280 or 768x1024
- Larger sizes (e.g., 2048x2048) require more processing time

## Prompt Guidelines:
- Be specific and detailed about visual elements
- Include style descriptors (photorealistic, anime, watercolor, etc.)
- Describe lighting, mood, and composition
- Always use ENGLISH for the image prompt

## Example Prompt Transformations:
- "台北夜景" → "Night cityscape of Taipei 101, neon lights reflecting on wet streets, cyberpunk atmosphere, ultra detailed, 8k" (1280x720 for landscape)
- "可愛的貓咪" → "Adorable fluffy cat sitting on a windowsill, soft natural lighting, bokeh background, warm colors" (1024x1024 for portrait)
- "手機桌布" → Use 720x1280 for mobile wallpaper format

## CRITICAL OUTPUT FORMAT:
After generating the image, your response MUST include this exact format:

"Image generated successfully! 
Size: [width]x[height]
Path: outputs/images/[filename].png"

The path MUST be included so the frontend can display the image. Never omit the path!

Respond in the user's language, but always include the English path.
""",
    markdown=True
)

# 建立 AgentOS 並啟用 A2A 介面
agent_os = AgentOS(
    name="Image Generator AgentOS",
    description="A2A-enabled image generation service using ComfyUI",
    agents=[image_generator],
    a2a_interface=True,  # 啟用 A2A 協定
)

app = agent_os.get_app()

if __name__ == "__main__":
    print("=" * 60)
    print("🎨 Image Generator Agent (A2A Enabled)")
    print("=" * 60)
    print(f"Server: http://localhost:9999")
    print(f"Agent Card: http://localhost:9999/a2a/agents/image-generator/.well-known/agent-card.json")
    print(f"API Docs: http://localhost:9999/docs")
    print("=" * 60)
    
    agent_os.serve(app="image_agent:app", host="0.0.0.0", port=9999, reload=True)
