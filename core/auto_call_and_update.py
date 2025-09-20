# Auto call and update - Make call, monitor status, then update result
import requests  # pyright: ignore[reportMissingModuleSource]
import time
import os
from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
import smartsheet  # pyright: ignore[reportMissingImports]
from ..tools.read_cancellation_dev import find_phone_by_client_policy

# Load environment variables
load_dotenv()

# VAPI Configuration
VAPI_API_KEY = "763666f4-1d39-46f5-9539-0b052ddb8495"
ASSISTANT_ID = "8e07049e-f7c8-4e5d-a893-8c33a318490d"
# Smartsheet Configuration
token = os.getenv('SMARTSHEET_ACCESS_TOKEN', 'xr7pjb35y9FyLBJ1KoPXyTQ91W4kD7UQH9kFO')
smart = smartsheet.Smartsheet(access_token=token)
smart.errors_as_exceptions(True)
cancellation_dev_sheet_id = 5146141873098628



# Multiple phone numbers for load balancing and avoiding limits
PHONE_NUMBER_IDS = [
    "29e32cd8-432f-4205-85bd-c001154b94a2",  # Twilio number: +19093100491
    "9c5c434b-7c24-42c1-a53d-0b293d436a34",  # New number: +19093256365
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
    phone_id = PHONE_NUMBER_IDS[current_phone_index]
    current_phone_index = (current_phone_index + 1) % len(PHONE_NUMBER_IDS)
    return phone_id

def make_vapi_call(phone_number, customer_info=None):
    """
    Make VAPI call with personalized greeting and return call ID
    
    Args:
        phone_number (str): Phone number to call
        customer_info (dict): Optional customer information for context
    
    Returns:
        str: Call ID if successful, None if failed
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
    
    # Add customer context if available
    if customer_info:
        customer_name = customer_info.get("insured", "")
        agent_name = customer_info.get("agent_name", "")
        office = customer_info.get("office", "")
        policy_number = customer_info.get("policy_number", "")
        
        # Add customer information to the payload
        payload["customers"][0]["name"] = customer_name
        
        # Note: VAPI will use the customer name for personalization
        # The actual greeting template should be configured in VAPI dashboard
        # using variables like {{customer.name}}
        
        print(f"👤 Customer: {customer_name}")
        print(f"🏢 Office: {office}")
        print(f"👨‍💼 Agent: {agent_name}")
        print(f"📋 Policy: {policy_number}")
        print(f"📱 Phone: {phone_number}")
        print(f"💬 Variables set for VAPI template: customer_name, agent_name, office, policy_number, phone_number")
    
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
            elif isinstance(result, list) and len(result) > 0:
                call_id = result[0].get('id')
            
            print(f"✅ Call initiated successfully!")
            print(f"📞 Call ID: {call_id}")
            
            if not call_id:
                print(f"❌ Could not extract Call ID from response")
                return None
                
            return call_id
        else:
            print(f"❌ Call failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error making call: {e}")
        return None

def check_call_status(call_id):
    """
    Check call status from VAPI API
    
    Args:
        call_id (str): VAPI call ID
    
    Returns:
        dict: Call data or None if failed
    """
    try:
        response = requests.get(
            f"https://api.vapi.ai/call/{call_id}",
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}"
            }
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get call status: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error checking call status: {e}")
        return None

def wait_for_call_completion(call_id, check_interval=10, max_wait_time=600):
    """
    Wait for call to complete with status monitoring
    
    Args:
        call_id (str): VAPI call ID
        check_interval (int): Seconds between status checks
        max_wait_time (int): Maximum wait time in seconds
    
    Returns:
        dict: Final call data or None if timeout/error
    """
    print(f"⏳ Monitoring call status (checking every {check_interval} seconds)")
    print(f"⏰ Maximum wait time: {max_wait_time} seconds")
    
    start_time = time.time()
    
    while True:
        # Check if we've exceeded max wait time
        elapsed_time = time.time() - start_time
        if elapsed_time > max_wait_time:
            print(f"⏰ Timeout reached ({max_wait_time}s). Stopping monitoring.")
            return None
        
        # Check call status
        call_data = check_call_status(call_id)
        if not call_data:
            print(f"❌ Failed to get call status. Retrying in {check_interval}s...")
            time.sleep(check_interval)
            continue
        
        status = call_data.get('status', 'unknown')
        print(f"📊 Call Status: {status} (elapsed: {int(elapsed_time)}s)")
        
        # Check if call is ended
        if status == 'ended':
            print(f"✅ Call completed!")
            ended_reason = call_data.get('endedReason', 'unknown')
            print(f"📋 End Reason: {ended_reason}")
            return call_data
        
        # If call is still active, wait and check again
        print(f"⏳ Call still active. Checking again in {check_interval}s...")
        time.sleep(check_interval)

def update_smartsheet_call_result(client_id, policy_number, call_data):
    """
    Update Call Result in Smartsheet based on call data
    
    Args:
        client_id (str): Client ID
        policy_number (str): Policy Number
        call_data (dict): VAPI call data
    
    Returns:
        bool: Success status
    """
    try:
        print(f"📝 Updating Smartsheet for Client ID: {client_id}, Policy: {policy_number}")
        
        # Get the sheet
        sheet = smart.Sheets.get_sheet(cancellation_dev_sheet_id)
        
        # Find the record
        result = find_phone_by_client_policy(sheet, client_id, policy_number)
        
        if not result["found"]:
            print(f"❌ Record not found: {result['error']}")
            return False
        
        print(f"✅ Found record at row {result['row_number']}")
        
        # Find Call Result column ID
        call_result_col_id = None
        for col in sheet.columns:
            if col.title == "Call Result":
                call_result_col_id = col.id
                break
        
        if not call_result_col_id:
            print("❌ Call Result column not found")
            return False
        
        # Find the row ID
        target_row_id = None
        for row in sheet.rows:
            if row.row_number == result['row_number']:
                target_row_id = row.id
                break
        
        if not target_row_id:
            print("❌ Target row not found")
            return False
        
        # Generate call result summary
        status = call_data.get('status', 'unknown')
        ended_reason = call_data.get('endedReason', 'unknown')
        cost = call_data.get('cost', 0)
        summary = call_data.get('summary', '')
        
        call_result_parts = [
            f"Status: {status.upper()}",
            f"Reason: {ended_reason}",
            f"Cost: ${cost:.4f}" if cost else "Cost: $0.00"
        ]
        
        # Add detailed summary information based on actual call content
        if summary:
            summary_lower = summary.lower()
            useful_info = []
            
            # Check for call issues first (highest priority)
            if 'wrong person' in summary_lower or 'wrong number' in summary_lower:
                useful_info.append('WRONG PERSON/NUMBER')
            elif 'not the right person' in summary_lower or 'different person' in summary_lower:
                useful_info.append('INCORRECT CONTACT')
            elif 'no answer' in summary_lower or 'voicemail' in summary_lower or 'answering machine' in summary_lower:
                useful_info.append('NO ANSWER/VOICEMAIL')
            elif 'busy' in summary_lower or 'line busy' in summary_lower:
                useful_info.append('LINE BUSY')
            elif 'disconnected' in summary_lower or 'hung up' in summary_lower:
                useful_info.append('CALL DISCONNECTED')
            
            # Check for customer responses
            if 'not interested' in summary_lower or 'declined' in summary_lower or 'refused' in summary_lower:
                useful_info.append('Customer declined')
            elif 'interested' in summary_lower or 'wants' in summary_lower or 'agreed' in summary_lower:
                useful_info.append('Customer interested')
            elif 'angry' in summary_lower or 'upset' in summary_lower or 'frustrated' in summary_lower:
                useful_info.append('Customer upset')
            elif 'confused' in summary_lower or 'unsure' in summary_lower:
                useful_info.append('Customer confused')
            
            # Check for specific outcomes
            if 'resolved' in summary_lower or 'solved' in summary_lower or 'fixed' in summary_lower:
                useful_info.append('Issue resolved')
            elif 'follow up' in summary_lower or 'callback' in summary_lower or 'call back' in summary_lower:
                useful_info.append('Needs follow-up')
            elif 'transfer' in summary_lower or 'forwarded' in summary_lower:
                useful_info.append('Call transferred')
            
            # Check for payment related
            if 'payment made' in summary_lower or 'paid' in summary_lower or 'payment received' in summary_lower:
                useful_info.append('Payment received')
            elif 'payment issue' in summary_lower or 'payment problem' in summary_lower or 'cannot pay' in summary_lower:
                useful_info.append('Payment issue')
            
            # Only mark as SUCCESS if there are clear positive indicators and no negative ones
            negative_indicators = ['wrong person', 'wrong number', 'not interested', 'declined', 'refused', 'angry', 'upset', 'hung up', 'disconnected', 'no answer']
            positive_indicators = ['resolved', 'agreed', 'interested', 'payment made', 'successful', 'completed successfully']
            
            has_negative = any(indicator in summary_lower for indicator in negative_indicators)
            has_positive = any(indicator in summary_lower for indicator in positive_indicators)
            
            if has_positive and not has_negative:
                if 'SUCCESS' not in [info.upper() for info in useful_info]:
                    useful_info.append('SUCCESS')
            elif has_negative:
                if 'FAILED' not in [info.upper() for info in useful_info]:
                    useful_info.append('ISSUE DETECTED')
            
            # Create detailed summary
            if useful_info:
                summary_short = ' | '.join(useful_info[:4])  # Allow up to 4 key points
            else:
                summary_short = 'Call completed - outcome unclear'
            
            call_result_parts.append(f"Summary: {summary_short}")
        
        call_result = " | ".join(call_result_parts)
        
        print(f"📋 Call Result: {call_result}")
        
        # Create update request
        new_cell = smart.models.Cell()
        new_cell.column_id = call_result_col_id
        new_cell.value = call_result
        
        new_row = smart.models.Row()
        new_row.id = target_row_id
        new_row.cells.append(new_cell)
        
        # Update the sheet
        update_result = smart.Sheets.update_rows(cancellation_dev_sheet_id, [new_row])
        
        if update_result.message == "SUCCESS":
            print(f"✅ Successfully updated Call Result in Smartsheet!")
            return True
        else:
            print(f"❌ Update failed: {update_result.message}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating Smartsheet: {e}")
        return False

def auto_call_and_update(client_id, policy_number, phone_number=None):
    """
    Complete workflow: Make call, monitor status, update result
    
    Args:
        client_id (str): Client ID
        policy_number (str): Policy Number
        phone_number (str): Phone number (optional, will lookup if not provided)
    
    Returns:
        bool: Success status
    """
    print(f"🚀 AUTO CALL AND UPDATE WORKFLOW")
    print(f"Client ID: {client_id}")
    print(f"Policy Number: {policy_number}")
    print("="*60)
    
    customer_info = None  # Initialize customer_info
    
    # Step 1: Get phone number and customer info if not provided
    if not phone_number:
        print(f"🔍 Looking up phone number...")
        try:
            sheet = smart.Sheets.get_sheet(cancellation_dev_sheet_id)
            result = find_phone_by_client_policy(sheet, client_id, policy_number)
            
            if not result["found"]:
                print(f"❌ Customer record not found: {result['error']}")
                return False
            
            phone_number = result.get('phone_number')
            customer_info = result  # Store customer info for later use
            
            if not phone_number or phone_number == "No phone number":
                print(f"❌ No valid phone number found for this customer")
                return False
            
            print(f"✅ Found phone number: {phone_number}")
            
        except Exception as e:
            print(f"❌ Error looking up phone number: {e}")
            return False
    
    # Step 2: Get customer info if not already available
    if not customer_info:
        try:
            sheet = smart.Sheets.get_sheet(cancellation_dev_sheet_id)
            result = find_phone_by_client_policy(sheet, client_id, policy_number)
            if result["found"]:
                customer_info = result
        except Exception as e:
            print(f"⚠️ Could not retrieve customer info: {e}")
    
    call_id = make_vapi_call(phone_number, customer_info)
    if not call_id:
        print(f"❌ Failed to initiate call")
        return False
    
    # Step 3: Monitor call status
    print(f"\n📡 MONITORING CALL STATUS")
    print("-" * 40)
    
    call_data = wait_for_call_completion(call_id)
    if not call_data:
        print(f"❌ Failed to get final call status")
        return False
    
    # Step 4: Update Smartsheet
    print(f"\n📝 UPDATING SMARTSHEET")
    print("-" * 40)
    
    success = update_smartsheet_call_result(client_id, policy_number, call_data)
    
    if success:
        print(f"\n🎉 WORKFLOW COMPLETED SUCCESSFULLY!")
        print(f"✅ Call made, monitored, and result updated")
        return True
    else:
        print(f"\n❌ WORKFLOW FAILED")
        return False

# Example usage and testing
if __name__ == "__main__":
    print("🤖 AUTO CALL AND UPDATE SYSTEM")
    print("="*50)
    
    # Example test
    print("🧪 EXAMPLE TEST:")
    print("This will make a call and automatically update the result")
    
    # Uncomment to run actual test
    # auto_call_and_update("24765", "BSNDP-2025-012160-01")
    
    print("\n💡 To use this system:")
    print("1. Call: auto_call_and_update(client_id, policy_number)")
    print("2. System will automatically:")
    print("   - Look up phone number")
    print("   - Make VAPI call")
    print("   - Monitor call status")
    print("   - Update Smartsheet when call ends")
    
    # Interactive mode
    print(f"\n" + "="*50)
    print("🔄 INTERACTIVE MODE")
    
    while True:
        try:
            print("\nEnter customer details (or 'quit' to exit):")
            client_id = input("Client ID: ").strip()
            
            if client_id.lower() == 'quit':
                break
                
            policy_number = input("Policy Number: ").strip()
            
            if client_id and policy_number:
                print(f"\n🚀 Starting auto call and update process...")
                auto_call_and_update(client_id, policy_number)
            else:
                print("❌ Please provide both Client ID and Policy Number")
                
            print("\n" + "-"*50)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
