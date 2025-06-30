import requests
import json

def test_render_api():
    # Replace this with your actual Render service URL
    base_url = "https://sliversystem-backend.onrender.com"
    
    print("Testing Render API endpoints...")
    print(f"Base URL: {base_url}")
    print("-" * 50)
    
    # Test 1: Health Check
    print("1. Testing Health Check...")
    try:
        response = requests.get(f"{base_url}/api/health", timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        if response.status_code == 200:
            print("   ✅ Health check passed!")
        else:
            print("   ❌ Health check failed!")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    print("-" * 50)
    
    # Test 2: Score API
    print("2. Testing Score API...")
    try:
        data = {"url": "https://example.com"}
        response = requests.post(
            f"{base_url}/api/score", 
            json=data, 
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Score: {result.get('score', 'N/A')}")
            print(f"   ✅ Score API working!")
        else:
            print(f"   Response: {response.text}")
            print("   ❌ Score API failed!")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    print("-" * 50)
    
    # Test 3: Chat API
    print("3. Testing Chat API...")
    try:
        data = {"message": "Hello, can you help me with accessibility?"}
        response = requests.post(
            f"{base_url}/api/chat", 
            json=data, 
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Response length: {len(result.get('response', ''))} characters")
            print("   ✅ Chat API working!")
        else:
            print(f"   Response: {response.text}")
            print("   ❌ Chat API failed!")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

if __name__ == "__main__":
    test_render_api() 