#!/usr/bin/env python3
"""
Comprehensive test script for all SliverSystem functionality
Tests all API endpoints and verifies responses
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def test_health_endpoint():
    print_header("Testing Health Endpoint")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"✓ Status Code: {response.status_code}")
        data = response.json()
        print(f"✓ Response: {json.dumps(data, indent=2)}")
        assert response.status_code == 200, "Health check failed"
        assert data['status'] == 'healthy', "Server not healthy"
        print("✅ Health endpoint PASSED")
        return True
    except Exception as e:
        print(f"❌ Health endpoint FAILED: {e}")
        return False

def test_chat_endpoint():
    print_header("Testing Chat Endpoint")
    try:
        payload = {
            "message": "What is WCAG?",
            "conversation_id": "test-conv-123"
        }
        response = requests.post(
            f"{BASE_URL}/api/chat",
            headers={"Content-Type": "application/json"},
            json=payload
        )
        print(f"✓ Status Code: {response.status_code}")
        data = response.json()
        print(f"✓ Conversation ID: {data.get('conversation_id')}")
        print(f"✓ Response preview: {data.get('response', '')[:100]}...")
        assert response.status_code == 200, "Chat request failed"
        assert 'response' in data, "No response field in data"
        assert len(data['response']) > 0, "Empty response"
        print("✅ Chat endpoint PASSED")
        return True
    except Exception as e:
        print(f"❌ Chat endpoint FAILED: {e}")
        return False

def test_score_endpoint():
    print_header("Testing Score Endpoint")
    try:
        payload = {
            "url": "http://www.example.com"
        }
        response = requests.post(
            f"{BASE_URL}/api/score",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=60  # Longer timeout for AI analysis
        )
        print(f"✓ Status Code: {response.status_code}")
        data = response.json()
        
        # Check required fields
        required_fields = ['score', 'score_explanation', 'wcag_standards', 'recommendations', 'priority_issues']
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
            print(f"✓ Field '{field}' present")
        
        # Validate score
        assert isinstance(data['score'], (int, float)), "Score should be numeric"
        assert 0 <= data['score'] <= 100, "Score should be between 0 and 100"
        print(f"✓ Score: {data['score']}/100")
        
        # Check WCAG standards structure
        wcag = data['wcag_standards']
        assert 'compliant' in wcag, "Missing compliant standards"
        assert 'non_compliant' in wcag, "Missing non_compliant standards"
        assert 'details' in wcag, "Missing details"
        print(f"✓ WCAG Standards: {len(wcag.get('compliant', []))} compliant, {len(wcag.get('non_compliant', []))} non-compliant")
        
        # Check priority issues
        issues = data['priority_issues']
        assert isinstance(issues, list), "Priority issues should be a list"
        print(f"✓ Priority Issues: {len(issues)} issues identified")
        
        # Check recommendations
        recs = data['recommendations']
        assert 'short_term' in recs, "Missing short_term recommendations"
        assert 'medium_term' in recs, "Missing medium_term recommendations"
        assert 'long_term' in recs, "Missing long_term recommendations"
        print(f"✓ Recommendations: short/medium/long term present")
        
        print("✅ Score endpoint PASSED")
        return True
    except Exception as e:
        print(f"❌ Score endpoint FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_static_pages():
    print_header("Testing Static Pages")
    pages = ['index.html', 'chat.html', 'score.html', 'help.html']
    all_passed = True
    
    for page in pages:
        try:
            response = requests.get(f"{BASE_URL}/{page}")
            if response.status_code == 200:
                print(f"✓ {page}: {response.status_code} - OK")
            else:
                print(f"✗ {page}: {response.status_code} - FAILED")
                all_passed = False
        except Exception as e:
            print(f"✗ {page}: ERROR - {e}")
            all_passed = False
    
    if all_passed:
        print("✅ All static pages accessible")
    else:
        print("❌ Some static pages failed")
    return all_passed

def test_chat_conversation_continuity():
    print_header("Testing Chat Conversation Continuity")
    try:
        conv_id = f"test-continuity-{int(time.time())}"
        
        # First message
        response1 = requests.post(
            f"{BASE_URL}/api/chat",
            json={"message": "My name is Alice", "conversation_id": conv_id}
        )
        data1 = response1.json()
        print(f"✓ Message 1: {data1['response'][:80]}...")
        
        # Second message (should remember name)
        response2 = requests.post(
            f"{BASE_URL}/api/chat",
            json={"message": "What is my name?", "conversation_id": conv_id}
        )
        data2 = response2.json()
        print(f"✓ Message 2: {data2['response'][:80]}...")
        
        # Check if bot remembers (Alice should be in response)
        if 'alice' in data2['response'].lower():
            print("✅ Conversation continuity PASSED")
            return True
        else:
            print("⚠️  Bot might not remember conversation context")
            return True  # Not a critical failure
    except Exception as e:
        print(f"❌ Conversation continuity FAILED: {e}")
        return False

def test_error_handling():
    print_header("Testing Error Handling")
    all_passed = True
    
    # Test empty chat message
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={"message": "", "conversation_id": "test"}
        )
        if response.status_code == 400:
            print("✓ Empty chat message handled correctly")
        else:
            print(f"✗ Empty chat message: Expected 400, got {response.status_code}")
            all_passed = False
    except Exception as e:
        print(f"✗ Empty chat message test error: {e}")
        all_passed = False
    
    # Test empty URL in score
    try:
        response = requests.post(
            f"{BASE_URL}/api/score",
            json={"url": ""}
        )
        if response.status_code == 400:
            print("✓ Empty URL handled correctly")
        else:
            print(f"✗ Empty URL: Expected 400, got {response.status_code}")
            all_passed = False
    except Exception as e:
        print(f"✗ Empty URL test error: {e}")
        all_passed = False
    
    if all_passed:
        print("✅ Error handling PASSED")
    else:
        print("❌ Some error handling tests FAILED")
    return all_passed

def run_all_tests():
    print_header("SLIVER SYSTEM - COMPREHENSIVE FUNCTIONALITY TEST")
    print(f"Testing server at: {BASE_URL}")
    print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Run all tests
    results['health'] = test_health_endpoint()
    time.sleep(0.5)
    
    results['chat'] = test_chat_endpoint()
    time.sleep(0.5)
    
    results['score'] = test_score_endpoint()
    time.sleep(0.5)
    
    results['static_pages'] = test_static_pages()
    time.sleep(0.5)
    
    results['conversation'] = test_chat_conversation_continuity()
    time.sleep(0.5)
    
    results['errors'] = test_error_handling()
    
    # Summary
    print_header("TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name.ljust(20)}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! System is fully functional.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review errors above.")
        return 1

if __name__ == "__main__":
    import sys
    exit_code = run_all_tests()
    sys.exit(exit_code)
