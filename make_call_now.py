# Direct call script - make the call now!
import requests
import os
from dotenv import load_dotenv
import smartsheet

# Load environment variables
load_dotenv()

# VAPI Configuration
VAPI_API_KEY = "763666f4-1d39-46f5-9539-0b052ddb8495"
ASSISTANT_ID = "8e07049e-f7c8-4e5d-a893-8c33a318490d"
PHONE_NUMBER_ID = "2f8d40fa-32c8-421b-8c70-ec877e4e9948"

def make_call_direct():
    """Make a direct call to the known customer"""
    
    print("📞 MAKING VAPI CALL NOW!")
    print("="*40)
    
    # Known customer data
    client_id = "24765"
    policy_number = "BSNDP-2025-012160-01"
    phone = "3239435582"
    
    print(f"👤 Customer: SHAO MING")
    print(f"📋 Client ID: {client_id}")
    print(f"📋 Policy: {policy_number}")
    print(f"📞 Phone: {phone}")
    
    # Format phone to E.164
    formatted_phone = f"+1{phone}"
    print(f"📞 Formatted Phone: {formatted_phone}")
    
    # Make the VAPI call
    print(f"\n🚀 Initiating VAPI call...")
    
    try:
        response = requests.post(
            "https://api.vapi.ai/call",
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "assistantId": ASSISTANT_ID,
                "customers": [
                    {
                        "number": formatted_phone
                    }
                ],
                "phoneNumberId": PHONE_NUMBER_ID
            }
        )
        
        print(f"📡 Response Status: {response.status_code}")
        
        if 200 <= response.status_code < 300:  # Check for any 2xx success status
            result = response.json()
            print(f"✅ CALL INITIATED SUCCESSFULLY!")
            print(f"📞 Call ID: {result.get('id', 'Unknown')}")
            print(f"📊 Full Response: {result}")
            return result
        else:
            print(f"❌ Call failed with status: {response.status_code}")
            print(f"📄 Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error making call: {e}")
        return None

if __name__ == "__main__":
    make_call_direct()
