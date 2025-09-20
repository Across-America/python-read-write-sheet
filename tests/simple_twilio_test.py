#!/usr/bin/env python3
"""
Simple Twilio test - minimal configuration
"""
import requests

def simple_test():
    print("🔧 SIMPLE TWILIO TEST")
    print("=" * 30)
    
    # Basic configuration
    VAPI_API_KEY = "763666f4-1d39-46f5-9539-0b052ddb8495"
    ASSISTANT_ID = "8e07049e-f7c8-4e5d-a893-8c33a318490d"
    
    # Test with your own phone number first
    test_number = input("Enter YOUR phone number for testing (e.g., 1234567890): ").strip()
    
    if not test_number:
        print("❌ No number provided")
        return
    
    # Format number
    if not test_number.startswith('+'):
        test_number = f"+1{test_number}"
    
    print(f"Testing with: {test_number}")
    
    # Try all phone numbers
    phone_ids = [
        ("VAPI Original", "2f8d40fa-32c8-421b-8c70-ec877e4e9948"),
        ("VAPI New", "03c87616-5adf-4e83-ab40-9d921882f2d4"),
        ("Twilio", "29e32cd8-432f-4205-85bd-c001154b94a2")
    ]
    
    for name, phone_id in phone_ids:
        print(f"\n🧪 Testing {name}...")
        
        payload = {
            "assistantId": ASSISTANT_ID,
            "customers": [{"number": test_number}],
            "phoneNumberId": phone_id
        }
        
        try:
            response = requests.post(
                "https://api.vapi.ai/call",
                headers={
                    "Authorization": f"Bearer {VAPI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=5
            )
            
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"  ✅ {name} WORKS!")
                result = response.json()
                print(f"  Call ID: {result.get('id', 'Unknown')}")
                break
            else:
                print(f"  ❌ {name} failed: {response.text[:100]}...")
                
        except Exception as e:
            print(f"  ❌ {name} error: {e}")
    
    print("\n💡 Recommendation:")
    print("If VAPI numbers work, use them for now.")
    print("If Twilio works, great! You can make unlimited calls.")
    print("If nothing works, wait for VAPI limits to reset tomorrow.")

if __name__ == "__main__":
    simple_test()
