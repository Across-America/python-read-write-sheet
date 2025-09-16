# Quick VAPI call script - simplified version
import requests
from read_cancellation_dev import search_phone_number

# VAPI Configuration
VAPI_API_KEY = "763666f4-1d39-46f5-9539-0b052ddb8495"
ASSISTANT_ID = "8e07049e-f7c8-4e5d-a893-8c33a318490d"
PHONE_NUMBER_ID = "2f8d40fa-32c8-421b-8c70-ec877e4e9948"

def quick_call(client_id, policy_number):
    """
    Quick function: Find phone number and make VAPI call
    
    Args:
        client_id (str): Client ID
        policy_number (str): Policy Number
    
    Returns:
        dict: Call result
    """
    print(f"🔍 Looking up: Client {client_id}, Policy {policy_number}")
    
    # First, get the phone number using your existing function
    phone = search_phone_number(client_id, policy_number)
    
    if not phone:
        print("❌ Cannot make call - no phone number found")
        return None
    
    # Format phone number to E.164 format (add +1 for US numbers)
    if not phone.startswith('+'):
        if len(phone) == 10:
            formatted_phone = f"+1{phone}"
        elif len(phone) == 11 and phone.startswith('1'):
            formatted_phone = f"+{phone}"
        else:
            formatted_phone = f"+1{phone}"
    else:
        formatted_phone = phone
    
    # Make the VAPI call
    print(f"\n📞 Making VAPI call to: {formatted_phone}")
    
    response = requests.post(
        "https://api.vapi.ai/call",
        headers={
            "Authorization": f"Bearer {VAPI_API_KEY}"
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
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Call initiated! Call ID: {result.get('id', 'Unknown')}")
        return result
    else:
        print(f"❌ Call failed: {response.status_code} - {response.text}")
        return None

# Example usage
if __name__ == "__main__":
    print("📞 QUICK VAPI CALL SYSTEM")
    print("="*40)
    
    # Example call (uncomment to test)
    # quick_call("24765", "BSNDP-2025-012160-01")
    
    # Interactive mode
    while True:
        try:
            print("\nEnter call details (or 'quit' to exit):")
            client_id = input("Client ID: ").strip()
            
            if client_id.lower() == 'quit':
                break
                
            policy_number = input("Policy Number: ").strip()
            
            if client_id and policy_number:
                quick_call(client_id, policy_number)
            else:
                print("❌ Please provide both Client ID and Policy Number")
                
            print("\n" + "-"*40)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
