import requests
import json

def test_score_endpoint():
    url = "http://127.0.0.1:5000/api/score"
    test_url = "https://example.com"
    
    print("=" * 60)
    print("Testing /api/score endpoint")
    print("=" * 60)
    
    data = {"url": test_url}
    
    print(f"\nSending POST request to: {url}")
    print(f"Request data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(
            url, 
            json=data, 
            headers={'Content-Type': 'application/json'},
            timeout=120  # 2 minute timeout for AI processing
        )
        
        print(f"\nResponse Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ SUCCESS!")
            print(f"\nScore: {result.get('score', 'N/A')}/100")
            print(f"Compliance Level: {result.get('compliance_level', 'N/A')}")
            
            if 'wcag_standards' in result:
                wcag = result['wcag_standards']
                print(f"\nCompliant Standards: {len(wcag.get('compliant', []))}")
                print(f"Non-Compliant Standards: {len(wcag.get('non_compliant', []))}")
            
            print("\nFull Response:")
            print(json.dumps(result, indent=2))
        else:
            print(f"\n❌ ERROR!")
            print(f"Response Text: {response.text}")
            
    except requests.exceptions.Timeout:
        print("\n❌ ERROR: Request timed out (>120 seconds)")
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to server")
        print("Make sure the Flask app is running on http://127.0.0.1:5000")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print(f"Error Type: {type(e).__name__}")

if __name__ == "__main__":
    test_score_endpoint()
