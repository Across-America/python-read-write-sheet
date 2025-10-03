#!/usr/bin/env python3
"""
Update all call results in Smartsheet with VAPI analysis
Gets all calls from VAPI and updates corresponding customers in Smartsheet
"""

import os
import requests
import time
import json
from dotenv import load_dotenv
import smartsheet

# Load environment variables
load_dotenv()

# VAPI Configuration
VAPI_API_KEY = "763666f4-1d39-46f5-9539-0b052ddb8495"

# Smartsheet Configuration
token = os.getenv('SMARTSHEET_ACCESS_TOKEN', 'xr7pjb35y9FyLBJ1KoPXyTQ91W4kD7UQH9kFO')
smart = smartsheet.Smartsheet(access_token=token)
smart.errors_as_exceptions(True)
cancellation_dev_sheet_id = 5146141873098628

def get_all_calls():
    """
    Get all calls from VAPI API
    """
    try:
        print("🔍 Fetching all calls from VAPI...")
        response = requests.get(
            "https://api.vapi.ai/call",
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}"
            }
        )
        
        if response.status_code == 200:
            calls = response.json()
            print(f"✅ Found {len(calls)} total calls")
            return calls
        else:
            print(f"❌ Failed to get calls: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Error fetching calls: {e}")
        return []

def get_call_details(call_id):
    """
    Get detailed call information including analysis
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
            print(f"❌ Failed to get call details for {call_id}: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting call details for {call_id}: {e}")
        return None

def find_customer_by_phone(phone_number):
    """
    Find customer in Smartsheet by phone number
    """
    try:
        sheet = smart.Sheets.get_sheet(cancellation_dev_sheet_id)
        
        # Find phone number column
        phone_col = None
        for col in sheet.columns:
            if col.title == "Phone number":
                phone_col = col.id
                break
        
        if not phone_col:
            return None
        
        # Search for customer by phone number
        for row in sheet.rows:
            phone_cell = row.get_column(phone_col)
            current_phone = str(phone_cell.display_value).strip() if phone_cell.display_value else ""
            
            # Format phone numbers for comparison
            def format_phone_for_comparison(phone):
                cleaned = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
                if len(cleaned) == 10:
                    return f"+1{cleaned}"
                elif len(cleaned) == 11 and cleaned.startswith('1'):
                    return f"+{cleaned}"
                else:
                    return phone
            
            if format_phone_for_comparison(current_phone) == phone_number:
                # Found the customer! Get all information
                customer_info = {
                    "row_id": row.id,
                    "row_number": row.row_number,
                    "phone_number": current_phone
                }
                
                # Add other useful information
                for col in sheet.columns:
                    if col.title in ["Client ID", "Policy Number", "Agent Name", "Office", "Insured", "LOB", "Status", "Cancellation Reason", "Cancellation Date"]:
                        cell = row.get_column(col.id)
                        value = str(cell.display_value) if cell.display_value else ""
                        customer_info[col.title.lower().replace(" ", "_")] = value
                
                return customer_info
        
        return None
        
    except Exception as e:
        print(f"❌ Error finding customer by phone {phone_number}: {e}")
        return None

def update_call_result_in_smartsheet(customer_info, call_data):
    """
    Update the Call Result column in Smartsheet with detailed VAPI analysis
    """
    try:
        print(f"\n📝 UPDATING SMARTSHEET FOR {customer_info.get('insured', 'Unknown')}")
        print("=" * 60)
        
        # Get the analysis data
        analysis = call_data.get('analysis', {})
        summary = analysis.get('summary', '')
        structured_data = analysis.get('structuredData', {})
        success_evaluation = analysis.get('successEvaluation', '')
        
        # Get call details
        ended_reason = call_data.get('endedReason', '')
        duration = call_data.get('duration', 0)
        cost = call_data.get('cost', 0)
        
        # Build detailed call result
        call_result_parts = []
        
        # 1. Basic call status
        call_result_parts.append("CALL COMPLETED")
        
        # 2. Call summary (main content)
        if summary:
            # Extract key information from summary
            summary_lines = summary.split('\n')
            for line in summary_lines:
                line = line.strip()
                if line and not line.startswith('**') and not line.startswith('Transfer Outcome:'):
                    # Clean up the summary text
                    clean_line = line.replace('**Call Summary:**', '').replace('**', '').strip()
                    if clean_line:
                        call_result_parts.append(f"SUMMARY: {clean_line}")
                        break
        
        # 3. Transfer status
        if structured_data and isinstance(structured_data, dict):
            call_outcome = structured_data.get('call_outcome', {})
            if call_outcome.get('transfer_requested'):
                call_result_parts.append("TRANSFER REQUESTED")
            if call_outcome.get('transfer_completed'):
                call_result_parts.append("SUCCESSFULLY TRANSFERRED")
            if call_outcome.get('customer_ended_call'):
                call_result_parts.append("CUSTOMER ENDED CALL")
        
        # 4. Customer response details
        if structured_data and isinstance(structured_data, dict):
            customer_response = structured_data.get('customer_response', {})
            payment_claimed = customer_response.get('payment_status_claimed', '')
            if payment_claimed and payment_claimed != 'not mentioned':
                call_result_parts.append(f"PAYMENT CLAIMED: {payment_claimed}")
            
            concerns = customer_response.get('concerns_raised', [])
            if concerns:
                concerns_str = ', '.join(concerns[:2])  # Limit to first 2 concerns
                call_result_parts.append(f"CONCERNS: {concerns_str}")
        
        # 5. Call quality indicators
        if structured_data and isinstance(structured_data, dict):
            call_quality = structured_data.get('call_quality', {})
            if call_quality.get('customer_understood'):
                call_result_parts.append("CUSTOMER UNDERSTOOD")
            if call_quality.get('customer_engaged'):
                call_result_parts.append("CUSTOMER ENGAGED")
        
        # 6. Follow-up requirements
        if structured_data and isinstance(structured_data, dict):
            follow_up = structured_data.get('follow_up', {})
            if follow_up.get('callback_requested'):
                call_result_parts.append("CALLBACK REQUESTED")
            if follow_up.get('escalation_needed'):
                call_result_parts.append("ESCALATION NEEDED")
            
            notes = follow_up.get('notes', '')
            if notes and len(notes) > 10:
                # Truncate long notes
                short_notes = notes[:50] + "..." if len(notes) > 50 else notes
                call_result_parts.append(f"NOTES: {short_notes}")
        
        # 7. Success evaluation
        if success_evaluation:
            success_status = "SUCCESS" if str(success_evaluation).lower() == 'true' else "UNSUCCESSFUL"
            call_result_parts.append(f"EVALUATION: {success_status}")
        
        # 8. Call metrics
        call_result_parts.append(f"DURATION: {duration}s")
        call_result_parts.append(f"COST: ${cost:.4f}")
        
        # Join all parts with " | " separator
        call_result = " | ".join(call_result_parts)
        
        print(f"📊 Detailed Call Result:")
        print(f"   {call_result}")
        
        # Find the Call Result column
        sheet = smart.Sheets.get_sheet(cancellation_dev_sheet_id)
        call_result_col = None
        
        for col in sheet.columns:
            if col.title == "Call Result":
                call_result_col = col.id
                break
        
        if not call_result_col:
            print("❌ Call Result column not found in Smartsheet")
            return False
        
        # Update the cell
        row_id = customer_info['row_id']
        
        # Create the cell update
        cell = smart.models.Cell()
        cell.column_id = call_result_col
        cell.value = call_result
        
        # Create the row update
        row = smart.models.Row()
        row.id = row_id
        row.cells = [cell]
        
        # Update the row
        result = smart.Sheets.update_rows(cancellation_dev_sheet_id, [row])
        
        if result.result:
            print(f"✅ Successfully updated Call Result in Smartsheet!")
            return True
        else:
            print(f"❌ Failed to update Smartsheet: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating Smartsheet: {e}")
        return False

def main():
    """
    Main function to update all call results
    """
    print("🤖 UPDATE ALL CALL RESULTS SYSTEM")
    print("=" * 60)
    print("Getting all calls from VAPI and updating Smartsheet")
    print("=" * 60)
    
    # Get all calls from VAPI
    all_calls = get_all_calls()
    
    if not all_calls:
        print("❌ No calls found")
        return
    
    # Filter for calls that are ended and have analysis
    ended_calls = []
    
    for call in all_calls:
        if call.get('status') == 'ended':
            ended_calls.append(call)
    
    print(f"📊 Found {len(ended_calls)} ended calls")
    
    # Process each call
    updated_count = 0
    failed_count = 0
    
    for i, call in enumerate(ended_calls, 1):
        call_id = call['id']
        
        # Check if call has customer information
        if 'customer' not in call or 'name' not in call['customer'] or 'number' not in call['customer']:
            print(f"\n⚠️  Skipping call {i}/{len(ended_calls)}: No customer information")
            continue
            
        customer_name = call['customer']['name']
        customer_phone = call['customer']['number']
        call_status = call['status']
        ended_reason = call.get('endedReason', 'unknown')
        
        print(f"\n📞 Processing call {i}/{len(ended_calls)}: {customer_name}")
        print(f"   Phone: {customer_phone}")
        print(f"   Status: {call_status}")
        print(f"   End Reason: {ended_reason}")
        
        # Find customer in Smartsheet
        customer_info = find_customer_by_phone(customer_phone)
        
        if not customer_info:
            print(f"❌ Customer not found in Smartsheet for {customer_phone}")
            failed_count += 1
            continue
        
        print(f"✅ Found customer: {customer_info.get('insured', 'Unknown')}")
        
        # Get detailed call information
        call_details = get_call_details(call_id)
        
        if not call_details:
            print(f"❌ Failed to get call details for {call_id}")
            failed_count += 1
            continue
        
        # Update Smartsheet
        if update_call_result_in_smartsheet(customer_info, call_details):
            updated_count += 1
            print(f"✅ Successfully updated {customer_name}")
        else:
            failed_count += 1
            print(f"❌ Failed to update {customer_name}")
        
        # Add delay to avoid rate limiting
        time.sleep(1)
    
    print(f"\n🎉 UPDATE COMPLETED!")
    print(f"✅ Successfully updated: {updated_count} customers")
    print(f"❌ Failed to update: {failed_count} customers")
    print(f"📊 Total processed: {len(ended_calls)} calls")

if __name__ == "__main__":
    main()
