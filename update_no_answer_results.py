#!/usr/bin/env python3
"""
Update Call Results for customers who didn't answer
Set appropriate Call Results for no-answer calls
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

def get_called_customers_with_basic_results():
    """
    Get customers with 'Called' status but only basic Call Results
    """
    try:
        print("🔍 Finding Called customers with basic Call Results...")
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
            
            # Check if customer is Called but has only basic Call Result
            if (call_status == "Called" and 
                call_result and 
                "CALL COMPLETED | DURATION: 0s | COST: $0.0000" in call_result):
                
                customer = {
                    "row_id": row.id,
                    "row_number": row.row_number,
                    "insured": insured,
                    "phone_number": phone,
                    "current_call_result": call_result
                }
                
                customers.append(customer)
        
        print(f"✅ Found {len(customers)} customers with basic Call Results")
        return customers
        
    except Exception as e:
        print(f"❌ Error loading customers: {e}")
        return []

def get_call_details_for_customer(customer_phone):
    """
    Get call details for a specific customer
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
            for call in calls:
                if (call.get('customer', {}).get('number') == formatted_phone and 
                    call.get('status') == 'ended'):
                    return call
            
            return None
        else:
            print(f"❌ Failed to get calls: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting calls for {customer_phone}: {e}")
        return None

def update_call_result_in_smartsheet(customer_info, call_data):
    """
    Update the Call Result column in Smartsheet with appropriate result
    """
    try:
        print(f"\n📝 UPDATING SMARTSHEET FOR {customer_info.get('insured', 'Unknown')}")
        print("=" * 60)
        
        # Get call details
        ended_reason = call_data.get('endedReason', 'unknown')
        duration = call_data.get('duration', 0)
        cost = call_data.get('cost', 0)
        
        # Build appropriate call result based on end reason
        call_result_parts = []
        
        # 1. Basic call status
        call_result_parts.append("CALL COMPLETED")
        
        # 2. Call outcome based on end reason
        if ended_reason == "customer-did-not-answer":
            call_result_parts.append("SUMMARY: Customer did not answer the call")
            call_result_parts.append("CUSTOMER ENDED CALL")
            call_result_parts.append("EVALUATION: UNSUCCESSFUL")
        elif ended_reason == "silence-timed-out":
            call_result_parts.append("SUMMARY: Call timed out due to silence")
            call_result_parts.append("CUSTOMER ENDED CALL")
            call_result_parts.append("EVALUATION: UNSUCCESSFUL")
        elif ended_reason == "assistant-forwarded-call":
            call_result_parts.append("SUMMARY: Customer was successfully transferred to billing specialist")
            call_result_parts.append("TRANSFER REQUESTED")
            call_result_parts.append("SUCCESSFULLY TRANSFERRED")
            call_result_parts.append("EVALUATION: SUCCESS")
        elif ended_reason == "customer-ended-call":
            call_result_parts.append("SUMMARY: Customer ended the call")
            call_result_parts.append("CUSTOMER ENDED CALL")
            call_result_parts.append("EVALUATION: UNSUCCESSFUL")
        else:
            call_result_parts.append(f"SUMMARY: Call ended - {ended_reason}")
            call_result_parts.append("EVALUATION: UNSUCCESSFUL")
        
        # 3. Call metrics
        call_result_parts.append(f"DURATION: {duration}s")
        call_result_parts.append(f"COST: ${cost:.4f}")
        
        # Join all parts with " | " separator
        call_result = " | ".join(call_result_parts)
        
        print(f"📊 Updated Call Result:")
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
    Main function to update no-answer call results
    """
    print("🔧 UPDATE NO-ANSWER CALL RESULTS")
    print("=" * 60)
    print("Updating Call Results for customers who didn't answer")
    print("=" * 60)
    
    # Get customers with basic Call Results
    customers = get_called_customers_with_basic_results()
    
    if not customers:
        print("✅ No customers found with basic Call Results!")
        return
    
    print(f"\n📊 Found {len(customers)} customers with basic Call Results:")
    for i, customer in enumerate(customers, 1):
        print(f" {i:2d}. {customer.get('insured', 'Unknown')} - {customer['phone_number']}")
    
    # Process each customer
    updated_count = 0
    failed_count = 0
    
    for i, customer in enumerate(customers, 1):
        print(f"\n📞 Processing customer {i}/{len(customers)}: {customer.get('insured', 'Unknown')}")
        print(f"   Phone: {customer['phone_number']}")
        
        # Get call details for this customer
        call_data = get_call_details_for_customer(customer['phone_number'])
        
        if not call_data:
            print(f"❌ No call data found for {customer['phone_number']}")
            failed_count += 1
            continue
        
        print(f"✅ Found call data - End Reason: {call_data.get('endedReason', 'unknown')}")
        
        # Update Smartsheet with appropriate result
        if update_call_result_in_smartsheet(customer, call_data):
            updated_count += 1
            print(f"✅ Successfully updated {customer.get('insured', 'Unknown')}")
        else:
            failed_count += 1
            print(f"❌ Failed to update {customer.get('insured', 'Unknown')}")
        
        # Add delay to avoid rate limiting
        time.sleep(1)
    
    print(f"\n🎉 UPDATE COMPLETED!")
    print(f"✅ Successfully updated: {updated_count} customers")
    print(f"❌ Failed to update: {failed_count} customers")
    print(f"📊 Total processed: {len(customers)} customers")

if __name__ == "__main__":
    main()

