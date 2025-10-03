#!/usr/bin/env python3
"""
Auto batch call script for customers with "Not call yet" status
Automatically confirms batch calling without user input
"""

import sys
import os
import requests
import time
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import smartsheet

# Load environment variables
load_dotenv()

# VAPI Configuration
VAPI_API_KEY = "763666f4-1d39-46f5-9539-0b052ddb8495"
ASSISTANT_ID = "8e07049e-f7c8-4e5d-a893-8c33a318490d"  # Spencer: Call Transfer V2 Campaign

# 🏢 COMPANY CALLER ID CONFIGURATION
# 硬性要求：必须显示公司号码 +1 (951) 247-2003
COMPANY_PHONE_NUMBER_ID = "def7dca0-2096-42be-82d7-812eeb7e3ed3"  # +1 (951) 247-2003

# Smartsheet Configuration
token = os.getenv('SMARTSHEET_ACCESS_TOKEN', 'xr7pjb35y9FyLBJ1KoPXyTQ91W4kD7UQH9kFO')
smart = smartsheet.Smartsheet(access_token=token)
smart.errors_as_exceptions(True)
cancellation_dev_sheet_id = 5146141873098628

def format_phone_number(phone_number):
    """
    Format phone number to E.164 format
    """
    # Remove any spaces, dashes, or parentheses
    cleaned = phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    if not cleaned.startswith('+'):
        if len(cleaned) == 10:
            formatted_phone = f"+1{cleaned}"
        elif len(cleaned) == 11 and cleaned.startswith('1'):
            formatted_phone = f"+{cleaned}"
        else:
            formatted_phone = f"+1{cleaned}"
    else:
        formatted_phone = cleaned
    
    return formatted_phone

def get_not_called_customers():
    """
    Get all customers with "Not call yet" status from cancellation dev sheet
    """
    try:
        print("🔍 Loading customers with 'Not call yet' status...")
        sheet = smart.Sheets.get_sheet(cancellation_dev_sheet_id)
        
        customers = []
        
        # Find column IDs
        client_id_col = None
        policy_number_col = None
        phone_number_col = None
        call_status_col = None
        
        for col in sheet.columns:
            if col.title == "Client ID":
                client_id_col = col.id
            elif col.title == "Policy Number":
                policy_number_col = col.id
            elif col.title == "Phone number":
                phone_number_col = col.id
            elif col.title == "Call Status":
                call_status_col = col.id
        
        if not all([client_id_col, policy_number_col, phone_number_col]):
            print("❌ Required columns not found")
            return []
        
        if not call_status_col:
            print("❌ Call Status column not found")
            return []
        
        # Process all rows
        for row in sheet.rows:
            client_cell = row.get_column(client_id_col)
            policy_cell = row.get_column(policy_number_col)
            phone_cell = row.get_column(phone_number_col)
            call_status_cell = row.get_column(call_status_col)
            
            client_id = str(client_cell.display_value).strip() if client_cell.display_value else ""
            policy_number = str(policy_cell.display_value).strip() if policy_cell.display_value else ""
            phone_number = str(phone_cell.display_value).strip() if phone_cell.display_value else ""
            call_status = str(call_status_cell.display_value).strip() if call_status_cell.display_value else ""
            
            # Check if this customer has "Not call yet" status and valid phone number
            if (client_id and policy_number and phone_number and 
                phone_number != "No phone number" and 
                len(phone_number) >= 10 and
                call_status.lower() == "not call yet"):
                
                customer = {
                    "client_id": client_id,
                    "policy_number": policy_number,
                    "phone_number": phone_number,
                    "row_number": row.row_number,
                    "row_id": row.id,  # Add row_id for Smartsheet updates
                    "call_status": call_status
                }
                
                # Add other useful information
                for col in sheet.columns:
                    if col.title in ["Agent Name", "Office", "Insured", "LOB", "Status", "Cancellation Reason", "Cancellation Date"]:
                        cell = row.get_column(col.id)
                        value = str(cell.display_value) if cell.display_value else ""
                        customer[col.title.lower().replace(" ", "_")] = value
                
                customers.append(customer)
        
        print(f"✅ Found {len(customers)} customers with 'Not call yet' status")
        return customers
        
    except Exception as e:
        print(f"❌ Error loading customers: {e}")
        return []

def check_call_status(call_id):
    """
    Check call status from VAPI API
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

def wait_for_call_completion(call_id, check_interval=15, max_wait_time=300):
    """
    Wait for call to complete AND analysis to be generated
    """
    print(f"⏳ Monitoring call status and waiting for analysis...")
    print(f"⏰ Checking every {check_interval} seconds")
    print(f"⏰ Maximum wait time: {max_wait_time} seconds")
    
    start_time = time.time()
    call_ended = False
    analysis_wait_start = 0
    
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
        if status == 'ended' and not call_ended:
            print(f"✅ Call completed!")
            ended_reason = call_data.get('endedReason', 'unknown')
            print(f"📋 End Reason: {ended_reason}")
            
            # Show call details
            duration = call_data.get('duration', 0)
            cost = call_data.get('cost', 0)
            print(f"⏱️ Duration: {duration} seconds")
            print(f"💰 Cost: ${cost:.4f}")
            
            call_ended = True
            analysis_wait_start = time.time()
            print(f"⏳ Call ended, waiting for VAPI analysis to complete...")
            continue
        
        # If call has ended, check for analysis
        if call_ended:
            analysis_elapsed = time.time() - analysis_wait_start
            
            # Check for analysis results
            analysis = call_data.get('analysis', {})
            summary = analysis.get('summary', '')
            structured_data = analysis.get('structuredData', {})
            success_evaluation = analysis.get('successEvaluation', '')
            
            print(f"🔍 Checking for analysis... ({int(analysis_elapsed)}s elapsed)")
            
            # Check if we have meaningful analysis results
            has_summary = summary and len(summary.strip()) > 10
            has_structured_data = structured_data and len(str(structured_data)) > 10
            has_success_eval = success_evaluation and len(str(success_evaluation)) > 5
            
            if has_summary or has_structured_data or has_success_eval:
                print(f"📝 Analysis completed after {int(analysis_elapsed)}s!")
                print(f"   Summary: {'✅' if has_summary else '❌'}")
                print(f"   Structured Data: {'✅' if has_structured_data else '❌'}")
                print(f"   Success Evaluation: {'✅' if has_success_eval else '❌'}")
                
                return call_data
            elif analysis_elapsed > 180:  # Wait up to 3 minutes for analysis
                print(f"⏰ Analysis wait timeout (180s). Returning with current data.")
                return call_data
            else:
                print(f"⏳ Analysis still processing... ({int(analysis_elapsed)}s elapsed)")
                time.sleep(check_interval)
                continue
        
        # If call is still active, wait and check again
        print(f"⏳ Call still active. Checking again in {check_interval}s...")
        time.sleep(check_interval)

def make_batch_vapi_call(customers, schedule_immediately=True):
    """
    Make batch VAPI call using the customers parameter
    """
    print(f"🚀 Making batch VAPI call to {len(customers)} customers")
    print(f"🤖 Using Spencer: Call Transfer V2 Campaign assistant")
    print(f"🏢 Company caller ID: +1 (951) 247-2003")
    
    # Prepare customers array for VAPI
    vapi_customers = []
    all_customer_contexts = []  # Store all customer contexts for assistantOverrides
    
    for customer in customers:
        formatted_phone = format_phone_number(customer['phone_number'])
        
        # Create customer context for VAPI - matching your prompt template fields
        customer_context = {
            "number": formatted_phone,
            "name": customer.get('insured', 'Customer')
        }
        
        # Create context for assistant overrides - matching your prompt template fields
        assistant_context = {
            "Insured": customer.get('insured', 'Customer'),  # Matches {{Insured}}
            "agent_name": customer.get('agent_name', 'Spencer'),  # Matches {{agent_name}}
            "LOB": customer.get('lob', 'Insurance'),  # Matches {{LOB}}
            "Policy Number": customer.get('policy_number', ''),  # Matches {{Policy Number}}
            "Cancellation Date": customer.get('cancellation_date', ''),  # Matches {{Cancellation Date}}
            "office": customer.get('office', 'Insurance Office'),
            "status": customer.get('status', 'Active'),
            "cancellation_reason": customer.get('cancellation_reason', ''),
            "client_id": customer.get('client_id', '')
        }
        
        vapi_customers.append(customer_context)
        all_customer_contexts.append(assistant_context)
        
        print(f"   📞 {customer.get('insured', 'Unknown')} - {formatted_phone}")
        print(f"      Policy: {customer.get('policy_number', 'N/A')}")
        print(f"      Agent: {customer.get('agent_name', 'N/A')}")
        print(f"      LOB: {customer.get('lob', 'N/A')}")
    
    # Prepare payload with assistant overrides
    payload = {
        "assistantId": ASSISTANT_ID,
        "phoneNumberId": COMPANY_PHONE_NUMBER_ID,
        "customers": vapi_customers,
        "assistantOverrides": {
            "variableValues": all_customer_contexts[0] if all_customer_contexts else {}  # Use first customer's context
        }
    }
    
    # Add scheduling if not immediate
    if not schedule_immediately:
        # Schedule for 1 hour from now
        schedule_time = datetime.now() + timedelta(hours=1)
        payload["schedulePlan"] = {
            "earliestAt": schedule_time.isoformat() + "Z"
        }
        print(f"⏰ Scheduled for: {schedule_time}")
    else:
        print(f"⚡ Calling immediately")
    
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
            print(f"✅ Batch call initiated successfully!")
            print(f"🔍 Response: {json.dumps(result, indent=2)}")
            
            # Extract call IDs for monitoring
            call_ids = []
            if 'results' in result and isinstance(result['results'], list):
                for call_result in result['results']:
                    if 'id' in call_result:
                        call_ids.append(call_result['id'])
            elif 'id' in result:
                call_ids.append(result['id'])
            
            if call_ids:
                print(f"\n📞 Monitoring {len(call_ids)} call(s)...")
                for i, call_id in enumerate(call_ids, 1):
                    print(f"   Call {i}: {call_id}")
                
                # Monitor the first call for summary (batch calls typically have same outcome)
                if call_ids:
                    print(f"\n📡 Monitoring first call for summary...")
                    call_data = wait_for_call_completion(call_ids[0])
                    if call_data:
                        print(f"\n✅ CALL MONITORING COMPLETED!")
                        print(f"📊 Final Status: {call_data.get('status', 'unknown')}")
                        print(f"📋 End Reason: {call_data.get('endedReason', 'unknown')}")
                        print(f"💰 Cost: ${call_data.get('cost', 0):.4f}")
                        print(f"⏱️ Duration: {call_data.get('duration', 0)} seconds")
                        
                        # Show VAPI analysis results
                        analysis = call_data.get('analysis', {})
                        if analysis:
                            print(f"\n📝 VAPI CALL ANALYSIS RESULTS:")
                            print("=" * 50)
                            
                            # Summary
                            summary = analysis.get('summary', '')
                            if summary:
                                print(f"📋 Summary:")
                                print("-" * 30)
                                print(summary)
                                print("-" * 30)
                            
                            # Structured Data
                            structured_data = analysis.get('structuredData', {})
                            if structured_data:
                                print(f"\n📊 Structured Data:")
                                print("-" * 30)
                                print(structured_data)
                                print("-" * 30)
                            
                            # Success Evaluation
                            success_evaluation = analysis.get('successEvaluation', '')
                            if success_evaluation:
                                print(f"\n🎯 Success Evaluation:")
                                print("-" * 30)
                                print(success_evaluation)
                                print("-" * 30)
                        
                        # Show transcript if available
                        transcript = call_data.get('transcript', '')
                        if transcript:
                            print(f"\n💬 Call Transcript:")
                            print("-" * 40)
                            print(transcript)
                            print("-" * 40)
                        
                        # Return result with call_data for analysis
                        return {
                            'success': True,
                            'call_ids': call_ids,
                            'call_data': call_data,
                            'result': result
                        }
            
            return {
                'success': True,
                'call_ids': call_ids,
                'result': result
            }
        else:
            print(f"❌ Batch call failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error making batch call: {e}")
        return None

def update_call_status_in_sheet(customers, status="Calling"):
    """
    Update call status in Smartsheet for the customers
    """
    try:
        print(f"📝 Updating call status to '{status}' for {len(customers)} customers...")
        
        # Get the sheet
        sheet = smart.Sheets.get_sheet(cancellation_dev_sheet_id)
        
        # Find Call Status column
        call_status_col = None
        for col in sheet.columns:
            if col.title == "Call Status":
                call_status_col = col.id
                break
        
        if not call_status_col:
            print("❌ Call Status column not found")
            return False
        
        # Prepare rows to update
        rows_to_update = []
        
        for customer in customers:
            # Find the row by row number
            for row in sheet.rows:
                if row.row_number == customer['row_number']:
                    # Create updated cell
                    new_cell = smart.models.Cell()
                    new_cell.column_id = call_status_col
                    new_cell.value = status
                    
                    # Create updated row
                    updated_row = smart.models.Row()
                    updated_row.id = row.id
                    updated_row.cells.append(new_cell)
                    
                    rows_to_update.append(updated_row)
                    break
        
        if rows_to_update:
            # Update rows in batch
            result = smart.Sheets.update_rows(cancellation_dev_sheet_id, rows_to_update)
            print(f"✅ Updated {len(rows_to_update)} rows in Smartsheet")
            return True
        else:
            print("❌ No rows to update")
            return False
            
    except Exception as e:
        print(f"❌ Error updating call status: {e}")
        return False

def update_call_result_in_smartsheet(customer_info, call_data):
    """
    Update the Call Result column in Smartsheet with detailed VAPI analysis
    """
    try:
        print(f"\n📝 UPDATING SMARTSHEET WITH DETAILED CALL RESULTS")
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
            print(f"📝 Updated value: {call_result}")
            return True
        else:
            print(f"❌ Failed to update Smartsheet: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating Smartsheet: {e}")
        return False

def auto_batch_call():
    """
    Automatically call all customers with "Not call yet" status
    """
    print("🤖 AUTO BATCH CALL SYSTEM")
    print("=" * 60)
    print("Automatically calling all 'Not call yet' customers")
    print("Using Spencer: Call Transfer V2 Campaign assistant")
    print("=" * 60)
    
    # Get customers with "Not call yet" status
    customers = get_not_called_customers()
    
    if not customers:
        print("❌ No customers found with 'Not call yet' status")
        return False
    
    print(f"\n📊 Found {len(customers)} customers to call:")
    print("-" * 50)
    for i, customer in enumerate(customers, 1):
        print(f" {i:2d}. {customer.get('insured', 'Unknown')} - {customer['phone_number']} - {customer['policy_number']}")
    
    print(f"\n⚠️  WARNING: This will make {len(customers)} phone calls!")
    print(f"💰 This will incur charges for each call")
    print(f"🏢 All calls will show caller ID: +1 (951) 247-2003")
    print(f"\n🚀 Starting batch call in 3 seconds...")
    
    # Countdown
    for i in range(3, 0, -1):
        print(f"   {i}...")
        time.sleep(1)
    
    print(f"\n🔥 INITIATING BATCH CALL!")
    
    # Update status to "Calling"
    update_call_status_in_sheet(customers, "Calling")
    
    # Make batch call
    result = make_batch_vapi_call(customers, schedule_immediately=True)
    
    if result and result.get('success'):
        print(f"\n✅ BATCH CALL INITIATED SUCCESSFULLY!")
        print(f"📊 Call monitoring and detailed analysis completed")
        
        # Update call status
        update_call_status_in_sheet(customers, "Called")
        
        # Update call result with detailed analysis for all customers
        if 'call_ids' in result and customers:
            print(f"\n📝 Updating Call Result for all customers...")
            
            # Get detailed call data for each customer
            for i, customer in enumerate(customers):
                if i < len(result['call_ids']):
                    call_id = result['call_ids'][i]
                    print(f"\n📞 Getting call details for {customer.get('insured', 'Unknown')} (Call ID: {call_id})")
                    
                    # Get detailed call information
                    call_details = check_call_status(call_id)
                    
                    if call_details:
                        print(f"✅ Got call details for {customer.get('insured', 'Unknown')}")
                        # Update Smartsheet with detailed analysis
                        update_call_result_in_smartsheet(customer, call_details)
                    else:
                        print(f"❌ Failed to get call details for {customer.get('insured', 'Unknown')}")
                        
                    # Add delay to avoid rate limiting
                    time.sleep(1)
        
        print(f"\n🎉 BATCH CALL COMPLETED!")
        print(f"📞 {len(customers)} customers have been called")
        print(f"📊 Detailed analysis completed and updated to Smartsheet")
        
        return True
    else:
        print(f"\n❌ BATCH CALL FAILED!")
        print(f"💡 Check the error messages above for details")
        
        # Revert status back to "Not call yet"
        print(f"\n📝 Reverting status back to 'Not call yet'...")
        update_call_status_in_sheet(customers, "Not call yet")
        
        return False

if __name__ == "__main__":
    auto_batch_call()
