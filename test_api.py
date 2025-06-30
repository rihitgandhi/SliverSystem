import requests
import json

def test_score_api():
    url = "http://127.0.0.1:5000/api/score"
    data = {"url": "https://example.com"}
    
    print("Testing API with data:", data)
    
    try:
        response = requests.post(url, json=data, headers={'Content-Type': 'application/json'})
        print("Response status:", response.status_code)
        print("Response headers:", response.headers)
        print("Response text:", response.text)
        
        if response.status_code == 200:
            result = response.json()
            print("Parsed JSON:", json.dumps(result, indent=2))
        else:
            print("Error response:", response.text)
            
    except Exception as e:
        print("Exception:", str(e))

if __name__ == "__main__":
    test_score_api() 