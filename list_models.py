"""List available Gemini models"""
import sys
sys.path.insert(0, 'backend')

from dotenv import load_dotenv
import os
load_dotenv()

import google.generativeai as genai

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print("Available Gemini Models:")
print("=" * 60)

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"✓ {model.name}")
        print(f"  Display Name: {model.display_name}")
        print(f"  Description: {model.description}")
        print()
