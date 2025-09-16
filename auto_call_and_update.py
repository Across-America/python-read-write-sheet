# Auto call and update - Make call, monitor status, then update result
import requests
import time
import os
from dotenv import load_dotenv
import smartsheet
from read_cancellation_dev import find_phone_by_client_policy

# Load environment variables
load_dotenv()

# VAPI Configuration
VAPI_API_KEY = "763666f4-1d39-46f5-9539-0b052ddb8495"
ASSISTANT_ID = "8e07049e-f7c8-4e5d-a893-8c33a318490d"
PHONE_NUMBER_ID = "2f8d40fa-32c8-421b-8c70-ec877e4e9948"

# Smartsheet Configuration
token = os.getenv('SMARTSHEET_ACCESS_TOKEN', 'xr7pjb35y9FyLBJ1KoPXyTQ91W4kD7UQH9kFO')
smart = smartsheet.Smartsheet(access_token=token)
smart.errors_as_exceptions(True)
cancellation_dev_sheet_id = 5146141873098628

def make_vapi_call(phone_number):
    """
    Make VAPI call and return call ID
    
    Args:
        phone_number (str): Phone number to call
    
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
        
        # Add summary if available (truncated)
        if summary:
            summary_short = summary[:150] + "..." if len(summary) > 150 else summary
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
    
    # Step 1: Get phone number if not provided
    if not phone_number:
        print(f"🔍 Looking up phone number...")
        try:
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
            
        except Exception as e:
            print(f"❌ Error looking up phone number: {e}")
            return False
    
    # Step 2: Make the call
    call_id = make_vapi_call(phone_number)
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
