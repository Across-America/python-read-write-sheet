"""
Automated STM1 calling script - runs continuously from 9 AM to 4:50 PM
Calls rows with empty called_times, one at a time with 36 second delay
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
CALL_INTERVAL_SECONDS = 36  # 36 seconds between calls
STOP_HOUR = 16  # 4 PM
STOP_MINUTE = 50  # 4:50 PM

def get_customers_with_empty_called_times(smartsheet_service):
    """Get all customers where called_times is empty or 0"""
    all_customers = smartsheet_service.get_all_customers_with_stages()
    
    customers_to_call = []
    for customer in all_customers:
        # Check called_times - only include if empty or 0
        called_times_str = customer.get('called_times', '') or customer.get('called_time', '') or customer.get('called time', '') or '0'
        try:
            called_times_count = int(str(called_times_str).strip()) if str(called_times_str).strip() else 0
            if called_times_count == 0:
                # Also check if done or recorded
                if customer.get('done?') in [True, 'true', 'True', 1]:
                    continue
                recorded_or_not = customer.get('recorded_or_not', '') or customer.get('recorded or not', '')
                if recorded_or_not in [True, 'true', 'True', 1, 'TRUE']:
                    continue
                
                # Check required fields
                insured_name = customer.get('insured_name_', '') or customer.get('insured_name', '') or customer.get('company', '')
                phone = customer.get('phone_number', '') or customer.get('contact_phone', '')
                if insured_name and phone:
                    customers_to_call.append(customer)
        except (ValueError, TypeError):
            # If parsing fails, treat as 0 (not called yet)
            if customer.get('done?') not in [True, 'true', 'True', 1]:
                recorded_or_not = customer.get('recorded_or_not', '') or customer.get('recorded or not', '')
                if recorded_or_not not in [True, 'true', 'True', 1, 'TRUE']:
                    insured_name = customer.get('insured_name_', '') or customer.get('insured_name', '') or customer.get('company', '')
                    phone = customer.get('phone_number', '') or customer.get('contact_phone', '')
                    if insured_name and phone:
                        customers_to_call.append(customer)
    
    return customers_to_call

if __name__ == "__main__":
    print("=" * 80)
    print("🤖 AUTOMATED STM1 CALLING - EMPTY CALLED_TIMES")
    print("=" * 80)
    print(f"⏰ Running from 9:00 AM to 4:50 PM Pacific Time")
    print(f"⏱️  Delay between calls: {CALL_INTERVAL_SECONDS} seconds")
    print("=" * 80)
    print()
    
    pacific_tz = ZoneInfo("America/Los_Angeles")
    
    # Wait until 9:00 AM if not already past
    now_pacific = datetime.now(pacific_tz)
    current_hour = now_pacific.hour
    current_minute = now_pacific.minute
    
    # Check if we should start
    if current_hour < STM1_CALLING_START_HOUR:
        target_time = now_pacific.replace(hour=STM1_CALLING_START_HOUR, minute=0, second=0, microsecond=0)
        wait_seconds = (target_time - now_pacific).total_seconds()
        print(f"⏰ Current time: {now_pacific.strftime('%I:%M %p %Z')}")
        print(f"⏰ Waiting until 9:00 AM... ({wait_seconds/60:.1f} minutes)")
        if wait_seconds > 0:
            time.sleep(wait_seconds)
    
    # Initialize services
    print("\n" + "=" * 80)
    print("🔧 INITIALIZING SERVICES")
    print("=" * 80)
    smartsheet_service = get_stm1_sheet()
    vapi_service = VAPIService(phone_number_id=STM1_PHONE_NUMBER_ID)
    print(f"✅ Services initialized")
    print(f"   🤖 Assistant ID: {STM1_ASSISTANT_ID}")
    print(f"   📱 Phone Number ID: {STM1_PHONE_NUMBER_ID}")
    
    total_success = 0
    total_failed = 0
    total_transferred = 0
    start_time = time.time()
    
    print("\n" + "=" * 80)
    print("🔄 CONTINUOUS CALLING LOOP")
    print("=" * 80)
    print(f"⏰ Started at: {datetime.now(pacific_tz).strftime('%I:%M %p %Z')}")
    print("=" * 80)
    
    call_count = 0
    
    while True:
        # Check current time
        now_pacific = datetime.now(pacific_tz)
        current_hour = now_pacific.hour
        current_minute = now_pacific.minute
        
        # Stop at 4:50 PM
        if current_hour > STOP_HOUR or (current_hour == STOP_HOUR and current_minute >= STOP_MINUTE):
            print(f"\n{'=' * 80}")
            print(f"⏰ STOPPING AT 4:50 PM")
            print(f"{'=' * 80}")
            print(f"   Current time: {now_pacific.strftime('%I:%M %p %Z')}")
            print(f"   Calls must stop by 4:50 PM Pacific Time")
            break
        
        # Check if within calling hours
        if current_hour < STM1_CALLING_START_HOUR:
            # Wait until 9 AM
            target_time = now_pacific.replace(hour=STM1_CALLING_START_HOUR, minute=0, second=0, microsecond=0)
            wait_seconds = (target_time - now_pacific).total_seconds()
            if wait_seconds > 0:
                print(f"\n⏰ Waiting until 9:00 AM... ({wait_seconds/60:.1f} minutes)")
                time.sleep(min(wait_seconds, 60))  # Check every minute
                continue
        
        # Get customers with empty called_times
        customers_to_call = get_customers_with_empty_called_times(smartsheet_service)
        
        if not customers_to_call:
            print(f"\n✅ No more customers with empty called_times")
            print(f"   Waiting 5 minutes before checking again...")
            time.sleep(300)  # Wait 5 minutes before checking again
            continue
        
        # Get first customer
        customer = customers_to_call[0]
        call_count += 1
        
        company = customer.get('insured_name_', '') or customer.get('insured_name', '') or customer.get('company', 'Unknown')
        phone = customer.get('phone_number', '') or customer.get('contact_phone', '')
        row_num = customer.get('row_number', 'N/A')
        
        print(f"\n{'=' * 80}")
        print(f"📞 Call #{call_count}: Row {row_num} - {company}")
        print(f"   Phone: {phone}")
        print(f"   Time: {now_pacific.strftime('%I:%M %p %Z')}")
        print(f"   Remaining: {len(customers_to_call)} customers with empty called_times")
        print(f"{'=' * 80}")
        
        # Validate customer
        is_valid, error_msg, validated_data = validate_stm1_customer_data(customer)
        if not is_valid:
            print(f"   ❌ Validation failed: {error_msg}")
            total_failed += 1
            time.sleep(CALL_INTERVAL_SECONDS)
            continue
        
        # Merge validated data
        customer_for_call = {**customer, **validated_data}
        
        try:
            # Make single call
            print(f"   🚀 Initiating call...")
            results = vapi_service.make_batch_call_with_assistant(
                [customer_for_call],
                STM1_ASSISTANT_ID,
                schedule_immediately=True,
                custom_variable_builder=build_stm1_variable_values
            )
            
            if results and results[0]:
                call_data = results[0]
                print(f"   ✅ Call completed")
                
                # Check if analysis exists, try to refresh if missing
                if 'analysis' not in call_data or not call_data.get('analysis'):
                    if 'id' in call_data:
                        call_id = call_data['id']
                        try:
                            refreshed_data = vapi_service.wait_for_call_completion(call_id)
                            if refreshed_data and refreshed_data.get('analysis'):
                                call_data = refreshed_data
                        except Exception as e:
                            print(f"      ⚠️  Failed to refresh call status: {e}")
                
                # Check transfer status
                ended_reason = call_data.get('endedReason', '')
                if ended_reason == 'assistant-forwarded-call':
                    total_transferred += 1
                    print(f"   🔄 Transfer detected!")
                
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
                    total_failed += 1
            else:
                print(f"   ❌ Call failed - no results returned")
                total_failed += 1
                
        except Exception as e:
            print(f"   ❌ Exception during call: {e}")
            total_failed += 1
        
        # Wait before next call
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


