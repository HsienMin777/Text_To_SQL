import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("找不到 GEMINI_API_KEY，請在 .env 檔案中設定後再執行。")

genai.configure(api_key=api_key)

print("正在查詢可用模型...")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"- {m.name}")
