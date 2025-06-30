import requests
import json
import time

def test_render_api_detailed():
    # Replace with your actual Render service URL
    base_url = "https://sliversystem-backend.onrender.com"
    
    print("🔍 DEBUGGING RENDER API")
    print("=" * 50)
    print(f"Base URL: {base_url}")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 1: Health Check
    print("1️⃣ Testing Health Check...")
    try:
        response = requests.get(f"{base_url}/api/health", timeout=15)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        print(f"   Response Text: {response.text}")
        
        if response.status_code == 200:
            print("   ✅ Health check PASSED")
        else:
            print("   ❌ Health check FAILED")
            
    except requests.exceptions.Timeout:
        print("   ❌ TIMEOUT: Request took too long")
    except requests.exceptions.ConnectionError:
        print("   ❌ CONNECTION ERROR: Cannot connect to server")
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
    
    print("-" * 50)
    
    # Test 2: Chat API
    print("2️⃣ Testing Chat API...")
    try:
        data = {"message": "Hello, test message"}
        response = requests.post(
            f"{base_url}/api/chat", 
            json=data, 
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   Response Length: {len(result.get('response', ''))} characters")
            print("   ✅ Chat API PASSED")
        else:
            print(f"   Response Text: {response.text}")
            print("   ❌ Chat API FAILED")
            
    except requests.exceptions.Timeout:
        print("   ❌ TIMEOUT: Request took too long")
    except requests.exceptions.ConnectionError:
        print("   ❌ CONNECTION ERROR: Cannot connect to server")
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
    
    print("-" * 50)
    
    # Test 3: Score API
    print("3️⃣ Testing Score API...")
    try:
        data = {"url": "https://example.com"}
        response = requests.post(
            f"{base_url}/api/score", 
            json=data, 
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   Score: {result.get('score', 'N/A')}")
            print("   ✅ Score API PASSED")
        else:
            print(f"   Response Text: {response.text}")
            print("   ❌ Score API FAILED")
            
    except requests.exceptions.Timeout:
        print("   ❌ TIMEOUT: Request took too long")
    except requests.exceptions.ConnectionError:
        print("   ❌ CONNECTION ERROR: Cannot connect to server")
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
    
    print("-" * 50)
    
    # Test 4: CORS Preflight
    print("4️⃣ Testing CORS Preflight...")
    try:
        response = requests.options(
            f"{base_url}/api/chat",
            headers={
                'Origin': 'https://yourusername.github.io',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            },
            timeout=10
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   CORS Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("   ✅ CORS Preflight PASSED")
        else:
            print("   ❌ CORS Preflight FAILED")
            
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")

if __name__ == "__main__":
    test_render_api_detailed() 