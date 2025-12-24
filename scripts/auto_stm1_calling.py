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
STOP_MINUTE = 55  # 4:55 PM (must stop before 5 PM)

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
    print(f"⏰ Running from 9:00 AM to 4:55 PM Pacific Time")
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
    loop_count = 0
    no_customers_count = 0
    MAX_NO_CUSTOMERS = 3  # Exit after 3 consecutive empty results
    
    while True:
        loop_count += 1
        
        # Progress indicator every 10 loops
        if loop_count % 10 == 0:
            now_pacific = datetime.now(pacific_tz)
            print(f"\n[{now_pacific.strftime('%H:%M:%S')}] Loop #{loop_count} - Still running...")
            print(f"   Success: {total_success}, Failed: {total_failed}, Transferred: {total_transferred}")
        
        # Check current time
        now_pacific = datetime.now(pacific_tz)
        current_hour = now_pacific.hour
        current_minute = now_pacific.minute
        
        # Stop at 4:55 PM (must stop before 5 PM)
        if current_hour > STOP_HOUR or (current_hour == STOP_HOUR and current_minute >= STOP_MINUTE):
            print(f"\n{'=' * 80}")
            print(f"⏰ STOPPING AT 4:55 PM")
            print(f"{'=' * 80}")
            print(f"   Current time: {now_pacific.strftime('%I:%M %p %Z')}")
            print(f"   Calls must stop by 4:55 PM Pacific Time (before 5 PM)")
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
        
        # Get customers with empty called_times (with error handling)
        try:
            print(f"\n[{now_pacific.strftime('%H:%M:%S')}] Loading customers with empty called_times...")
            print(f"[{now_pacific.strftime('%H:%M:%S')}] Loading all customers from Smartsheet...")
            all_customers = smartsheet_service.get_all_customers_with_stages()
            print(f"[{now_pacific.strftime('%H:%M:%S')}] Loaded {len(all_customers)} total customers")
            
            customers_to_call = get_customers_with_empty_called_times(smartsheet_service)
            print(f"[{now_pacific.strftime('%H:%M:%S')}] Found {len(customers_to_call)} customers to call")
            
            # Debug: Show why customers might be filtered out
            if len(customers_to_call) == 0 and len(all_customers) > 0:
                print(f"[{now_pacific.strftime('%H:%M:%S')}] ⚠️  WARNING: Found 0 customers but {len(all_customers)} total customers exist")
                print(f"[{now_pacific.strftime('%H:%M:%S')}] Debugging first 5 customers...")
                for i, customer in enumerate(all_customers[:5], 1):
                    called_times = customer.get('called_times', '') or customer.get('called_time', '') or customer.get('called time', '')
                    done = customer.get('done?', False)
                    recorded = customer.get('recorded_or_not', '') or customer.get('recorded or not', '')
                    name = customer.get('insured_name_', '') or customer.get('insured_name', '') or customer.get('company', '')
                    phone = customer.get('phone_number', '') or customer.get('contact_phone', '')
                    print(f"   Customer {i}: called_times='{called_times}', done={done}, recorded={recorded}, name={bool(name)}, phone={bool(phone)}")
        except Exception as e:
            print(f"\n❌ Error loading customers: {e}")
            import traceback
            traceback.print_exc()
            print(f"   Retrying in 60 seconds...")
            time.sleep(60)  # Wait 1 minute before retry
            continue
        
        if not customers_to_call:
            no_customers_count += 1
            print(f"\n[{now_pacific.strftime('%H:%M:%S')}] ⚠️  No customers with empty called_times found")
            print(f"[{now_pacific.strftime('%H:%M:%S')}] Attempt {no_customers_count}/{MAX_NO_CUSTOMERS}")
            
            if no_customers_count >= MAX_NO_CUSTOMERS:
                print(f"\n{'=' * 80}")
                print(f"❌ EXITING: No customers found after {MAX_NO_CUSTOMERS} attempts")
                print(f"{'=' * 80}")
                print(f"   Total customers in sheet: {len(all_customers) if 'all_customers' in locals() else 'unknown'}")
                print(f"   Customers to call: 0")
                print(f"   Summary: Success={total_success}, Failed={total_failed}, Transferred={total_transferred}")
                print(f"{'=' * 80}")
                break
            
            print(f"   Waiting 5 minutes before checking again... ({no_customers_count}/{MAX_NO_CUSTOMERS})")
            time.sleep(300)  # Wait 5 minutes before checking again
            continue
        else:
            no_customers_count = 0  # Reset counter when customers found
            print(f"[{now_pacific.strftime('%H:%M:%S')}] ✅ Found {len(customers_to_call)} customers - starting calls...")
        
        # Get first customer
        customer = customers_to_call[0]
        
        # Check time again before initiating call (in case we're close to 4:55 PM)
        now_pacific = datetime.now(pacific_tz)
        current_hour = now_pacific.hour
        current_minute = now_pacific.minute
        
        # Stop if outside calling hours (after 5 PM)
        if current_hour >= STM1_CALLING_END_HOUR:
            print(f"\n{'=' * 80}")
            print(f"⏰ CALLING HOURS ENDED")
            print(f"{'=' * 80}")
            print(f"   Current time: {now_pacific.strftime('%I:%M %p %Z')}")
            print(f"   Calling hours end at {STM1_CALLING_END_HOUR}:00 PM Pacific Time")
            print(f"   Stopping calls. Completed {call_count}/{len(customers_to_call)} calls")
            print(f"{'=' * 80}")
            break
        
        # Stop if too close to end time (4:55 PM or later)
        if current_hour == STM1_CALLING_END_HOUR - 1 and current_minute >= 55:
            print(f"\n{'=' * 80}")
            print(f"⏰ APPROACHING END OF CALLING HOURS")
            print(f"{'=' * 80}")
            print(f"   Current time: {now_pacific.strftime('%I:%M %p %Z')}")
            print(f"   Calling hours end at {STM1_CALLING_END_HOUR}:00 PM Pacific Time")
            print(f"   Stopping calls to ensure completion before end time")
            print(f"   Completed {call_count}/{len(customers_to_call)} calls")
            print(f"{'=' * 80}")
            break
        
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
                custom_variable_builder=build_stm1_variable_values,
                skip_wait=True  # Skip waiting for faster calling
            )
            
            # Handle different return formats
            if isinstance(results, dict):
                # Old format - extract call_data
                call_data = results.get('call_data') or results.get('result', {})
            elif isinstance(results, list) and results:
                # New format - list of call data
                call_data = results[0]
            else:
                call_data = None
            
            if call_data:
                call_id = call_data.get('id', '')
                print(f"   ✅ Call initiated (ID: {call_id[:20] if call_id else 'N/A'}...)")
                
                # For automated calling with skip_wait=True, call_data may be minimal
                # Try to get current status if call_id exists
                if call_id and call_data.get('status') == 'initiated':
                    try:
                        # Quick check - don't wait
                        quick_check = vapi_service.check_call_status(call_id)
                        if quick_check:
                            status = quick_check.get('status', 'unknown')
                            ended_reason = quick_check.get('endedReason', '')
                            print(f"   📊 Call status: {status} ({ended_reason})")
                            
                            # Use quick_check if it has more info
                            if status != 'unknown':
                                call_data = quick_check
                        else:
                            print(f"   ⏳ Call initiated, status will be checked later")
                    except Exception as e:
                        print(f"      ⚠️  Quick check failed: {e}")
                
                # Check transfer status
                ended_reason = call_data.get('endedReason', '')
                if ended_reason == 'assistant-forwarded-call':
                    total_transferred += 1
                    print(f"   🔄 Transfer detected!")
                
                # Update Smartsheet (even without analysis - will update again later)
                try:
                    success = update_after_stm1_call(smartsheet_service, customer, call_data)
                    if success:
                        print(f"   ✅ Smartsheet updated")
                        total_success += 1
                    else:
                        print(f"   ⚠️  Smartsheet update returned False (may retry later)")
                        total_failed += 1
                except Exception as e:
                    print(f"   ❌ Exception during Smartsheet update: {e}")
                    total_failed += 1
            else:
                print(f"   ❌ Call failed - no results returned")
                total_failed += 1
                
        except Exception as e:
            print(f"   ❌ Exception during call: {e}")
            import traceback
            traceback.print_exc()
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


