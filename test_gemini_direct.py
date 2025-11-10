#!/usr/bin/env python3
"""
Direct test of Google Gemini API to verify configuration and connectivity
"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

def test_gemini_api():
    """Test the Gemini API configuration and connectivity"""
    print("=" * 60)
    print("Google Gemini API Test")
    print("=" * 60)
    
    # Get API key from config
    api_key = os.getenv('GEMINI_API_KEY', 'AIzaSyD77xnWvyPutXCe3jJfN1zB2l5lDVVwOm4')
    
    print(f"\n1. API Key Status:")
    if api_key and api_key != '':
        print(f"   ✓ API Key Found: {api_key[:10]}...{api_key[-4:]}")
    else:
        print("   ✗ API Key NOT Found or Empty")
        return False
    
    print(f"\n2. Configuring Gemini API...")
    try:
        genai.configure(api_key=api_key)
        print("   ✓ API Configuration Successful")
    except Exception as e:
        print(f"   ✗ Configuration Failed: {str(e)}")
        return False
    
    print(f"\n3. Testing Model Creation...")
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        print("   ✓ Model Created Successfully (gemini-2.5-flash)")
    except Exception as e:
        print(f"   ✗ Model Creation Failed: {str(e)}")
        return False
    
    print(f"\n4. Testing Content Generation...")
    try:
        prompt = "Say 'Hello, I am working!' in exactly 5 words."
        response = model.generate_content(prompt)
        print(f"   ✓ Content Generation Successful")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ✗ Content Generation Failed: {str(e)}")
        print(f"   Error Type: {type(e).__name__}")
        print(f"   Error Details: {str(e)}")
        
        # Check for common error types
        if "API_KEY_INVALID" in str(e) or "invalid" in str(e).lower():
            print("\n   DIAGNOSIS: Invalid API Key")
            print("   - The API key may be incorrect or expired")
            print("   - Generate a new key at: https://makersuite.google.com/app/apikey")
        elif "quota" in str(e).lower():
            print("\n   DIAGNOSIS: Quota Exceeded")
            print("   - You may have exceeded the free tier limits")
            print("   - Check quota at: https://console.cloud.google.com/")
        elif "403" in str(e):
            print("\n   DIAGNOSIS: Permission Denied")
            print("   - The API key may not have permission to use this model")
            print("   - Verify API is enabled in Google Cloud Console")
        elif "404" in str(e):
            print("\n   DIAGNOSIS: Model Not Found")
            print("   - The model name may be incorrect")
            print("   - Try 'gemini-1.5-flash' or 'gemini-1.5-pro' instead")
        
        return False
    
    print(f"\n5. Testing Available Models...")
    try:
        models = genai.list_models()
        print("   ✓ Available Models:")
        for m in models:
            if 'gemini' in m.name.lower():
                print(f"      - {m.name}")
    except Exception as e:
        print(f"   ⚠ Could not list models: {str(e)}")
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED - Gemini API is working correctly!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_gemini_api()
    if not success:
        print("\n" + "=" * 60)
        print("✗ TESTS FAILED - See errors above")
        print("=" * 60)
        exit(1)
