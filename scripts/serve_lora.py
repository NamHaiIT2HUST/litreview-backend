import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch

# Khởi tạo FastAPI
app = FastAPI(title="SLR Swarm LoRA Server", version="1.0")

# Biến toàn cục lưu trữ model và tokenizer
model = None
tokenizer = None
current_adapter = None

class CompletionRequest(BaseModel):
    model: str  # Tên adapter: lora_agent1_scope, lora_agent2_criteria, lora_agent3_pico
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.1

def load_base_model():
    global model, tokenizer
    print("Loading Base Model (4-bit)...")
    try:
        from unsloth import FastLanguageModel
        max_seq_length = 8192
        dtype = None
        load_in_4bit = True

        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name = "unsloth/llama-3-8b-Instruct",
            max_seq_length = max_seq_length,
            dtype = dtype,
            load_in_4bit = load_in_4bit,
        )
        FastLanguageModel.for_inference(model) # Enable native 2x faster inference
        print("Base Model loaded successfully!")
    except Exception as e:
        print(f"Lỗi khi load base model: {e}")
        print("Vui lòng đảm bảo bạn đang chạy môi trường có hỗ trợ Unsloth/GPU.")

def switch_adapter(adapter_name: str):
    global current_adapter, model
    if not model:
        raise HTTPException(status_code=500, detail="Base model not loaded")
        
    if current_adapter == adapter_name:
        return # Đã load rồi
        
    adapter_path = os.path.join("models", adapter_name)
    if not os.path.exists(adapter_path):
        raise HTTPException(status_code=404, detail=f"Adapter {adapter_name} không tồn tại tại {adapter_path}")
        
    print(f"Switching adapter to: {adapter_name}...")
    try:
        # Nếu đã có adapter khác, cần unload (hoặc peft tự đè lên nếu dùng load_adapter với tên mới)
        # Tuy nhiên với unsloth/peft, đơn giản nhất là set_adapter
        model.load_adapter(adapter_path, adapter_name=adapter_name)
        model.set_adapter(adapter_name)
        current_adapter = adapter_name
        print(f"Successfully switched to {adapter_name}!")
    except Exception as e:
        print(f"Lỗi khi switch adapter: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/completions")
async def generate_completion(req: CompletionRequest):
    if not model:
        raise HTTPException(status_code=500, detail="Model server is not fully initialized.")
        
    # Switch sang adapter yêu cầu (Agent 1, 2 hoặc 3)
    switch_adapter(req.model)
    
    inputs = tokenizer([req.prompt], return_tensors="pt").to("cuda")
    
    outputs = model.generate(
        **inputs,
        max_new_tokens=req.max_tokens,
        use_cache=True,
        temperature=req.temperature,
    )
    
    # Bỏ qua phần prompt trong kết quả output
    input_len = inputs["input_ids"].shape[1]
    generated_text = tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True)
    
    return {
        "id": "cmpl-lora",
        "object": "text_completion",
        "model": req.model,
        "choices": [
            {
                "text": generated_text,
                "index": 0,
                "finish_reason": "stop"
            }
        ]
    }

@app.on_event("startup")
async def startup_event():
    # Khởi chạy trong thread ngầm hoặc trực tiếp
    # Tuy nhiên trên local Windows có thể tắt đi nếu chỉ muốn chạy backend mock
    if os.getenv("ENABLE_LOCAL_MODEL") == "true":
        load_base_model()

if __name__ == "__main__":
    print("=========================================================")
    print("🚀 SLR Swarm LoRA Inference Server")
    print("Khởi chạy: uvicorn scripts.serve_lora:app --host 0.0.0.0 --port 8000")
    print("Lưu ý: Yêu cầu GPU và Unsloth. Đặt ENABLE_LOCAL_MODEL=true")
    print("=========================================================")
    uvicorn.run("serve_lora:app", host="0.0.0.0", port=8000, reload=False)
