#!/usr/bin/env python3
"""
Example client for the Auto Call and Update API

This demonstrates how to interact with the FastAPI server to:
1. Start auto call workflows
2. Make quick calls
3. Monitor call status
"""

import requests
import time
import json

# API Configuration
API_BASE_URL = "http://localhost:8000"

def start_auto_call(client_id: str, policy_number: str, phone_number: str = None):
    """
    Start an auto call workflow
    """
    url = f"{API_BASE_URL}/call/auto"
    payload = {
        "client_id": client_id,
        "policy_number": policy_number
    }
    
    if phone_number:
        payload["phone_number"] = phone_number
    
    print(f"🚀 Starting auto call workflow...")
    print(f"   Client ID: {client_id}")
    print(f"   Policy: {policy_number}")
    if phone_number:
        print(f"   Phone: {phone_number}")
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        print(f"✅ Workflow started successfully!")
        print(f"   Session ID: {result['session_id']}")
        print(f"   Status: {result['status']}")
        
        return result['session_id']
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error starting workflow: {e}")
        return None

def make_quick_call(phone_number: str):
    """
    Make a quick call with just a phone number
    """
    url = f"{API_BASE_URL}/call/quick"
    payload = {"phone_number": phone_number}
    
    print(f"📞 Making quick call to: {phone_number}")
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        print(f"✅ Quick call started!")
        print(f"   Session ID: {result['session_id']}")
        print(f"   Status: {result['status']}")
        
        return result['session_id']
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error making quick call: {e}")
        return None

def get_call_status(session_id: str):
    """
    Get the current status of a call session
    """
    url = f"{API_BASE_URL}/call/status/{session_id}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        result = response.json()
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting status: {e}")
        return None

def monitor_call_progress(session_id: str, check_interval: int = 5, max_checks: int = 120):
    """
    Monitor call progress until completion or timeout
    """
    print(f"📡 Monitoring session: {session_id}")
    print(f"    Checking every {check_interval} seconds (max {max_checks} checks)")
    print("-" * 60)
    
    for i in range(max_checks):
        status_data = get_call_status(session_id)
        
        if not status_data:
            print("❌ Failed to get status, retrying...")
            time.sleep(check_interval)
            continue
        
        status = status_data.get("status", "unknown")
        progress = status_data.get("progress", "No progress info")
        timestamp = status_data.get("timestamp", "")
        
        print(f"[{i+1:3d}] {status.upper():12} | {progress}")
        
        # Check for completion
        if status in ["completed", "failed", "error", "timeout"]:
            print("-" * 60)
            if status == "completed":
                print("🎉 Call completed successfully!")
                if status_data.get("call_data"):
                    call_data = status_data["call_data"]
                    print(f"   Call Status: {call_data.get('status', 'unknown')}")
                    print(f"   End Reason: {call_data.get('endedReason', 'unknown')}")
                    if call_data.get('cost'):
                        print(f"   Cost: ${call_data.get('cost', 0):.4f}")
            else:
                print(f"❌ Call ended with status: {status}")
                if status_data.get("error"):
                    print(f"   Error: {status_data['error']}")
            return status_data
        
        time.sleep(check_interval)
    
    print("⏰ Monitoring timeout reached")
    return status_data

def check_api_health():
    """
    Check if the API server is running
    """
    url = f"{API_BASE_URL}/health"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        result = response.json()
        print(f"✅ API is healthy")
        print(f"   Status: {result['status']}")
        print(f"   Timestamp: {result['timestamp']}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ API health check failed: {e}")
        return False

def demo_auto_call():
    """
    Demo the auto call workflow
    """
    print("🧪 DEMO: Auto Call Workflow")
    print("=" * 50)
    
    # Example customer data (adjust as needed)
    client_id = "24765"
    policy_number = "BSNDP-2025-012160-01"
    
    # Start the workflow
    session_id = start_auto_call(client_id, policy_number)
    
    if session_id:
        print("\n📡 Monitoring progress...")
        monitor_call_progress(session_id)

def demo_quick_call():
    """
    Demo the quick call feature
    """
    print("🧪 DEMO: Quick Call")
    print("=" * 50)
    
    # Example phone number (adjust as needed)
    phone_number = "3239435582"
    
    # Make the call
    session_id = make_quick_call(phone_number)
    
    if session_id:
        print("\n📡 Monitoring progress...")
        monitor_call_progress(session_id)

def interactive_mode():
    """
    Interactive mode for testing the API
    """
    print("🔄 INTERACTIVE API CLIENT")
    print("=" * 50)
    
    while True:
        print("\nChoose an option:")
        print("1. Auto Call Workflow")
        print("2. Quick Call")
        print("3. Check Session Status")
        print("4. API Health Check")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == "1":
            print("\n--- Auto Call Workflow ---")
            client_id = input("Client ID: ").strip()
            policy_number = input("Policy Number: ").strip()
            phone_number = input("Phone Number (optional): ").strip() or None
            
            if client_id and policy_number:
                session_id = start_auto_call(client_id, policy_number, phone_number)
                if session_id:
                    monitor = input("Monitor progress? (y/n): ").strip().lower()
                    if monitor == 'y':
                        monitor_call_progress(session_id)
            else:
                print("❌ Client ID and Policy Number are required")
        
        elif choice == "2":
            print("\n--- Quick Call ---")
            phone_number = input("Phone Number: ").strip()
            
            if phone_number:
                session_id = make_quick_call(phone_number)
                if session_id:
                    monitor = input("Monitor progress? (y/n): ").strip().lower()
                    if monitor == 'y':
                        monitor_call_progress(session_id)
            else:
                print("❌ Phone number is required")
        
        elif choice == "3":
            print("\n--- Check Session Status ---")
            session_id = input("Session ID: ").strip()
            
            if session_id:
                status_data = get_call_status(session_id)
                if status_data:
                    print(f"\nSession Status:")
                    print(json.dumps(status_data, indent=2, default=str))
            else:
                print("❌ Session ID is required")
        
        elif choice == "4":
            print("\n--- API Health Check ---")
            check_api_health()
        
        elif choice == "5":
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice. Please enter 1-5.")
        
        print("\n" + "-" * 50)

if __name__ == "__main__":
    print("🤖 AUTO CALL API CLIENT")
    print("=" * 50)
    
    # Check API health first
    if not check_api_health():
        print("\n❌ API server is not available!")
        print("   Make sure to start the server with: python app.py")
        print("   Or: uvicorn app:app --reload")
        exit(1)
    
    print("\nAPI server is available!")
    print("\nAvailable demos:")
    print("1. Run demo_auto_call() - Test auto call workflow")
    print("2. Run demo_quick_call() - Test quick call")
    print("3. Run interactive_mode() - Interactive testing")
    
    # Uncomment to run demos:
    # demo_auto_call()
    # demo_quick_call()
    
    # Start interactive mode
    interactive_mode() 