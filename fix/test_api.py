"""
test_api.py - Quick API Test Script

Tests the orchestrator integration endpoints.
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_health():
    """Test health endpoint."""
    print("\n" + "="*80)
    print("Testing Health Endpoint")
    print("="*80)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_device_status():
    """Test device status."""
    print("\n" + "="*80)
    print("Testing Device Status")
    print("="*80)
    
    try:
        response = requests.get(f"{BASE_URL}/api/device")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_agent_status():
    """Test agent status."""
    print("\n" + "="*80)
    print("Testing Agent Status")
    print("="*80)
    
    try:
        response = requests.get(f"{BASE_URL}/api/status")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_run_test():
    """Test running a test case."""
    print("\n" + "="*80)
    print("Testing Test Execution (Mock Mode)")
    print("="*80)
    
    try:
        payload = {
            "test_ids": ["TEST-001"],
            "use_learned": True,
            "max_retries": 3
        }
        
        print(f"Request: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            f"{BASE_URL}/api/run-tests",
            json=payload
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_standalone_command():
    """Test standalone command execution."""
    print("\n" + "="*80)
    print("Testing Standalone Command")
    print("="*80)
    
    try:
        payload = {
            "command": "Open Settings and enable Bluetooth"
        }
        
        print(f"Request: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            f"{BASE_URL}/api/execute-command",
            json=payload
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_send_guidance():
    """Test HITL guidance."""
    print("\n" + "="*80)
    print("Testing HITL Guidance")
    print("="*80)
    
    try:
        payload = {
            "guidance": "Tap the Settings icon",
            "coordinates": [850, 450],  # List (converted to tuple by Pydantic)
            "action_type": "tap"
        }
        
        print(f"Request: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            f"{BASE_URL}/api/send-guidance",
            json=payload
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_stop():
    """Test stop execution."""
    print("\n" + "="*80)
    print("Testing Stop")
    print("="*80)
    
    try:
        response = requests.post(f"{BASE_URL}/api/stop")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("="*80)
    print("AI AGENT FRAMEWORK - API TEST SUITE")
    print("="*80)
    print(f"Target: {BASE_URL}")
    print("="*80)
    
    tests = [
        ("Health Check", test_health),
        ("Device Status", test_device_status),
        ("Agent Status", test_agent_status),
        ("Run Test", test_run_test),
        ("Standalone Command", test_standalone_command),
        ("HITL Guidance", test_send_guidance),
        ("Stop Execution", test_stop),
    ]
    
    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print("="*80)
    print(f"Results: {passed}/{total} tests passed")
    print("="*80)


if __name__ == "__main__":
    main()