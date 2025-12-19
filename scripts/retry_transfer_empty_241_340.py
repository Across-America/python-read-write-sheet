"""
Retry calls for rows 241-340 where transfer column is empty
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Fix Windows encoding issue
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import and run
from workflows.stm1 import (
    get_stm1_sheet,
    validate_stm1_customer_data,
    update_after_stm1_call
)
from workflows.stm1_variables import build_stm1_variable_values
from services import VAPIService
from config import STM1_ASSISTANT_ID, STM1_PHONE_NUMBER_ID, STM1_CALLING_START_HOUR, STM1_CALLING_END_HOUR
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time

# Configuration
START_ROW = 241  # Start from row 241 (0-indexed: 241-340)
END_ROW = 341     # End at row 341 (exclusive, so 241-340)
CALL_INTERVAL_SECONDS = 36  # 36 seconds between calls

if __name__ == "__main__":
    print("=" * 80)
    print("📞 RETRY CALLS FOR ROWS 241-340 WITH EMPTY TRANSFER STATUS")
    print("=" * 80)
    print(f"📊 Checking rows {START_ROW}-{END_ROW-1}")
    print(f"🔍 Filtering: transfer column is empty")
    print(f"⏱️  Delay between calls: {CALL_INTERVAL_SECONDS} seconds")
    print("=" * 80)
    print()
    
    # Check current time
    pacific_tz = ZoneInfo("America/Los_Angeles")
    now_pacific = datetime.now(pacific_tz)
    current_hour = now_pacific.hour
    current_minute = now_pacific.minute
    
    print(f"Current time: {now_pacific.strftime('%I:%M %p %Z')}")
    print(f"Calling hours: {STM1_CALLING_START_HOUR}:00 AM - {STM1_CALLING_END_HOUR}:00 PM Pacific Time")
    print()
    
    # Check if current time is within calling hours
    if current_hour < STM1_CALLING_START_HOUR or current_hour >= STM1_CALLING_END_HOUR:
        print(f"❌ Outside calling hours ({STM1_CALLING_START_HOUR}:00 - {STM1_CALLING_END_HOUR}:00 Pacific Time)")
        print(f"   Current time: {now_pacific.strftime('%I:%M %p %Z')}")
        print(f"   STM1 calls can only be made between {STM1_CALLING_START_HOUR}:00 AM and {STM1_CALLING_END_HOUR}:00 PM Pacific Time")
        sys.exit(1)
    
    # Safety check: Stop at 4:50 PM (10 minutes before end time)
    STOP_HOUR = 16  # 4 PM
    STOP_MINUTE = 50  # 4:50 PM
    if current_hour > STOP_HOUR or (current_hour == STOP_HOUR and current_minute >= STOP_MINUTE):
        print(f"❌ Too close to end of calling hours")
        print(f"   Current time: {now_pacific.strftime('%I:%M %p %Z')}")
        print(f"   Calls must stop by 4:50 PM Pacific Time")
        print(f"   Please run again earlier in the day")
        sys.exit(1)
    
    print(f"✅ Current time is within calling hours")
    print()
    
    # Check for auto-confirm flag
    auto_confirm = "--yes" in sys.argv or "-y" in sys.argv
    
    if not auto_confirm:
        # Ask for confirmation
        try:
            response = input(f"Proceed with retry calls for rows {START_ROW}-{END_ROW-1} with empty transfer status? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("❌ Test cancelled")
                sys.exit(0)
        except EOFError:
            # Non-interactive environment, auto-confirm
            print("⚠️  Non-interactive environment detected, auto-confirming...")
            auto_confirm = True
    else:
        print("🤖 Auto-confirm mode enabled")
    
    try:
        # Initialize services
        print("\n" + "=" * 80)
        print("🔧 INITIALIZING SERVICES")
        print("=" * 80)
        smartsheet_service = get_stm1_sheet()
        vapi_service = VAPIService(phone_number_id=STM1_PHONE_NUMBER_ID)
        print(f"✅ Services initialized")
        print(f"   🤖 Assistant ID: {STM1_ASSISTANT_ID}")
        print(f"   📱 Phone Number ID: {STM1_PHONE_NUMBER_ID}")
        
        # Get all customers and filter to rows 241-340
        print("\n" + "=" * 80)
        print(f"🔍 FETCHING CUSTOMERS (ROWS {START_ROW}-{END_ROW-1})")
        print("=" * 80)
        all_customers = smartsheet_service.get_all_customers_with_stages()
        
        # Filter to rows 241-340 (0-indexed: 241-340)
        target_rows = all_customers[START_ROW-1:END_ROW-1]  # Convert to 0-indexed
        print(f"📊 Total customers in sheet: {len(all_customers)}")
        print(f"📊 Checking rows {START_ROW}-{END_ROW-1} ({len(target_rows)} rows)")
        
        # Filter customers where transfer column is empty
        # Check multiple possible column names
        customers_to_retry = []
        for customer in target_rows:
            transfer_status = (
                customer.get('transferred_to_aacs_or_not', '') or 
                customer.get('transfer', '') or 
                customer.get('was_transferred', '') or 
                customer.get('transfer_status', '')
            )
            
            # Consider empty if: None, empty string, or whitespace
            if not transfer_status or str(transfer_status).strip() == '':
                customers_to_retry.append(customer)
        
        print(f"\n📊 Found {len(customers_to_retry)} customers with empty transfer status")
        
        if not customers_to_retry:
            print("✅ No customers found with empty transfer status")
            sys.exit(0)
        
        # Show customers to be called
        print("\n" + "=" * 80)
        print("📋 CUSTOMERS TO RETRY:")
        print("=" * 80)
        for i, customer in enumerate(customers_to_retry, 1):
            company = customer.get('insured_name_', '') or customer.get('insured_name', '') or customer.get('company', 'Unknown')
            phone = customer.get('phone_number', '') or customer.get('contact_phone', '')
            claim = customer.get('claim_number', 'N/A')
            row_num = customer.get('row_number', 'N/A')
            print(f"   {i}. Row {row_num}: {company}")
            print(f"      Phone: {phone}")
            print(f"      Claim: {claim}")
        print("=" * 80)
        
        # Sequential calling (one at a time)
        print("\n" + "=" * 80)
        print("📞 SEQUENTIAL CALLING (ONE AT A TIME)")
        print("=" * 80)
        print(f"⏰ Starting time: {datetime.now(pacific_tz).strftime('%I:%M %p %Z')}")
        estimated_seconds = len(customers_to_retry) * CALL_INTERVAL_SECONDS
        print(f"⏰ Target completion: {(datetime.now(pacific_tz) + timedelta(seconds=estimated_seconds)).strftime('%I:%M %p %Z')}")
        print("=" * 80)
        
        total_success = 0
        total_failed = 0
        total_transferred = 0
        start_time = time.time()
        
        for i, customer in enumerate(customers_to_retry, 1):
            # Check time before each call to ensure we don't continue past 5 PM
            now_pacific = datetime.now(pacific_tz)
            current_hour = now_pacific.hour
            current_minute = now_pacific.minute
            
            # Stop if outside calling hours
            if current_hour >= STM1_CALLING_END_HOUR:
                print(f"\n{'=' * 80}")
                print(f"⏰ CALLING HOURS ENDED")
                print(f"{'=' * 80}")
                print(f"   Current time: {now_pacific.strftime('%I:%M %p %Z')}")
                print(f"   Calling hours end at {STM1_CALLING_END_HOUR}:00 PM Pacific Time")
                print(f"   Stopping calls. Completed {i-1}/{len(customers_to_retry)} calls")
                print(f"{'=' * 80}")
                break
            
            # Stop at 4:50 PM (10 minutes before end time)
            STOP_HOUR = 16  # 4 PM
            STOP_MINUTE = 50  # 4:50 PM
            if current_hour > STOP_HOUR or (current_hour == STOP_HOUR and current_minute >= STOP_MINUTE):
                print(f"\n{'=' * 80}")
                print(f"⏰ STOPPING AT 4:50 PM")
                print(f"{'=' * 80}")
                print(f"   Current time: {now_pacific.strftime('%I:%M %p %Z')}")
                print(f"   Calls must stop by 4:50 PM Pacific Time")
                print(f"   Stopping calls now")
                print(f"   Completed {i-1}/{len(customers_to_retry)} calls")
                print(f"{'=' * 80}")
                break
            
            company = customer.get('insured_name_', '') or customer.get('insured_name', '') or customer.get('company', 'Unknown')
            phone = customer.get('phone_number', '') or customer.get('contact_phone', '')
            row_num = customer.get('row_number', 'N/A')
            
            print(f"\n{'=' * 80}")
            print(f"📞 Call {i}/{len(customers_to_retry)}: Row {row_num} - {company}")
            print(f"   Phone: {phone}")
            print(f"   Time: {now_pacific.strftime('%I:%M %p %Z')}")
            print(f"{'=' * 80}")
            
            # Validate customer
            is_valid, error_msg, validated_data = validate_stm1_customer_data(customer)
            if not is_valid:
                print(f"   ❌ Validation failed: {error_msg}")
                total_failed += 1
                continue
            
            # Merge validated data
            customer_for_call = {**customer, **validated_data}
            
            try:
                # Make single call (one customer at a time)
                print(f"   🚀 Initiating call...")
                results = vapi_service.make_batch_call_with_assistant(
                    [customer_for_call],  # Only one customer at a time
                    STM1_ASSISTANT_ID,
                    schedule_immediately=True,
                    custom_variable_builder=build_stm1_variable_values
                )
                
                if results and results[0]:
                    call_data = results[0]
                    print(f"   ✅ Call completed")
                    
                    # Check if analysis exists, try to refresh if missing
                    if 'analysis' not in call_data or not call_data.get('analysis'):
                        print(f"   ⚠️  No analysis in call_data, attempting to refresh...")
                        if 'id' in call_data:
                            call_id = call_data['id']
                            try:
                                refreshed_data = vapi_service.wait_for_call_completion(call_id)
                                if refreshed_data and refreshed_data.get('analysis'):
                                    call_data = refreshed_data
                                    print(f"      ✅ Successfully retrieved analysis from refreshed call status")
                            except Exception as e:
                                print(f"      ❌ Failed to refresh call status: {e}")
                    
                    # Check transfer status
                    ended_reason = call_data.get('endedReason', '')
                    if ended_reason == 'assistant-forwarded-call':
                        total_transferred += 1
                        print(f"   🔄 Transfer detected!")
                    else:
                        print(f"   📞 No transfer (endedReason: {ended_reason})")
                    
                    # Update Smartsheet
                    try:
                        success = update_after_stm1_call(smartsheet_service, customer, call_data)
                        if success:
                            print(f"   ✅ Smartsheet updated successfully")
                            total_success += 1
                        else:
                            print(f"   ❌ Smartsheet update failed")
                            total_failed += 1
                    except Exception as e:
                        print(f"   ❌ Exception during Smartsheet update: {e}")
                        import traceback
                        traceback.print_exc()
                        total_failed += 1
                else:
                    print(f"   ❌ Call failed - no results returned")
                    total_failed += 1
                    
            except Exception as e:
                print(f"   ❌ Exception during call: {e}")
                import traceback
                traceback.print_exc()
                total_failed += 1
            
            # Add delay between calls
            if i < len(customers_to_retry):
                print(f"\n   ⏳ Waiting {CALL_INTERVAL_SECONDS} seconds before next call...")
                time.sleep(CALL_INTERVAL_SECONDS)
        
        # Final summary
        end_time = time.time()
        elapsed_time = end_time - start_time
        elapsed_minutes = elapsed_time / 60
        
        print("\n" + "=" * 80)
        print("🏁 CALLING COMPLETE")
        print("=" * 80)
        print(f"   ✅ Successful: {total_success}")
        print(f"   ❌ Failed: {total_failed}")
        print(f"   🔄 Transferred: {total_transferred}")
        print(f"   📊 Total: {total_success + total_failed}")
        print(f"   ⏱️  Elapsed time: {elapsed_minutes:.1f} minutes ({elapsed_time:.0f} seconds)")
        print(f"   ⏰ Completion time: {datetime.now(pacific_tz).strftime('%I:%M %p %Z')}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

