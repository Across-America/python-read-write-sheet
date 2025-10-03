#!/usr/bin/env python3
"""
Fix incomplete Call Results for Called customers
Gets detailed VAPI analysis for customers with incomplete Call Results
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

def get_called_customers_with_incomplete_results():
    """
    Get customers with 'Called' status but incomplete Call Results
    """
    try:
        print("🔍 Finding Called customers with incomplete Call Results...")
        sheet = smart.Sheets.get_sheet(cancellation_dev_sheet_id)
        
        # Find columns
        call_status_col = None
        call_result_col = None
        insured_col = None
        phone_col = None
        
        for col in sheet.columns:
            if col.title == "Call Status":
                call_status_col = col.id
            elif col.title == "Call Result":
                call_result_col = col.id
            elif col.title == "Insured":
                insured_col = col.id
            elif col.title == "Phone number":
                phone_col = col.id
        
        customers = []
        
        for row in sheet.rows:
            call_status_cell = row.get_column(call_status_col)
            call_result_cell = row.get_column(call_result_col)
            insured_cell = row.get_column(insured_col)
            phone_cell = row.get_column(phone_col)
            
            call_status = str(call_status_cell.display_value).strip() if call_status_cell.display_value else ""
            call_result = str(call_result_cell.display_value).strip() if call_result_cell.display_value else ""
            insured = str(insured_cell.display_value).strip() if insured_cell.display_value else ""
            phone = str(phone_cell.display_value).strip() if phone_cell.display_value else ""
            
            # Check if customer is Called but has incomplete Call Result
            if (call_status == "Called" and 
                call_result and 
                len(call_result) < 100 and  # Too short
                "CALL COMPLETED" in call_result):
                
                customer = {
                    "row_id": row.id,
                    "row_number": row.row_number,
                    "insured": insured,
                    "phone_number": phone,
                    "current_call_result": call_result
                }
                
                # Add other useful information
                for col in sheet.columns:
                    if col.title in ["Client ID", "Policy Number", "Agent Name", "Office", "LOB", "Status", "Cancellation Reason", "Cancellation Date"]:
                        cell = row.get_column(col.id)
                        value = str(cell.display_value) if cell.display_value else ""
                        customer[col.title.lower().replace(" ", "_")] = value
                
                customers.append(customer)
        
        print(f"✅ Found {len(customers)} customers with incomplete Call Results")
        return customers
        
    except Exception as e:
        print(f"❌ Error loading customers: {e}")
        return []

def get_recent_calls_for_customer(customer_phone):
    """
    Get recent calls for a specific customer phone number
    """
    try:
        # Format phone number for comparison
        def format_phone_for_comparison(phone):
            cleaned = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            if len(cleaned) == 10:
                return f"+1{cleaned}"
            elif len(cleaned) == 11 and cleaned.startswith('1'):
                return f"+{cleaned}"
            else:
                return phone
        
        formatted_phone = format_phone_for_comparison(customer_phone)
        
        # Get all calls
        response = requests.get(
            "https://api.vapi.ai/call",
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}"
            }
        )
        
        if response.status_code == 200:
            calls = response.json()
            
            # Find calls for this customer
            customer_calls = []
            for call in calls:
                if (call.get('customer', {}).get('number') == formatted_phone and 
                    call.get('status') == 'ended'):
                    customer_calls.append(call)
            
            # Sort by creation time (most recent first)
            customer_calls.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
            
            return customer_calls
        else:
            print(f"❌ Failed to get calls: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Error getting calls for {customer_phone}: {e}")
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
    Main function to fix incomplete call results
    """
    print("🔧 FIX INCOMPLETE CALL RESULTS")
    print("=" * 60)
    print("Finding and fixing customers with incomplete Call Results")
    print("=" * 60)
    
    # Get customers with incomplete Call Results
    customers = get_called_customers_with_incomplete_results()
    
    if not customers:
        print("✅ No customers found with incomplete Call Results!")
        return
    
    print(f"\n📊 Found {len(customers)} customers with incomplete Call Results:")
    for i, customer in enumerate(customers, 1):
        print(f" {i:2d}. {customer.get('insured', 'Unknown')} - {customer['phone_number']}")
        print(f"     Current Call Result: {customer['current_call_result']}")
    
    # Process each customer
    updated_count = 0
    failed_count = 0
    
    for i, customer in enumerate(customers, 1):
        print(f"\n📞 Processing customer {i}/{len(customers)}: {customer.get('insured', 'Unknown')}")
        print(f"   Phone: {customer['phone_number']}")
        
        # Get recent calls for this customer
        customer_calls = get_recent_calls_for_customer(customer['phone_number'])
        
        if not customer_calls:
            print(f"❌ No recent calls found for {customer['phone_number']}")
            failed_count += 1
            continue
        
        print(f"✅ Found {len(customer_calls)} recent calls")
        
        # Get detailed call information for the most recent call
        most_recent_call = customer_calls[0]
        call_id = most_recent_call['id']
        print(f"   Using most recent call: {call_id}")
        
        call_details = get_call_details(call_id)
        
        if not call_details:
            print(f"❌ Failed to get call details for {call_id}")
            failed_count += 1
            continue
        
        # Update Smartsheet with detailed analysis
        if update_call_result_in_smartsheet(customer, call_details):
            updated_count += 1
            print(f"✅ Successfully updated {customer.get('insured', 'Unknown')}")
        else:
            failed_count += 1
            print(f"❌ Failed to update {customer.get('insured', 'Unknown')}")
        
        # Add delay to avoid rate limiting
        time.sleep(1)
    
    print(f"\n🎉 FIX COMPLETED!")
    print(f"✅ Successfully updated: {updated_count} customers")
    print(f"❌ Failed to update: {failed_count} customers")
    print(f"📊 Total processed: {len(customers)} customers")

if __name__ == "__main__":
    main()

