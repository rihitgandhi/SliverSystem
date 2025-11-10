import time
import requests
import json

print("Waiting for server to be ready...")
time.sleep(2)

print("\n" + "="*60)
print("Testing Website Accessibility Score Endpoint")
print("="*60)

try:
    # Test the health endpoint first
    print("\n1. Testing health endpoint...")
    health_response = requests.get("http://127.0.0.1:5000/api/health", timeout=5)
    print(f"   Status: {health_response.status_code}")
    print(f"   Response: {health_response.json()}")
    
    if health_response.status_code == 200:
        print("   ✅ Health check passed!")
    
    # Test the score endpoint
    print("\n2. Testing /api/score endpoint...")
    print("   Sending request to analyze: https://example.com")
    print("   (This may take 30-60 seconds...)")
    
    score_response = requests.post(
        "http://127.0.0.1:5000/api/score",
        json={"url": "https://example.com"},
        headers={"Content-Type": "application/json"},
        timeout=120
    )
    
    print(f"\n   Status Code: {score_response.status_code}")
    
    if score_response.status_code == 200:
        result = score_response.json()
        print("   ✅ SUCCESS!")
        print(f"\n   📊 Accessibility Score: {result.get('score', 'N/A')}/100")
        print(f"   📋 Compliance Level: {result.get('compliance_level', 'N/A')}")
        
        if 'wcag_standards' in result:
            wcag = result['wcag_standards']
            print(f"\n   WCAG Standards:")
            print(f"   - Compliant: {len(wcag.get('compliant', []))} standards")
            print(f"   - Non-Compliant: {len(wcag.get('non_compliant', []))} standards")
        
        if 'priority_issues' in result:
            print(f"\n   Priority Issues: {len(result['priority_issues'])} found")
        
        print("\n   🎉 The accessibility score feature is WORKING!")
        
    else:
        print(f"   ❌ ERROR: Status {score_response.status_code}")
        print(f"   Response: {score_response.text[:500]}")
        
except requests.exceptions.Timeout:
    print("\n   ❌ Request timed out after 120 seconds")
    print("   The Gemini API might be taking too long to respond")
except requests.exceptions.ConnectionError:
    print("\n   ❌ Could not connect to server")
    print("   Make sure the server is running on http://127.0.0.1:5000")
except Exception as e:
    print(f"\n   ❌ ERROR: {str(e)}")
    print(f"   Type: {type(e).__name__}")

print("\n" + "="*60)
