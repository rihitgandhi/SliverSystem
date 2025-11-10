#!/usr/bin/env python3
"""List all available Gemini models"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY', 'AIzaSyD77xnWvyPutXCe3jJfN1zB2l5lDVVwOm4')
genai.configure(api_key=api_key)

print("Available Gemini models:")
print("=" * 60)
try:
    for model in genai.list_models():
        print(f"\nModel: {model.name}")
        print(f"  Display Name: {model.display_name}")
        print(f"  Description: {model.description}")
        print(f"  Supported Methods: {model.supported_generation_methods}")
except Exception as e:
    print(f"Error listing models: {e}")
    print(f"Error type: {type(e).__name__}")
