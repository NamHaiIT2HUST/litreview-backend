# %% [markdown]
# # Notebook 2: Train & Eval bằng Unsloth (CHẠY TRÊN GOOGLE COLAB)
# Hướng dẫn:
# 1. Truy cập https://colab.research.google.com/
# 2. Tạo sổ tay mới (New Notebook).
# 3. Vào Runtime -> Change runtime type -> Chọn T4 GPU.
# 4. Copy các cell code dưới đây vào Colab và chạy tuần tự.
# 5. Đừng quên upload file `dataset_agent1.jsonl` (đã tạo ở Notebook 1) lên thư mục bên trái của Colab trước khi chạy.

# %% [markdown]
# ## Bước 1: Cài đặt thư viện Unsloth (Nhanh gấp 2 lần bình thường)
# %%
# !pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
# !pip install --no-deps xformers trl peft accelerate bitsandbytes

# %% [markdown]
# ## Bước 2: Tải Mô hình Llama-3-8B-Instruct (Base Model)
# %%
from unsloth import FastLanguageModel
import torch
max_seq_length = 2048 # Độ dài context, 2048 là đủ cho task của chúng ta
dtype = None # Tự động chọn (Float16 cho T4)
load_in_4bit = True # BẮT BUỘC bật 4-bit để vừa với 16GB VRAM của Colab

print("Đang tải Base Model...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "unsloth/llama-3-8b-Instruct-bnb-4bit", # Bản đã nén 4-bit siêu nhẹ
    max_seq_length = max_seq_length,
    dtype = dtype,
    load_in_4bit = load_in_4bit,
)

# Thêm kỹ thuật LoRA (Chỉ train 1 phần nhỏ của mạng neural)
model = FastLanguageModel.get_peft_model(
    model,
    r = 16, # Rank, 16 là mức chuẩn
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                      "gate_proj", "up_proj", "down_proj",],
    lora_alpha = 16,
    lora_dropout = 0,
    bias = "none",
    use_gradient_checkpointing = "unsloth",
    random_state = 3407,
    use_rslora = False,
    loftq_config = None,
)
print("Hoàn tất gắn LoRA!")

# %% [markdown]
# ## Bước 3: Nạp Dataset của Agent 1
# %%
from datasets import load_dataset

# Template để format dữ liệu đầu vào cho Llama 3
prompt_template = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{}

### Input:
{}

### Response:
{}"""

EOS_TOKEN = tokenizer.eos_token # Cần thiết để model biết khi nào dừng sinh chữ
def formatting_prompts_func(examples):
    instructions = examples["instruction"]
    inputs       = examples["input"]
    outputs      = examples["output"]
    texts = []
    for instruction, input, output in zip(instructions, inputs, outputs):
        text = prompt_template.format(instruction, input, output) + EOS_TOKEN
        texts.append(text)
    return { "text" : texts, }

# Nạp file bạn đã upload lên Colab
dataset = load_dataset("json", data_files="dataset_agent1.jsonl", split="train")
dataset = dataset.map(formatting_prompts_func, batched = True,)

print(f"Đã nạp {len(dataset)} mẫu dữ liệu!")

# %% [markdown]
# ## Bước 4: Bắt đầu Huấn Luyện (Fine-tuning)
# %%
from trl import SFTTrainer
from transformers import TrainingArguments

trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "text",
    max_seq_length = max_seq_length,
    dataset_num_proc = 2,
    packing = False, # Có thể làm train nhanh hơn cho chuỗi ngắn
    args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        warmup_steps = 5,
        max_steps = 60, # Tăng số này lên (vd: 300) khi train data thật. 60 chỉ để demo.
        learning_rate = 2e-4,
        fp16 = not torch.cuda.is_bf16_supported(),
        bf16 = torch.cuda.is_bf16_supported(),
        logging_steps = 1,
        optim = "adamw_8bit",
        weight_decay = 0.01,
        lr_scheduler_type = "linear",
        seed = 3407,
        output_dir = "outputs",
    ),
)

# Chạy lệnh Train! (Có thể mất 15p - 2 tiếng tùy số step)
print("BẮT ĐẦU TRAINING...")
trainer_stats = trainer.train()

# %% [markdown]
# ## Bước 5: Lưu Model LoRA
# %%
model.save_pretrained("lora_agent1_llama3")
tokenizer.save_pretrained("lora_agent1_llama3")
print("Đã lưu tệp trọng số LoRA vào thư mục lora_agent1_llama3! Hãy nén lại tải về máy.")

# %% [markdown]
# ## Bước 6: Chạy thử (Inference)
# %%
FastLanguageModel.for_inference(model) # Bật chế độ suy luận siêu nhanh

# Đưa ra một Idea hoàn toàn mới để test con AI vừa train
test_instruction = "Evaluate the research scope and suggest refinements."
test_input = "Domain: Robotics\nTopic: Dùng AI làm cánh tay robot\nIdea: Dùng AI cho robot nhặt rác"

prompt = prompt_template.format(test_instruction, test_input, "") # Bỏ trống phần output
inputs = tokenizer([prompt], return_tensors = "pt").to("cuda")

print("\n--- KẾT QUẢ AI SINH RA (AGENT 1) ---")
outputs = model.generate(**inputs, max_new_tokens = 256, use_cache = True)
print(tokenizer.batch_decode(outputs, skip_special_tokens = True)[0])
