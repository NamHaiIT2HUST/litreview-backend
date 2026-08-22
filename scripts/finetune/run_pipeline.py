import requests
import pandas as pd
import json
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from sklearn.model_selection import train_test_split

print("==================================================")
print("🚀 PIPELINE TẠO 500 MẪU VÀNG (7 WORKERS ĐA LUỒNG)")
print("==================================================")

# 1. DANH SÁCH 7 API KEYS
GEMINI_API_KEYS = [
    "YOUR_API_KEY_HERE",
    "YOUR_API_KEY_HERE",
    "YOUR_API_KEY_HERE",
    "YOUR_API_KEY_HERE",
    "YOUR_API_KEY_HERE",
    "YOUR_API_KEY_HERE",
    "YOUR_API_KEY_HERE",
]

NUM_WORKERS = len(GEMINI_API_KEYS)
MODEL_NAME = "gemini-3.5-flash-lite"  # Model tối ưu, không bị giới hạn quota

# 2. SỐ LƯỢNG MẪU: 500 MẪU VÀNG CHUẨN LIMA
SAMPLE_SIZE = 500

if os.path.exists("raw_abstracts_massive.csv"):
    full_df = pd.read_csv("raw_abstracts_massive.csv")
    raw_df = full_df.head(SAMPLE_SIZE).copy()
    print(f"-> Đã chọn {len(raw_df)} bài báo khoa học chất lượng cao từ cache!")
else:
    print("-> Không tìm thấy raw_abstracts_massive.csv!")
    exit(1)

# 3. TEMPLATES
agent1_prompt = """You are an expert AI professor in __DOMAIN__. Read this paper abstract:
"__ABSTRACT__"

Based on this, invent a naive research idea a student might propose that is "too_broad" or "too_narrow".
Then, act as the professor and evaluate it.
Output strictly valid JSON with this schema:
{
  "instruction": "Evaluate the research scope and suggest refinements.",
  "input": "Domain: __DOMAIN__\\nTopic: __TITLE__\\nIdea: [Naive student idea in Vietnamese]",
  "output": "{\\"status\\\": \\"[too_broad or too_narrow]\\", \\\"feedback\\\": \\"[Expert feedback in Vietnamese]\\\", \\\"suggested_topics\\\": [\\\"[Refined topic 1 in Vietnamese]\\\", \\\"[Refined topic 2 in Vietnamese]\\\"]}"
}
Ensure the "output" field is a stringified JSON. No markdown tags."""

agent2_prompt = """You are a strict methodology expert in __DOMAIN__. Read this paper abstract:
"__ABSTRACT__"

Write PRISMA inclusion and exclusion criteria for a systematic literature review on this topic.
Output strictly valid JSON with this schema:
{
  "instruction": "Generate rigorous PRISMA inclusion and exclusion criteria.",
  "input": "Domain: __DOMAIN__\\nTopic: __TITLE__",
  "output": "{\\\"include\\\": [\\\"[Include criteria 1 in Vietnamese]\\\", \\\"[Include criteria 2 in Vietnamese]\\\"], \\\"exclude\\\": [\\\"[Exclude criteria 1 in Vietnamese]\\\", \\\"[Exclude criteria 2 in Vietnamese]\\\"]}"
}
Ensure the "output" field is a stringified JSON. No markdown tags."""

agent3_prompt = """You are a technical research librarian expert in __DOMAIN__. Read this paper abstract:
"__ABSTRACT__"

Extract the PICO elements and construct a Boolean academic search query string (AND, OR, parentheses).
Output strictly valid JSON with this schema:
{
  "instruction": "Extract PICO elements and generate a robust Boolean search query.",
  "input": "Topic: __TITLE__",
  "output": "{\\\"P\\\": \\\"[Problem/Population in English]\\\", \\\"I\\\": \\\"[Intervention/Method in English]\\\", \\\"C\\\": \\\"[Comparison/Baseline in English]\\\", \\\"O\\\": \\\"[Outcome/Metric in English]\\\", \\\"boolean_query\\\": \\\"[Robust boolean query string]\\\"}"
}
Ensure the "output" field is a stringified JSON. No markdown tags."""

# 4. HÀM GỌI API QUA REST (KHÔNG BỊ LOCK THREAD)
def call_gemini_rest(prompt, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    r = requests.post(url, json=payload, timeout=15)
    if r.status_code == 200:
        text = r.json()['candidates'][0]['content']['parts'][0]['text']
        return text
    raise ValueError(f"HTTP {r.status_code}: {r.text[:100]}")

def process_single_row(args):
    index, row, prompt_template, key = args
    prompt = (prompt_template
              .replace('__DOMAIN__', str(row.get('domain', '')))
              .replace('__ABSTRACT__', str(row.get('abstract', '')))
              .replace('__TITLE__', str(row.get('title', ''))))
    
    for retry in range(3):
        try:
            raw_json_str = call_gemini_rest(prompt, key)
            data_point = json.loads(raw_json_str)
            if isinstance(data_point.get('output'), dict):
                data_point['output'] = json.dumps(data_point['output'], ensure_ascii=False)
            elif isinstance(data_point.get('output'), str):
                json.loads(data_point['output'])
            return data_point
        except Exception:
            time.sleep(1)
            continue
    return None

def run_single_agent(df, prompt_template, agent_name, prefix):
    output_raw = f"raw_{prefix}_all.jsonl"
    print(f"\n⚡ BẮT ĐẦU TẠO {agent_name.upper()} ({len(df)} MẪU) - DỰ KIẾN ~5-6 PHÚT...")
    
    tasks = []
    for idx, (_, row) in enumerate(df.iterrows()):
        key = GEMINI_API_KEYS[idx % NUM_WORKERS]
        tasks.append((idx, row, prompt_template, key))
    
    valid_results = []
    with open(output_raw, 'w', encoding='utf-8') as f:
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            futures = [executor.submit(process_single_row, t) for t in tasks]
            for future in tqdm(as_completed(futures), total=len(futures), desc=f"Đang sinh {agent_name}"):
                res = future.result()
                if res:
                    f.write(json.dumps(res, ensure_ascii=False) + '\n')
                    f.flush()
                    valid_results.append(res)
    
    print(f"✅ Hoàn thành {len(valid_results)}/{len(df)} mẫu hợp lệ!")
    
    # Chia train (85%) và test (15%)
    if len(valid_results) >= 10:
        train, test = train_test_split(valid_results, test_size=0.15, random_state=42)
        with open(f'{prefix}_train.jsonl', 'w', encoding='utf-8') as f:
            for r in train:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        with open(f'{prefix}_test.jsonl', 'w', encoding='utf-8') as f:
            for r in test:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        print(f"🎉 Đã lưu: {prefix}_train.jsonl ({len(train)} mẫu) & {prefix}_test.jsonl ({len(test)} mẫu)")

# CHỌN CHẾ ĐỘ CHẠY
print("\n--- BẠN MUỐN CHẠY PHẦN NÀO? ---")
print("1. Chỉ chạy Agent 1 (Scope Optimizer)  ~ 5 phút")
print("2. Chỉ chạy Agent 2 (Criteria Gen)     ~ 5 phút")
print("3. Chỉ chạy Agent 3 (Keywords & PICO)  ~ 5 phút")
print("4. Chạy TẤT CẢ 3 Agents (Full 1.500 mẫu) ~ 15-18 phút")

choice = input("\nNhập lựa chọn của bạn (1/2/3/4) rồi ấn Enter [Mặc định: 4]: ").strip()
if not choice:
    choice = "4"

if choice == "1":
    run_single_agent(raw_df, agent1_prompt, "Agent 1 (Scope)", "agent1_scope")
elif choice == "2":
    run_single_agent(raw_df, agent2_prompt, "Agent 2 (Criteria)", "agent2_criteria")
elif choice == "3":
    run_single_agent(raw_df, agent3_prompt, "Agent 3 (Keywords)", "agent3_pico")
else:
    run_single_agent(raw_df, agent1_prompt, "Agent 1 (Scope)", "agent1_scope")
    run_single_agent(raw_df, agent2_prompt, "Agent 2 (Criteria)", "agent2_criteria")
    run_single_agent(raw_df, agent3_prompt, "Agent 3 (Keywords)", "agent3_pico")

print("\n🏆 XONG HOÀN TOÀN! DỮ LIỆU ĐÃ NẰM GỌN TRÊN MÁY BẠN!")


