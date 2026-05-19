import os
from dotenv import load_dotenv
from google import genai

# Load API Key
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("Danh sách các model AI khả dụng cho API Key của bạn:")

# Gọi API lấy danh sách model và lọc ra những con dòng "flash" cho nhẹ
for model in client.models.list():
    if "flash" in model.name:
        print("✅", model.name)