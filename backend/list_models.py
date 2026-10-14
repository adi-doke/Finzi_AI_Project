import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='backend/.env')

api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print("Listing models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error listing models: {e}")
