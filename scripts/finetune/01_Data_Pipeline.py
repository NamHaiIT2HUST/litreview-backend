# %% [markdown]
# # Notebook 1: Data Pipeline (Chạy trên máy Dell của bạn)
# Hướng dẫn chạy:
# 1. Cài đặt thư viện: `pip install requests pandas google-generativeai tqdm`
# 2. Bấm nút "Run Cell" (hoặc Shift + Enter) cho từng ô code dưới đây.

# %%
# Cài đặt thư viện (Chạy 1 lần)
# !pip install requests pandas google-generativeai tqdm

# %%
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import google.generativeai as genai
import json
import time
from tqdm import tqdm

# ==========================================
# CẤU HÌNH API KEY CỦA BẠN Ở ĐÂY
# ==========================================
GEMINI_API_KEY = "YOUR_API_KEY_HERE"
genai.configure(api_key=GEMINI_API_KEY)

# Sử dụng model Gemini 1.5 Flash (nhanh và rẻ) để sinh data
model = genai.GenerativeModel('gemini-1.5-flash')

# %% [markdown]
# ## Bước 1: Cào Dữ Liệu Thô (Raw Data) từ ArXiv (Toán & Robotics)
# Chúng ta sẽ cào khoảng 50 bài báo mẫu để làm demo.

# %%
def fetch_arxiv_abstracts(query, max_results=50):
    url = f'http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={max_results}'
    print(f"Đang tải dữ liệu cho từ khóa: {query}...")
    response = requests.get(url)
    root = ET.fromstring(response.content)
    
    abstracts = []
    for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
        title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()
        summary = entry.find('{http://www.w3.org/2005/Atom}summary').text.strip()
        abstracts.append({'title': title, 'abstract': summary, 'domain': query})
        
    return abstracts

# Lấy 25 bài Robotics và 25 bài Toán học
robotics_data = fetch_arxiv_abstracts("robotics", 25)
math_data = fetch_arxiv_abstracts("optimization", 25)

raw_df = pd.DataFrame(robotics_data + math_data)
raw_df.to_csv('raw_abstracts.csv', index=False)
print(f"Đã lưu {len(raw_df)} bài báo thô vào file raw_abstracts.csv")
raw_df.head()

# %% [markdown]
# ## Bước 2: Dùng Gemini Tổng hợp Dataset cho Agent 1 (Scope Optimizer)
# Đưa Abstract thô cho Gemini và yêu cầu nó tạo JSON gồm: Idea, Status, Feedback, Suggested Topics.

# %%
agent1_prompt_template = """
You are an expert AI professor in {domain}. Read the following paper abstract:
"{abstract}"

Based on this, invent a naive research idea a student might propose that is "too_broad" or "too_narrow".
Then, act as the professor and evaluate it.
Output strictly in JSON format like this:
{{
  "instruction": "Evaluate the research scope and suggest refinements.",
  "input": "Domain: {domain}\\nTopic: {title}\\nIdea: [Insert naive idea here]",
  "output": "{{\\"status\\": \\"[too_broad, too_narrow, or optimal]\\", \\"feedback\\": \\"[Your expert feedback in Vietnamese]\\", \\"suggested_topics\\": [\\"[Suggest 2-3 specific topics in Vietnamese]\\"]}}"
}}
Ensure the JSON is valid and the "output" field is a stringified JSON. Do not include markdown formatting like ```json in the output, just raw JSON.
"""

def generate_agent1_dataset(df):
    dataset = []
    print("Bắt đầu gọi Gemini API để sinh Dataset cho Agent 1...")
    
    # Rút gọn lặp qua 5 bài đầu tiên để demo chạy thử (Bạn có thể đổi thành len(df) để chạy hết)
    for index, row in tqdm(df.head(5).iterrows(), total=5):
        prompt = agent1_prompt_template.format(
            domain=row['domain'], 
            abstract=row['abstract'], 
            title=row['title']
        )
        try:
            response = model.generate_content(prompt)
            # Lọc bỏ markdown ```json nếu Gemini vô tình sinh ra
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            data_point = json.loads(clean_text)
            dataset.append(data_point)
            time.sleep(3) # Tránh bị rate limit của Google API
        except Exception as e:
            print(f"Lỗi ở dòng {index}: {e}")
            
    return dataset

agent1_data = generate_agent1_dataset(raw_df)

# Lưu ra file JSONL chuẩn để Train
with open('dataset_agent1.jsonl', 'w', encoding='utf-8') as f:
    for item in agent1_data:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
print("Đã tạo xong file dataset_agent1.jsonl! Sẵn sàng mang lên Colab.")


