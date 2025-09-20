#!/usr/bin/env python3
"""
Help verify the phone number +16262387555 in Twilio
"""
import requests

def verify_phone_number():
    """
    Instructions for verifying phone number in Twilio
    """
    print("📞 PHONE NUMBER VERIFICATION GUIDE")
    print("=" * 50)
    
    target_number = "+16262387555"
    print(f"Target number to verify: {target_number}")
    print()
    
    print("🔧 Steps to verify in Twilio Console:")
    print("1. Login to Twilio Console: https://console.twilio.com")
    print("2. Go to Phone Numbers > Manage > Verified Caller IDs")
    print("3. Click 'Add a new number'")
    print(f"4. Enter: {target_number}")
    print("5. Choose verification method:")
    print("   - SMS: Send verification code to the number")
    print("   - Voice: Call the number with verification code")
    print("6. Complete the verification process")
    print()
    
    print("⚠️  Important Notes:")
    print("- You need access to the phone number to receive the verification code")
    print("- If this is a customer's number, you may need to ask them to verify")
    print("- Or use your own number for testing first")
    print()
    
    print("🧪 Alternative: Test with your own verified number")
    print("If you have your own phone number verified in Twilio,")
    print("we can test the system with that number first.")
    
    # Ask for verified number
    verified_number = input("\nEnter a verified phone number for testing (or press Enter to skip): ").strip()
    
    if verified_number:
        if not verified_number.startswith('+'):
            verified_number = f"+1{verified_number}"
        
        print(f"\n🧪 Testing with verified number: {verified_number}")
        test_call(verified_number)

def test_call(phone_number):
    """
    Test a call with the verified number
    """
    VAPI_API_KEY = "763666f4-1d39-46f5-9539-0b052ddb8495"
    ASSISTANT_ID = "8e07049e-f7c8-4e5d-a893-8c33a318490d"
    TWILIO_PHONE_ID = "29e32cd8-432f-4205-85bd-c001154b94a2"
    
    payload = {
        "assistantId": ASSISTANT_ID,
        "customers": [{"number": phone_number}],
        "phoneNumberId": TWILIO_PHONE_ID
    }
    
    try:
        response = requests.post(
            "https://api.vapi.ai/call",
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS! Twilio call initiated!")
            print(f"Call ID: {result.get('id', 'Unknown')}")
            print("🎉 Twilio is working! You can now make unlimited calls!")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    verify_phone_number()
