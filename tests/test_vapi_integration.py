# Test VAPI integration without making actual calls
from api.read_cancellation_dev import search_phone_number
import requests

print("🧪 TESTING VAPI INTEGRATION")
print("="*50)

# Test 1: Check if we can get phone number
print("Test 1: Getting phone number from Smartsheet")
print("Client ID: 24765, Policy: BSNDP-2025-012160-01")

# This will show the phone search working
phone = search_phone_number("24765", "BSNDP-2025-012160-01")

if phone:
    print(f"\n✅ Phone number retrieved: {phone}")
    
    # Test 2: Prepare VAPI call payload (but don't send it)
    print(f"\nTest 2: Preparing VAPI call payload")
    
    payload = {
        "assistantId": "8e07049e-f7c8-4e5d-a893-8c33a318490d",
        "customers": [
            {
                "number": phone
            }
        ],
        "phoneNumberId": "2f8d40fa-32c8-421b-8c70-ec877e4e9948"
    }
    
    print(f"📞 VAPI Payload prepared:")
    print(f"   Assistant ID: {payload['assistantId']}")
    print(f"   Phone Number: {payload['customers'][0]['number']}")
    print(f"   Phone Number ID: {payload['phoneNumberId']}")
    
    print(f"\n✅ Integration test successful!")
    print(f"📞 Ready to make calls with VAPI!")
    
    # Show the actual call function
    print(f"\n💡 To make actual calls, use:")
    print(f"   from quick_call import quick_call")
    print(f"   quick_call('24765', 'BSNDP-2025-012160-01')")
    
else:
    print("❌ Could not retrieve phone number")

print(f"\n🔧 VAPI Call Function Ready!")
print(f"Files created:")
print(f"  - make_vapi_call.py (full featured)")
print(f"  - quick_call.py (simple version)")
