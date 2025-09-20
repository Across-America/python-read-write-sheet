#!/usr/bin/env python3
"""
Test the enhanced VAPI system with policy information integration
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'core'))

# Import required modules
from read_cancellation_dev import find_phone_by_client_policy
import smartsheet
from dotenv import load_dotenv
import requests
import time

# Load environment variables
load_dotenv()

# Configuration
VAPI_API_KEY = "763666f4-1d39-46f5-9539-0b052ddb8495"
ASSISTANT_ID = "8e07049e-f7c8-4e5d-a893-8c33a318490d"
PHONE_NUMBER_IDS = [
    "29e32cd8-432f-4205-85bd-c001154b94a2",  # Twilio number: +19093100491
    "9c5c434b-7c24-42c1-a53d-0b293d436a34",  # New number: +19093256365
    "2f8d40fa-32c8-421b-8c70-ec877e4e9948",  # Original number: +16264602769
    "03c87616-5adf-4e83-ab40-9d921882f2d4",  # New number: +16265219363
]

# Smartsheet configuration
token = os.getenv('SMARTSHEET_ACCESS_TOKEN', 'xr7pjb35y9FyLBJ1KoPXyTQ91W4kD7UQH9kFO')
smart = smartsheet.Smartsheet(access_token=token)
smart.errors_as_exceptions(True)
cancellation_dev_sheet_id = 5146141873098628

current_phone_index = 0

def get_next_phone_number_id():
    """Get the next phone number ID in rotation"""
    global current_phone_index
    phone_id = PHONE_NUMBER_IDS[current_phone_index]
    current_phone_index = (current_phone_index + 1) % len(PHONE_NUMBER_IDS)
    return phone_id

def make_enhanced_vapi_call(phone_number, customer_info=None):
    """
    Make a VAPI call with enhanced customer context
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
    
    print(f"📞 Making VAPI call to: {formatted_phone}")
    
    # Get the next available phone number ID
    phone_number_id = get_next_phone_number_id()
    print(f"📞 Using phone number {current_phone_index}/{len(PHONE_NUMBER_IDS)}")
    
    # Prepare payload with customer context
    payload = {
        "assistantId": ASSISTANT_ID,
        "customers": [
            {
                "number": formatted_phone
            }
        ],
        "phoneNumberId": phone_number_id
    }
    
    # Add enhanced customer context if available
    if customer_info:
        customer_name = customer_info.get("insured", "")
        agent_name = customer_info.get("agent_name", "")
        office = customer_info.get("office", "")
        policy_number = customer_info.get("policy_number", "")
        lob = customer_info.get("lob", "")
        company = customer_info.get("company", "")
        status = customer_info.get("status", "")
        cancellation_date = customer_info.get("cancellation_date", "")
        cancellation_reason = customer_info.get("cancellation_reason", "")
        
        # Add customer information to the payload
        payload["customers"][0]["name"] = customer_name
        
        # Create comprehensive customer context for VAPI agent
        customer_context = {
            "customer_name": customer_name,
            "policy_number": policy_number,
            "agent_name": agent_name,
            "office": office,
            "lob": lob,
            "company": company,
            "status": status,
            "cancellation_date": cancellation_date,
            "cancellation_reason": cancellation_reason
        }
        
        # Add assistant overrides with enhanced context
        payload["assistantOverrides"] = {
            "variableValues": customer_context
        }
        
        print(f"👤 Customer: {customer_name}")
        print(f"🏢 Office: {office}")
        print(f"👨‍💼 Agent: {agent_name}")
        print(f"📋 Policy: {policy_number}")
        print(f"📱 Phone: {phone_number}")
        print(f"🏷️ LOB: {lob}")
        print(f"🏢 Company: {company}")
        print(f"📊 Status: {status}")
        if cancellation_date:
            print(f"📅 Cancellation Date: {cancellation_date}")
        if cancellation_reason:
            print(f"📝 Cancellation Reason: {cancellation_reason}")
        print(f"💬 Enhanced context sent to VAPI agent with complete policy information")
    
    try:
        response = requests.post(
            "https://api.vapi.ai/call",
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        print(f"📡 Response Status: {response.status_code}")
        
        if 200 <= response.status_code < 300:
            result = response.json()
            print(f"🔍 Full Response: {result}")
            
            # Try different ways to extract call ID
            call_id = None
            if 'id' in result:
                call_id = result['id']
            elif 'results' in result and len(result['results']) > 0:
                call_id = result['results'][0].get('id')
            
            if call_id:
                print(f"✅ Call initiated successfully!")
                print(f"📞 Call ID: {call_id}")
                return call_id
            else:
                print("⚠️ Call initiated but no ID returned")
                return result
        else:
            print(f"❌ Call failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error making VAPI call: {e}")
        return None

def test_enhanced_system():
    """Test the enhanced VAPI system with policy information"""
    print('🧪 TESTING ENHANCED VAPI SYSTEM WITH POLICY INFORMATION')
    print('=' * 65)
    print('📋 Expected: Agent should have complete policy context')
    print('📊 Including: LOB, agent, status, cancellation reason')
    print('🎯 Agent should be able to answer specific policy questions')
    print('=' * 65)
    
    # Test parameters
    client_id = "13910"
    policy_number = "CP0032322"
    
    try:
        # Get customer information
        sheet = smart.Sheets.get_sheet(cancellation_dev_sheet_id)
        result = find_phone_by_client_policy(sheet, client_id, policy_number)
        
        if not result["found"]:
            print(f"❌ Customer record not found: {result['error']}")
            return False
        
        phone_number = result.get('phone_number')
        if not phone_number or phone_number == "No phone number":
            print(f"❌ No valid phone number found for this customer")
            return False
        
        print(f"✅ Found phone number: {phone_number}")
        
        # Make the enhanced VAPI call
        call_id = make_enhanced_vapi_call(phone_number, result)
        
        if call_id:
            print(f"\n✅ Test successful!")
            print(f"📝 Agent now has complete policy context:")
            print(f"   • Customer Name: {result.get('insured', '')}")
            print(f"   • Policy Type: {result.get('lob', '')}")
            print(f"   • Agent: {result.get('agent_name', '')}")
            print(f"   • Status: {result.get('status', '')}")
            print(f"   • Cancellation Reason: {result.get('cancellation_reason', '')}")
            print(f"\n🎯 Agent should now be able to answer:")
            print(f"   Q: 'What type of insurance?' A: 'Your policy is {result.get('lob', '')} insurance'")
            print(f"   Q: 'Who is my agent?' A: 'I'm {result.get('agent_name', '')}, your assigned agent'")
            print(f"   Q: 'Policy number?' A: 'Your policy number is {policy_number}'")
            return True
        else:
            print(f"\n❌ Test failed - could not initiate call")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False

if __name__ == "__main__":
    test_enhanced_system()
