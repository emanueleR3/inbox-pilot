"""
Simple test script to verify Jerry API endpoints work correctly.
Run this after starting the API server.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8010"
USER_ID = "test_user_123"


def print_response(title, response):
    """Pretty print the response."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")


def test_get_tools():
    """Test getting available tools."""
    print("\n🧪 Test 1: Get Available Tools")
    response = requests.get(f"{BASE_URL}/chatbot/tools")
    print_response("Available Tools", response)
    return response.status_code == 200


def test_create_thread():
    """Test creating a new thread."""
    print("\n🧪 Test 2: Create New Thread")
    response = requests.post(
        f"{BASE_URL}/chatbot/thread/create",
        json={"user_id": USER_ID}
    )
    print_response("Create Thread", response)
    if response.status_code == 200:
        return response.json().get("thread_id")
    return None


def test_send_message(thread_id=None):
    """Test sending a message."""
    print("\n🧪 Test 3: Send Message")
    payload = {
        "user_id": USER_ID,
        "message": "Hello Jerry! Can you introduce yourself?"
    }
    if thread_id:
        payload["thread_id"] = thread_id
    
    response = requests.post(
        f"{BASE_URL}/chatbot/message",
        json=payload
    )
    print_response("Send Message", response)
    if response.status_code == 200:
        return response.json().get("thread_id")
    return None


def test_get_history(thread_id):
    """Test getting thread history."""
    print("\n🧪 Test 4: Get Thread History")
    response = requests.get(f"{BASE_URL}/chatbot/thread/{thread_id}/history")
    print_response("Thread History", response)
    return response.status_code == 200


def test_execute_tool():
    """Test executing a tool directly."""
    print("\n🧪 Test 5: Execute Tool (Send Email)")
    response = requests.post(
        f"{BASE_URL}/chatbot/tool/execute",
        json={
            "tool_name": "send_email",
            "tool_params": {
                "sender_address": "dev4@example.com",
                "receiver_address": "customer@example.com",
                "subject": "Test from Jerry API",
                "body": "This is a test email sent via the Jerry API tool execution endpoint.",
                "provider": "google"
            }
        }
    )
    print_response("Execute Tool", response)
    return response.status_code == 200


def test_delete_thread(thread_id):
    """Test deleting a thread."""
    print("\n🧪 Test 6: Delete Thread")
    response = requests.delete(f"{BASE_URL}/chatbot/thread/{thread_id}")
    print_response("Delete Thread", response)
    return response.status_code == 200


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("🚀 Starting Jerry API Tests")
    print("="*60)
    
    results = []
    
    # Test 1: Get tools
    results.append(("Get Tools", test_get_tools()))
    
    # Test 2: Create thread
    thread_id = test_create_thread()
    results.append(("Create Thread", thread_id is not None))
    
    if thread_id:
        # Test 3: Send message
        thread_id = test_send_message(thread_id)
        results.append(("Send Message", thread_id is not None))
        
        # Give the agent time to respond
        time.sleep(2)
        
        # Test 4: Get history
        if thread_id:
            results.append(("Get History", test_get_history(thread_id)))
        
        # Test 5: Execute tool
        results.append(("Execute Tool", test_execute_tool()))
        
        # Test 6: Delete thread
        if thread_id:
            results.append(("Delete Thread", test_delete_thread(thread_id)))
    
    # Print summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to the API server.")
        print("Make sure the server is running on http://localhost:8010")
        exit(1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        exit(1)
