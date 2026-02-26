import httpx
import json
import logging
import random
import uuid
import asyncio
import threading

COMFYUI_URL = "http://192.168.37.71:30631"
logger = logging.getLogger(__name__)

import os

# 全域 Semaphore：同時只跑一張圖，避免 ComfyUI 並發 timeout
# 使用 threading.Semaphore（非 asyncio），避免「bound to a different event loop」錯誤
# 因為每次 asyncio.run() 在獨立 thread 執行，asyncio.Semaphore 會綁死初始 loop
_image_semaphore = threading.Semaphore(1)

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
    workflow_path = os.path.join(os.path.dirname(__file__), "workflow_image2.json")
    
    try:
        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow = json.load(f)
    except FileNotFoundError:
        logger.error(f"Workflow file not found at {workflow_path}!")
        return None

    # Update input parameters
    # Node 15: GoogleTranslateTextNode (Text Prompt)
    # Node 6: KSampler (Random Seed)
    
    prompt_node_id = "15"
    ksampler_node_id = "6"
    
    if prompt_node_id in workflow:
        workflow[prompt_node_id]["inputs"]["text"] = prompt
    else:
        logger.error(f"Node {prompt_node_id} not found in workflow")

    if ksampler_node_id in workflow:
        seed = random.randint(1, 100000000000000)
        workflow[ksampler_node_id]["inputs"]["seed"] = seed
    
    # 設定圖片尺寸 (Node 4: EmptySD3LatentImage)
    size_node_id = "4"
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

    # 每張圖需 ~30s；Semaphore 序列化後可能需等前張完成，給 5 分鐘緩衝
    timeout = httpx.Timeout(300.0, connect=10.0)

    # 全域序列鎖：一次只跑一張，避免多張並行全部 timeout
    # threading.Semaphore.acquire() 為阻塞式，在 ThreadPoolExecutor 子執行緒中可安全呼叫
    logger.info("Waiting for image slot (serialized queue)...")
    _image_semaphore.acquire()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # 1. Queue Prompt
            logger.info(f"Queueing image generation for: {prompt[:40]}...")
            resp = await client.post(f"{COMFYUI_URL}/prompt", json=prompt_payload)
            resp.raise_for_status()
            prompt_id = resp.json()["prompt_id"]

            # 2. Poll /history 直到完成；180 次 × 1s = 最多等 3 分鐘
            completed = False
            filename = ""
            retries = 180

            while not completed and retries > 0:
                await asyncio.sleep(1)
                hist_resp = await client.get(f"{COMFYUI_URL}/history/{prompt_id}")
                if hist_resp.status_code == 200:
                    history = hist_resp.json()
                    if prompt_id in history:
                        outputs = history[prompt_id].get("outputs", {})
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
                            completed = True  # Stop polling
                else:
                    logger.warning(f"Failed to check history: {hist_resp.status_code}")
                retries -= 1

            if completed and filename:
                # Download image from ComfyUI to local storage
                view_url = f"{COMFYUI_URL}/view?filename={filename}&type=output"

                local_dir = "outputs/images"
                os.makedirs(local_dir, exist_ok=True)
                local_path = os.path.join(local_dir, filename)

                img_resp = await client.get(view_url)
                if img_resp.status_code == 200:
                    with open(local_path, "wb") as f:
                        f.write(img_resp.content)
                    logger.info(f"Saved image to {local_path}")
                    return local_path
                else:
                    logger.error("Failed to download image from ComfyUI")
                    return view_url
            else:
                logger.warning("Image generation timed out after 3 minutes")
                return None
    except Exception as e:
        logger.error(f"ComfyUI Error: {e}")
        return None
    finally:
        _image_semaphore.release()
