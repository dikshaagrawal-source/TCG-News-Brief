"""Run this to diagnose Gemini API issues: python3 test_gemini.py"""
from dotenv import load_dotenv
load_dotenv()
import os
from google import genai
from google.genai import types

api_key = os.environ.get("GEMINI_API_KEY", "")
print(f"Key found: {bool(api_key)} | prefix: {api_key[:10]}...")

client = genai.Client(api_key=api_key)

models_to_try = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
    "gemini-2.0-flash",
    "gemini-pro",
]

for model in models_to_try:
    try:
        print(f"\nTrying {model}...", end=" ", flush=True)
        response = client.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=[types.Part(text="Say hello in 3 words.")])]
        )
        print(f"✅ WORKS! Response: {response.text.strip()}")
        print(f"\n>>> Use this model: {model}")
        break
    except Exception as e:
        print(f"❌ {type(e).__name__}: {e}")
