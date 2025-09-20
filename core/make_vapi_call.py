# Make VAPI calls using phone numbers from Cancellations Dev sheet
import requests
import os
from dotenv import load_dotenv
from ..tools.read_cancellation_dev import search_phone_number, find_phone_by_client_policy
import smartsheet

# Load environment variables
load_dotenv()

# VAPI Configuration
VAPI_API_KEY = "763666f4-1d39-46f5-9539-0b052ddb8495"
ASSISTANT_ID = "8e07049e-f7c8-4e5d-a893-8c33a318490d"

# Multiple phone numbers for load balancing
PHONE_NUMBER_IDS = [
    "2f8d40fa-32c8-421b-8c70-ec877e4e9948",  # Original number: +16264602769
    "03c87616-5adf-4e83-ab40-9d921882f2d4",  # New number: +16265219363 (626-521-9363)
]

# Track which phone number to use next
current_phone_index = 0

def get_next_phone_number_id():
    """
    Get the next phone number ID for load balancing
    Returns the next available phone number ID
    """
    global current_phone_index
    
    if not PHONE_NUMBER_IDS:
        raise Exception("No phone numbers configured!")
    
    phone_id = PHONE_NUMBER_IDS[current_phone_index]
    current_phone_index = (current_phone_index + 1) % len(PHONE_NUMBER_IDS)
    
    print(f"📞 Using phone number {current_phone_index + 1}/{len(PHONE_NUMBER_IDS)}")
    return phone_id

def make_vapi_call(phone_number, customer_info=None):
    """
    Make a VAPI call to the specified phone number with personalized greeting
    
    Args:
        phone_number (str): Phone number to call
        customer_info (dict): Optional customer information for context
    
    Returns:
        dict: VAPI response
    """
    # Format phone number to E.164 format
    if not phone_number.startswith('+'):
        if len(phone_number) == 10:
            formatted_phone = f"+1{phone_number}"
        elif len(phone_number) == 11 and phone_number.startswith('1'):
            formatted_phone = f"+{phone_number}"
        else:
            formatted_phone = f"+1{phone_number}"
    else:
        formatted_phone = phone_number
    
    url = "https://api.vapi.ai/call"
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Get next available phone number
    phone_number_id = get_next_phone_number_id()
    
    payload = {
        "assistantId": ASSISTANT_ID,
        "customers": [
            {
                "number": formatted_phone
            }
        ],
        "phoneNumberId": phone_number_id
    }
    
    # Add customer context if available
    if customer_info:
        # Extract customer name for personalized greeting
        customer_name = customer_info.get("insured", "")
        agent_name = customer_info.get("agent_name", "")
        office = customer_info.get("office", "")
        policy_number = customer_info.get("policy_number", "")
        phone_number = customer_info.get("phone_number", formatted_phone)
        
        # Add only basic customer information that VAPI supports
        payload["customers"][0]["name"] = customer_name
        
        # Note: VAPI variables might need to be configured in the dashboard
        # The assistant should be configured with these variables in VAPI dashboard
        # and they should be accessible via {{customer.name}} in the template
    
    try:
        print(f"📞 Making VAPI call to: {formatted_phone}")
        if customer_info:
            print(f"👤 Customer: {customer_info.get('insured', 'Unknown')}")
            print(f"📋 Policy: {customer_info.get('policy_number', 'Unknown')}")
            print(f"🏢 Office: {customer_info.get('office', 'Unknown')}")
            print(f"👨‍💼 Agent: {customer_info.get('agent_name', 'Unknown')}")
            print(f"💬 Personalized greeting will use customer name: {customer_info.get('insured', 'Unknown')}")
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"✅ Call initiated successfully!")
            
            # Handle different response formats
            if 'results' in result and len(result['results']) > 0:
                call_data = result['results'][0]
                call_id = call_data.get('id', 'Unknown')
                status = call_data.get('status', 'Unknown')
                print(f"📞 Call ID: {call_id}")
                print(f"📊 Status: {status}")
                print(f"👤 Customer: {call_data.get('customer', {}).get('name', 'Unknown')}")
                print(f"📱 Phone: {call_data.get('customer', {}).get('number', 'Unknown')}")
            else:
                call_id = result.get('id', 'Unknown')
                print(f"📞 Call ID: {call_id}")
            
            return result
        else:
            print(f"❌ Call failed with status code: {response.status_code}")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error making VAPI call: {e}")
        return None

def call_by_client_policy(client_id, policy_number):
    """
    Find phone number by Client ID and Policy Number, then make VAPI call
    
    Args:
        client_id (str): Client ID to search for
        policy_number (str): Policy Number to search for
    
    Returns:
        dict: VAPI call result
    """
    print(f"🔍 Searching for Client ID: {client_id}, Policy: {policy_number}")
    
    try:
        # Get Smartsheet connection
        token = os.getenv('SMARTSHEET_ACCESS_TOKEN', 'xr7pjb35y9FyLBJ1KoPXyTQ91W4kD7UQH9kFO')
        smart = smartsheet.Smartsheet(access_token=token)
        smart.errors_as_exceptions(True)
        
        # Get the sheet
        sheet = smart.Sheets.get_sheet(5146141873098628)  # Cancellations Dev sheet ID
        
        # Search for the record
        result = find_phone_by_client_policy(sheet, client_id, policy_number)
        
        if result["found"]:
            phone_number = result['phone_number']
            
            print(f"\n🎯 Customer Found!")
            print(f"📞 Phone Number: {phone_number}")
            print(f"👤 Client ID: {result['client_id']}")
            print(f"📋 Policy Number: {result['policy_number']}")
            print(f"🏠 Insured: {result.get('insured', 'N/A')}")
            print(f"🏢 Office: {result.get('office', 'N/A')}")
            print(f"👨‍💼 Agent: {result.get('agent_name', 'N/A')}")
            
            # Check if phone number is valid
            if phone_number and phone_number != "No phone number":
                print(f"\n📞 Initiating VAPI call...")
                return make_vapi_call(phone_number, result)
            else:
                print(f"❌ No valid phone number found for this customer")
                return None
        else:
            print(f"\n❌ {result['error']}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def call_by_phone_number(phone_number):
    """
    Make VAPI call directly to a phone number
    
    Args:
        phone_number (str): Phone number to call
    
    Returns:
        dict: VAPI call result
    """
    return make_vapi_call(phone_number)

def interactive_call_mode():
    """
    Interactive mode for making calls
    """
    print(f"\n" + "="*60)
    print("📞 INTERACTIVE VAPI CALL MODE")
    print("="*60)
    print("Choose an option:")
    print("1. Call by Client ID + Policy Number")
    print("2. Call by Phone Number directly")
    print("3. Quit")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-3): ").strip()
            
            if choice == "1":
                print("\n🔍 Search and Call by Client ID + Policy Number:")
                client_id = input("Client ID: ").strip()
                policy_number = input("Policy Number: ").strip()
                
                if client_id and policy_number:
                    call_by_client_policy(client_id, policy_number)
                else:
                    print("❌ Please provide both Client ID and Policy Number")
                    
            elif choice == "2":
                print("\n📞 Direct Call by Phone Number:")
                phone_number = input("Phone Number: ").strip()
                
                if phone_number:
                    call_by_phone_number(phone_number)
                else:
                    print("❌ Please provide a phone number")
                    
            elif choice == "3":
                print("👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3")
                
            print("\n" + "-"*40)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            continue

# Example usage and testing
if __name__ == "__main__":
    print("📞 VAPI CALL SYSTEM")
    print("="*50)
    print("This script can make calls using VAPI API")
    print("It integrates with Cancellations Dev sheet to find phone numbers")
    print()
    
    # Test with known data
    print("🧪 QUICK TEST:")
    print("Testing with known customer: Client ID 24765, Policy BSNDP-2025-012160-01")
    
    # Uncomment the line below to make an actual test call
    # call_by_client_policy("24765", "BSNDP-2025-012160-01")
    
    print("\n💡 To make actual calls, uncomment the test line above or run interactive mode")
    
    # Start interactive mode
    interactive_call_mode()
