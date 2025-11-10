import requests
import json
import time

print("="*70)
print("DEBUGGING ACCESSIBILITY SCORE FEATURE - STEP BY STEP")
print("="*70)

# Wait for server to start
print("\n[STEP 1] Waiting for server to be ready...")
time.sleep(3)

# Test 1: Can we reach the server?
print("\n[STEP 2] Testing if server is reachable...")
try:
    response = requests.get("http://127.0.0.1:5000/", timeout=5)
    print(f"✅ Server is reachable! Status: {response.status_code}")
except Exception as e:
    print(f"❌ Cannot reach server: {e}")
    exit(1)

# Test 2: Health check
print("\n[STEP 3] Testing health endpoint...")
try:
    response = requests.get("http://127.0.0.1:5000/api/health", timeout=5)
    health = response.json()
    print(f"✅ Health check passed!")
    print(f"   Response: {json.dumps(health, indent=2)}")
    if health.get('api_key') != 'configured':
        print("⚠️  WARNING: API key not configured!")
except Exception as e:
    print(f"❌ Health check failed: {e}")
    exit(1)

# Test 3: Test OPTIONS request (CORS preflight)
print("\n[STEP 4] Testing OPTIONS request (CORS preflight)...")
try:
    response = requests.options("http://127.0.0.1:5000/api/score", timeout=5)
    print(f"✅ OPTIONS request successful! Status: {response.status_code}")
    print(f"   CORS Headers: {dict(response.headers)}")
except Exception as e:
    print(f"❌ OPTIONS request failed: {e}")

# Test 4: Test POST to /api/score with minimal payload
print("\n[STEP 5] Testing POST to /api/score...")
print("   Sending: {\"url\": \"https://example.com\"}")
print("   Please wait 30-60 seconds for Gemini AI to respond...")

try:
    start_time = time.time()
    response = requests.post(
        "http://127.0.0.1:5000/api/score",
        json={"url": "https://example.com"},
        headers={
            "Content-Type": "application/json",
            "Origin": "http://localhost:5000"
        },
        timeout=120
    )
    elapsed = time.time() - start_time
    
    print(f"\n   Response received in {elapsed:.1f} seconds")
    print(f"   Status Code: {response.status_code}")
    print(f"   Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ SUCCESS! API is working!")
        print(f"\n   📊 Score: {result.get('score', 'N/A')}/100")
        print(f"   📋 Compliance: {result.get('compliance_level', 'N/A')}")
        
        # Show first 500 chars of response
        print(f"\n   Response Preview:")
        print(f"   {json.dumps(result, indent=2)[:500]}...")
        
        print("\n" + "="*70)
        print("✅ THE ACCESSIBILITY SCORE FEATURE IS WORKING!")
        print("="*70)
    else:
        print(f"\n❌ ERROR Response:")
        print(f"   {response.text[:1000]}")
        
        print("\n" + "="*70)
        print("❌ PROBLEM FOUND: Server returned error")
        print("="*70)
        
except requests.exceptions.Timeout:
    print(f"\n❌ Request timed out after 120 seconds")
    print("\n" + "="*70)
    print("❌ PROBLEM: Gemini API is too slow or not responding")
    print("="*70)
    
except requests.exceptions.ConnectionError as e:
    print(f"\n❌ Connection error: {e}")
    print("\n" + "="*70)
    print("❌ PROBLEM: Cannot connect to server")
    print("="*70)
    
except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    print(f"   Type: {type(e).__name__}")
    print("\n" + "="*70)
    print(f"❌ PROBLEM: {type(e).__name__} - {str(e)}")
    print("="*70)

print("\n[STEP 6] Checking server logs...")
print("Look at the terminal where server is running for any error messages")
