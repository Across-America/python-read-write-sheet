# Update Smartsheet Call Result based on VAPI call status
import requests
import os
from dotenv import load_dotenv
import smartsheet
from read_cancellation_dev import find_phone_by_client_policy

# Load environment variables
load_dotenv()

# VAPI Configuration
VAPI_API_KEY = "763666f4-1d39-46f5-9539-0b052ddb8495"

# Smartsheet Configuration
token = os.getenv('SMARTSHEET_ACCESS_TOKEN', 'xr7pjb35y9FyLBJ1KoPXyTQ91W4kD7UQH9kFO')
smart = smartsheet.Smartsheet(access_token=token)
smart.errors_as_exceptions(True)
cancellation_dev_sheet_id = 5146141873098628

def get_call_status(call_id):
    """
    Get call status from VAPI API
    
    Args:
        call_id (str): VAPI call ID
    
    Returns:
        dict: Call details or None if failed
    """
    try:
        print(f"📞 Getting call status for ID: {call_id}")
        
        response = requests.get(
            f"https://api.vapi.ai/call/{call_id}",
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}"
            }
        )
        
        if response.status_code == 200:
            call_data = response.json()
            print(f"✅ Call data retrieved successfully")
            print(f"📊 Status: {call_data.get('status', 'Unknown')}")
            print(f"⏱️ Duration: {call_data.get('startedAt', 'N/A')} to {call_data.get('endedAt', 'N/A')}")
            return call_data
        else:
            print(f"❌ Failed to get call data: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting call status: {e}")
        return None

def update_call_result_in_smartsheet(client_id, policy_number, call_result):
    """
    Update Call Result column in Smartsheet for specific client/policy
    
    Args:
        client_id (str): Client ID
        policy_number (str): Policy Number
        call_result (str): Call result to update
    
    Returns:
        bool: Success status
    """
    try:
        print(f"🔍 Finding record for Client ID: {client_id}, Policy: {policy_number}")
        
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
        
        # Create update request
        new_cell = smart.models.Cell()
        new_cell.column_id = call_result_col_id
        new_cell.value = call_result
        
        new_row = smart.models.Row()
        new_row.id = target_row_id
        new_row.cells.append(new_cell)
        
        # Update the sheet
        print(f"📝 Updating Call Result to: {call_result}")
        update_result = smart.Sheets.update_rows(cancellation_dev_sheet_id, [new_row])
        
        if update_result.message == "SUCCESS":
            print(f"✅ Successfully updated Call Result!")
            return True
        else:
            print(f"❌ Update failed: {update_result.message}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating Smartsheet: {e}")
        return False

def process_call_result(call_id, client_id, policy_number):
    """
    Complete workflow: Get call status and update Smartsheet
    
    Args:
        call_id (str): VAPI call ID
        client_id (str): Client ID
        policy_number (str): Policy Number
    
    Returns:
        bool: Success status
    """
    print(f"🚀 PROCESSING CALL RESULT")
    print(f"Call ID: {call_id}")
    print(f"Client ID: {client_id}")
    print(f"Policy Number: {policy_number}")
    print("="*60)
    
    # Step 1: Get call status
    call_data = get_call_status(call_id)
    if not call_data:
        return False
    
    # Step 2: Check if call is ended
    call_status = call_data.get('status', '')
    if call_status != 'ended':
        print(f"⏳ Call is not ended yet. Status: {call_status}")
        print("Please wait for call to complete before updating.")
        return False
    
    # Step 3: Determine call result based on call data
    ended_reason = call_data.get('endedReason', '')
    transcript = call_data.get('transcript', '')
    summary = call_data.get('summary', '')
    
    # Create call result summary
    call_result_parts = []
    
    # Add basic status
    call_result_parts.append(f"Status: {call_status.upper()}")
    
    # Add end reason
    if ended_reason:
        call_result_parts.append(f"Reason: {ended_reason}")
    
    # Add key information from summary if available
    if summary:
        # Extract key points from summary (first 200 chars)
        summary_short = summary[:200] + "..." if len(summary) > 200 else summary
        call_result_parts.append(f"Summary: {summary_short}")
    
    # Add cost information
    cost = call_data.get('cost', 0)
    if cost:
        call_result_parts.append(f"Cost: ${cost:.4f}")
    
    call_result = " | ".join(call_result_parts)
    
    print(f"📋 Generated Call Result:")
    print(f"   {call_result}")
    
    # Step 4: Update Smartsheet
    success = update_call_result_in_smartsheet(client_id, policy_number, call_result)
    
    if success:
        print(f"\n🎉 PROCESS COMPLETED SUCCESSFULLY!")
        print(f"✅ Call result updated in Smartsheet")
        return True
    else:
        print(f"\n❌ PROCESS FAILED")
        return False

# Example usage and testing
if __name__ == "__main__":
    print("📞 CALL RESULT PROCESSOR")
    print("="*50)
    
    # Example with the call ID from your screenshot
    example_call_id = "0c192ea2-7ce3-4fb1-adbf-266b0dc41033"
    example_client_id = "24765"
    example_policy_number = "BSNDP-2025-012160-01"
    
    print("🧪 EXAMPLE TEST:")
    print(f"Processing call result for known customer...")
    
    # Uncomment to run the actual update
    # process_call_result(example_call_id, example_client_id, example_policy_number)
    
    print("\n💡 To use this function:")
    print("1. Make a VAPI call and get the call ID")
    print("2. Wait for call to complete")
    print("3. Run: process_call_result(call_id, client_id, policy_number)")
    
    # Interactive mode
    print(f"\n" + "="*50)
    print("🔄 INTERACTIVE MODE")
    
    while True:
        try:
            print("\nEnter call details (or 'quit' to exit):")
            call_id = input("Call ID: ").strip()
            
            if call_id.lower() == 'quit':
                break
                
            client_id = input("Client ID: ").strip()
            policy_number = input("Policy Number: ").strip()
            
            if call_id and client_id and policy_number:
                process_call_result(call_id, client_id, policy_number)
            else:
                print("❌ Please provide all required information")
                
            print("\n" + "-"*40)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
