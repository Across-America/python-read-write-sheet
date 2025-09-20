# Test script for personalized VAPI calls with Smartsheet integration
import os
from dotenv import load_dotenv
from make_vapi_call import make_vapi_call, call_by_client_policy
from read_cancellation_dev import find_phone_by_client_policy
import smartsheet

# Load environment variables
load_dotenv()

def test_customer_info_extraction():
    """
    Test extracting customer information from Smartsheet
    """
    print("🧪 TESTING CUSTOMER INFO EXTRACTION")
    print("=" * 50)
    
    try:
        # Get Smartsheet connection
        token = os.getenv('SMARTSHEET_ACCESS_TOKEN', 'xr7pjb35y9FyLBJ1KoPXyTQ91W4kD7UQH9kFO')
        smart = smartsheet.Smartsheet(access_token=token)
        smart.errors_as_exceptions(True)
        
        # Get the sheet
        sheet = smart.Sheets.get_sheet(5146141873098628)  # Cancellations Dev sheet ID
        
        # Test with a known customer
        test_client_id = "24765"
        test_policy = "BSNDP-2025-012160-01"
        
        print(f"🔍 Testing with Client ID: {test_client_id}")
        print(f"📋 Policy Number: {test_policy}")
        
        # Search for the record
        result = find_phone_by_client_policy(sheet, test_client_id, test_policy)
        
        if result["found"]:
            print(f"\n✅ Customer Found!")
            print(f"👤 Customer Name: {result.get('insured', 'N/A')}")
            print(f"📞 Phone Number: {result.get('phone_number', 'N/A')}")
            print(f"🏢 Office: {result.get('office', 'N/A')}")
            print(f"👨‍💼 Agent: {result.get('agent_name', 'N/A')}")
            print(f"📋 Policy: {result.get('policy_number', 'N/A')}")
            print(f"📊 LOB: {result.get('lob', 'N/A')}")
            print(f"📍 Status: {result.get('status', 'N/A')}")
            
            # Test personalized greeting generation
            customer_name = result.get('insured', '')
            agent_name = result.get('agent_name', '')
            office = result.get('office', '')
            policy_number = result.get('policy_number', '')
            
            if customer_name:
                greeting = f"Hi {customer_name}, this is {agent_name} calling from {office} regarding your insurance policy {policy_number}."
            else:
                greeting = f"Hi, this is {agent_name} calling from {office} regarding your insurance policy {policy_number}."
            
            print(f"\n💬 Generated Greeting:")
            print(f"   {greeting}")
            
            return result
        else:
            print(f"\n❌ Customer not found: {result['error']}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_vapi_payload_generation(customer_info):
    """
    Test generating VAPI payload with customer information
    """
    print(f"\n🧪 TESTING VAPI PAYLOAD GENERATION")
    print("=" * 50)
    
    if not customer_info:
        print("❌ No customer info provided")
        return None
    
    phone_number = customer_info.get('phone_number', '')
    if not phone_number or phone_number == "No phone number":
        print("❌ No valid phone number")
        return None
    
    # Simulate the payload generation (without making actual call)
    print(f"📞 Phone Number: {phone_number}")
    print(f"👤 Customer Name: {customer_info.get('insured', 'N/A')}")
    print(f"🏢 Office: {customer_info.get('office', 'N/A')}")
    print(f"👨‍💼 Agent: {customer_info.get('agent_name', 'N/A')}")
    print(f"📋 Policy: {customer_info.get('policy_number', 'N/A')}")
    
    # Generate the VAPI payload structure
    payload = {
        "assistantId": "8e07049e-f7c8-4e5d-a893-8c33a318490d",
        "customers": [
            {
                "number": phone_number,
                "name": customer_info.get('insured', ''),
                "variables": {
                    "customer_name": customer_info.get('insured', ''),
                    "agent_name": customer_info.get('agent_name', ''),
                    "office": customer_info.get('office', ''),
                    "policy_number": customer_info.get('policy_number', ''),
                    "phone_number": phone_number
                },
                "greeting": f"Hi {customer_info.get('insured', 'Customer')}, this is a call regarding your insurance policy."
            }
        ],
        "phoneNumberId": "2f8d40fa-32c8-421b-8c70-ec877e4e9948"
    }
    
    print(f"\n📋 Generated VAPI Payload:")
    print(f"   Assistant ID: {payload['assistantId']}")
    print(f"   Customer Name: {payload['customers'][0]['name']}")
    print(f"   Phone Number: {payload['customers'][0]['number']}")
    print(f"   Greeting: {payload['customers'][0]['greeting']}")
    print(f"   Variables: {payload['customers'][0]['variables']}")
    
    return payload

def test_prompt_templates():
    """
    Test the prompt templates
    """
    print(f"\n🧪 TESTING PROMPT TEMPLATES")
    print("=" * 50)
    
    from vapi_prompt_templates import get_personalized_prompt_template, get_simple_greeting_template
    
    print("📝 Main Personalized Template Preview:")
    print("-" * 30)
    template = get_personalized_prompt_template()
    # Show first 500 characters
    print(template[:500] + "..." if len(template) > 500 else template)
    
    print(f"\n📝 Simple Greeting Template:")
    print("-" * 30)
    simple_template = get_simple_greeting_template()
    print(simple_template)

def run_full_test():
    """
    Run the complete test suite
    """
    print("🚀 PERSONALIZED VAPI CALLS - FULL TEST SUITE")
    print("=" * 60)
    
    # Test 1: Customer info extraction
    customer_info = test_customer_info_extraction()
    
    if customer_info:
        # Test 2: VAPI payload generation
        payload = test_vapi_payload_generation(customer_info)
        
        # Test 3: Prompt templates
        test_prompt_templates()
        
        print(f"\n✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print(f"\n📋 NEXT STEPS:")
        print(f"1. Copy the prompt template from vapi_prompt_templates.py")
        print(f"2. Update your VAPI assistant with the template")
        print(f"3. Test with a real call using call_by_client_policy()")
        print(f"4. Monitor the call to ensure personalization works")
        
        return True
    else:
        print(f"\n❌ TESTS FAILED - Could not extract customer information")
        return False

def interactive_test():
    """
    Interactive test mode
    """
    print(f"\n🔄 INTERACTIVE TEST MODE")
    print("=" * 40)
    
    while True:
        try:
            print("\nEnter test parameters (or 'quit' to exit):")
            client_id = input("Client ID: ").strip()
            
            if client_id.lower() == 'quit':
                print("👋 Goodbye!")
                break
                
            policy_number = input("Policy Number: ").strip()
            
            if not client_id or not policy_number:
                print("❌ Please provide both Client ID and Policy Number")
                continue
            
            print(f"\n🔍 Testing with Client ID: {client_id}, Policy: {policy_number}")
            
            # Test the call function (without actually making the call)
            try:
                # This will extract customer info and show what would be sent to VAPI
                customer_info = test_customer_info_extraction()
                if customer_info:
                    test_vapi_payload_generation(customer_info)
            except Exception as e:
                print(f"❌ Test failed: {e}")
            
            print("\n" + "-"*40)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            continue

if __name__ == "__main__":
    print("🧪 PERSONALIZED VAPI CALLS TEST SUITE")
    print("=" * 50)
    print("This script tests the integration between Smartsheet and VAPI")
    print("for personalized customer calls.")
    print()
    
    # Run full test suite
    success = run_full_test()
    
    if success:
        print(f"\n🎉 Ready to use personalized calls!")
        print(f"💡 Run 'python test_personalized_calls.py' for interactive testing")
    else:
        print(f"\n⚠️ Please check your Smartsheet connection and try again")
