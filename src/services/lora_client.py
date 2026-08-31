import json
import logging
import os

import aiohttp

logger = logging.getLogger(__name__)

# Cấu hình LORA_API_URL trong biến môi trường (Ví dụ: URL ngrok từ Colab, hoặc http://localhost:8000)
LORA_API_URL = os.getenv("LORA_API_URL")

async def call_lora_model(agent_name: str, instruction: str, input_text: str) -> dict | None:
    """
    Gọi tới máy chủ LoRA (Local hoặc Colab Ngrok).
    Nếu không có kết nối, trả về None để hệ thống tự động Fallback sang Gemini.

    agent_name: lora_agent1_scope | lora_agent2_criteria | lora_agent3_pico
    """
    if not LORA_API_URL:
        return None

    prompt_template = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{instruction}

### Input:
{input}

### Response:
"""
    prompt = prompt_template.format(instruction=instruction, input=input_text)

    try:
        async with aiohttp.ClientSession() as session:
            # Gửi request tới vLLM / FastAPI Server đang host LoRA
            # Cấu trúc API tương thích OpenAI chuẩn
            payload = {
                "model": agent_name,
                "prompt": prompt,
                "max_tokens": 256,
                "temperature": 0.1
            }
            async with session.post(f"{LORA_API_URL}/v1/completions", json=payload, timeout=10) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    raw_text = result["choices"][0]["text"].strip()

                    # Clean markdown code blocks if any
                    clean_text = raw_text.replace("```json", "").replace("```", "").strip()
                    return json.loads(clean_text)
                else:
                    logger.warning(f"LoRA Server trả về lỗi: {resp.status}")
    except Exception as e:
        logger.warning(f"Không thể kết nối LoRA Server ({LORA_API_URL}): {e}")

    return None
