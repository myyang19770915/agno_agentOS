import httpx
import json
import logging
import random
import uuid
import asyncio

COMFYUI_URL = "http://127.0.0.1:8002"
logger = logging.getLogger(__name__)

import os

# ... imports ...

async def generate_image(prompt: str, width: int = 1024, height: int = 1024) -> str:
    """
    使用 ComfyUI 生成圖片並返回檔案名稱/URL。
    
    Args:
        prompt: 圖片生成提示詞
        width: 圖片寬度（建議範圍 512-2048，預設 1024）
        height: 圖片高度（建議範圍 512-2048，預設 1024）
    
    Returns:
        生成圖片的本地路徑，若失敗則返回 None
    """
    # Load the workflow template
    workflow_path = os.path.join(os.path.dirname(__file__), "workflow_imagez.json")
    
    try:
        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow = json.load(f)
    except FileNotFoundError:
        logger.error(f"Workflow file not found at {workflow_path}!")
        return None

    # Update input parameters
    # Node 45: Text Prompt
    # Node 44: Random Seed
    
    prompt_node_id = "45"
    ksampler_node_id = "44"
    
    if prompt_node_id in workflow:
        workflow[prompt_node_id]["inputs"]["text"] = prompt
    else:
        logger.error(f"Node {prompt_node_id} not found in workflow")

    if ksampler_node_id in workflow:
        seed = random.randint(1, 100000000000000)
        workflow[ksampler_node_id]["inputs"]["seed"] = seed
    
    # 設定圖片尺寸 (Node 41: EmptySD3LatentImage)
    size_node_id = "41"
    if size_node_id in workflow:
        # 限制尺寸在合理範圍內 (512-2048)
        width = max(512, min(2048, width))
        height = max(512, min(2048, height))
        workflow[size_node_id]["inputs"]["width"] = width
        workflow[size_node_id]["inputs"]["height"] = height
        logger.info(f"Image size set to {width}x{height}")
    else:
        logger.warning(f"Size node {size_node_id} not found in workflow, using default size")
    
    # Send to ComfyUI
    client_id = str(uuid.uuid4())
    prompt_payload = {
        "prompt": workflow,
        "client_id": client_id
    }
    
    timeout = httpx.Timeout(120.0, connect=10.0)
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # 1. Queue Prompt
            logger.info(f"Queueing image generation for: {prompt[:30]}...")
            resp = await client.post(f"{COMFYUI_URL}/prompt", json=prompt_payload)
            resp.raise_for_status()
            prompt_id = resp.json()["prompt_id"]
            
            # 2. Wait for completion (Polling history)
            # This is a simplified approach. Ideally use Websockets.
            # For MVP, we poll /history/{prompt_id}
            
            completed = False
            filename = ""
            retries = 60 # Increase to 60 seconds
            
            while not completed and retries > 0:
                await asyncio.sleep(1)
                hist_resp = await client.get(f"{COMFYUI_URL}/history/{prompt_id}")
                if hist_resp.status_code == 200:
                    history = hist_resp.json()
                    # logger.info(f"Checking history for {prompt_id}: {history}") # Verbose debug
                    if prompt_id in history:
                        # Found execution results
                        outputs = history[prompt_id].get("outputs", {})
                        
                        # Iterate over all outputs to find images, don't rely on hardcoded node ID "9"
                        for node_id, node_output in outputs.items():
                            if "images" in node_output:
                                images = node_output["images"]
                                if images:
                                    filename = images[0]["filename"]
                                    completed = True
                                    logger.info(f"Found image in node {node_id}: {filename}")
                                    break
                        
                        if not completed:
                             logger.warning(f"Prompt {prompt_id} finished but no images found in outputs: {outputs.keys()}")
                             completed = True # Stop polling
                else:
                    logger.warning(f"Failed to check history: {hist_resp.status_code}")
                retries -= 1
            
            if completed:
                # Download image from ComfyUI to local storage
                view_url = f"{COMFYUI_URL}/view?filename={filename}&type=output"
                
                local_dir = "outputs/images"
                if not os.path.exists(local_dir):
                    os.makedirs(local_dir)
                    
                local_path = os.path.join(local_dir, filename)
                
                # Fetch and save
                img_resp = await client.get(view_url)
                if img_resp.status_code == 200:
                    with open(local_path, "wb") as f:
                        f.write(img_resp.content)
                    logger.info(f"Saved image to {local_path}")
                    # Return local relative path
                    return local_path
                else:
                    logger.error("Failed to download image from ComfyUI")
                    return view_url # Fallback
            else:
                logger.warning("Image generation timed out")
                return None

    except Exception as e:
        logger.error(f"ComfyUI Error: {e}")
        return None
