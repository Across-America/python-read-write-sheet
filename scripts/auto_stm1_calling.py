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
    if not isinstance(sys.stdout, io.TextIOWrapper):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass
    if not isinstance(sys.stderr, io.TextIOWrapper):
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass

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
    """Get all customers where called_times is empty or 0, sorted by row number (ascending)"""
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
                if not insured_name or not phone:
                    continue
                
                # Skip phone numbers starting with 52 (Mexico country code)
                phone_cleaned = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace(".", "").replace("/", "")
                if phone_cleaned.startswith('+52'):
                    continue
                # If it starts with 52 but has more than 10 digits, it's likely a Mexico number
                if phone_cleaned.startswith('52') and len(phone_cleaned) > 10:
                    continue
                
                customers_to_call.append(customer)
        except (ValueError, TypeError):
            # If parsing fails, treat as 0 (not called yet)
            if customer.get('done?') not in [True, 'true', 'True', 1]:
                recorded_or_not = customer.get('recorded_or_not', '') or customer.get('recorded or not', '')
                if recorded_or_not not in [True, 'true', 'True', 1, 'TRUE']:
                    insured_name = customer.get('insured_name_', '') or customer.get('insured_name', '') or customer.get('company', '')
                    phone = customer.get('phone_number', '') or customer.get('contact_phone', '')
                    if not insured_name or not phone:
                        continue
                    
                    # Skip phone numbers starting with 52 (Mexico country code)
                    phone_cleaned = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace(".", "").replace("/", "")
                    if phone_cleaned.startswith('+52'):
                        continue
                    # If it starts with 52 but has more than 10 digits, it's likely a Mexico number
                    if phone_cleaned.startswith('52') and len(phone_cleaned) > 10:
                        continue
                    
                    customers_to_call.append(customer)
    
    # Sort by row number (ascending) to call from the beginning
    # CRITICAL: Must convert to int for proper numeric sorting
    def get_row_number(customer):
        row_num = customer.get('row_number', 0)
        if row_num is None:
            return 999999  # Put None at the end
        try:
            # Convert to int for proper numeric sorting
            num = int(row_num)
            return num
        except (ValueError, TypeError):
            return 999999  # Put invalid values at the end
    
    # Sort in ascending order (smallest row numbers first)
    customers_to_call.sort(key=get_row_number, reverse=False)
    
    # Debug: Print first few rows to verify sorting
    if customers_to_call:
        first_rows = [c.get('row_number') for c in customers_to_call[:5]]
        last_rows = [c.get('row_number') for c in customers_to_call[-5:]]
        print(f"   [SORT VERIFY] First 5 rows: {first_rows}")
        print(f"   [SORT VERIFY] Last 5 rows: {last_rows}")
        
        # Verify sorting is correct
        row_nums = []
        for c in customers_to_call:
            try:
                row_nums.append(int(c.get('row_number', 0)))
            except:
                pass
        
        if len(row_nums) > 1:
            is_sorted = all(row_nums[i] <= row_nums[i+1] for i in range(len(row_nums)-1))
            if not is_sorted:
                print(f"   [ERROR] Sorting FAILED! List is not in ascending order!")
            else:
                print(f"   [OK] Sorting verified: ascending order (first={row_nums[0]}, last={row_nums[-1]})")
    
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
    
    # Check if running in GitHub Actions
    is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
    
    # Wait until 9:00 AM if not already past
    now_pacific = datetime.now(pacific_tz)
    current_hour = now_pacific.hour
    current_minute = now_pacific.minute
    
    # Check if we should start
    if current_hour < STM1_CALLING_START_HOUR:
        target_time = now_pacific.replace(hour=STM1_CALLING_START_HOUR, minute=0, second=0, microsecond=0)
        wait_seconds = (target_time - now_pacific).total_seconds()
        print(f"⏰ Current time: {now_pacific.strftime('%I:%M %p %Z')}")
        
        # In GitHub Actions, don't wait - just exit if too early
        # The workflow should be scheduled for the correct time
        if is_github_actions:
            print(f"⏰ Too early - GitHub Actions detected. Current time is before {STM1_CALLING_START_HOUR}:00 AM Pacific Time")
            print(f"   Workflow should be scheduled for UTC 16:00 (PDT) or UTC 17:00 (PST) to match 9:00 AM Pacific Time")
            print(f"   Exiting. Will try again at the next scheduled run.")
            sys.exit(0)
        else:
            # Local run: wait until 9 AM
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
            # In GitHub Actions, don't wait - just exit if too early
            if is_github_actions:
                print(f"\n⏰ Too early - GitHub Actions detected. Current time is before {STM1_CALLING_START_HOUR}:00 AM Pacific Time")
                print(f"   Exiting. Will try again at the next scheduled run.")
                break
            else:
                # Local run: wait until 9 AM
                target_time = now_pacific.replace(hour=STM1_CALLING_START_HOUR, minute=0, second=0, microsecond=0)
                wait_seconds = (target_time - now_pacific).total_seconds()
                if wait_seconds > 0:
                    print(f"\n⏰ Waiting until 9:00 AM... ({wait_seconds/60:.1f} minutes)")
                    time.sleep(min(wait_seconds, 60))  # Check every minute
                continue
        
        # Get customers with empty called_times (with error handling)
        try:
            print(f"\n[{now_pacific.strftime('%H:%M:%S')}] Loading customers with empty called_times...")
            customers_to_call = get_customers_with_empty_called_times(smartsheet_service)
            print(f"[{now_pacific.strftime('%H:%M:%S')}] Found {len(customers_to_call)} customers to call")
            
            # Debug: Show first and last few row numbers to verify sorting
            if customers_to_call:
                first_rows = [c.get('row_number') for c in customers_to_call[:5]]
                last_rows = [c.get('row_number') for c in customers_to_call[-5:]]
                print(f"   [SORT CHECK] First 5 rows: {first_rows}")
                print(f"   [SORT CHECK] Last 5 rows: {last_rows}")
        except Exception as e:
            print(f"\n❌ Error loading customers: {e}")
            import traceback
            traceback.print_exc()
            print(f"   Retrying in 60 seconds...")
            time.sleep(60)  # Wait 1 minute before retry
            continue
        
        if not customers_to_call:
            no_customers_count += 1
            print(f"\n✅ No more customers with empty called_times")
            if no_customers_count >= MAX_NO_CUSTOMERS:
                print(f"   No customers found after {MAX_NO_CUSTOMERS} attempts. Exiting.")
                print(f"   Summary: Success={total_success}, Failed={total_failed}, Transferred={total_transferred}")
                break
            print(f"   Waiting 5 minutes before checking again... ({no_customers_count}/{MAX_NO_CUSTOMERS})")
            time.sleep(300)  # Wait 5 minutes before checking again
            continue
        else:
            no_customers_count = 0  # Reset counter when customers found
        
        # Get first customer (should be smallest row number)
        customer = customers_to_call[0]
        row_num = customer.get('row_number', 'N/A')
        print(f"   [CALLING] Next customer: Row {row_num}")
        
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
                if call_id:
                    # Wait for call to complete and analysis to be ready
                    # This ensures call_notes will have complete information
                    max_wait_for_analysis = 120  # Wait up to 2 minutes for analysis
                    analysis_ready = False
                    
                    if call_data.get('status') == 'initiated' or not call_data.get('analysis'):
                        print(f"   ⏳ Waiting for call to complete and analysis to be ready...")
                        try:
                            # Wait for call completion with analysis
                            final_call_data = vapi_service.wait_for_call_completion(
                                call_id,
                                check_interval=5,  # Check every 5 seconds
                                max_wait_time=max_wait_for_analysis
                            )
                            
                            if final_call_data and final_call_data.get('analysis'):
                                call_data = final_call_data
                                analysis_ready = True
                                print(f"   ✅ Call completed with analysis ready")
                            elif final_call_data:
                                # Call completed but analysis not ready yet
                                call_data = final_call_data
                                print(f"   ⚠️  Call completed but analysis not ready yet")
                                
                                # Try a few more times to get analysis
                                for retry in range(3):
                                    time.sleep(10)  # Wait 10 seconds
                                    check_result = vapi_service.check_call_status(call_id)
                                    if check_result and check_result.get('analysis'):
                                        call_data = check_result
                                        analysis_ready = True
                                        print(f"   ✅ Analysis ready after retry {retry + 1}")
                                        break
                        except Exception as e:
                            print(f"      ⚠️  Error waiting for analysis: {e}")
                            print(f"      ⚠️  Continuing with available call_data...")
                            # Continue with available call_data - don't break the loop
                    else:
                        # Call already completed, check if analysis is ready
                        if call_data.get('analysis'):
                            analysis_ready = True
                        else:
                            # Try to get analysis
                            try:
                                check_result = vapi_service.check_call_status(call_id)
                                if check_result and check_result.get('analysis'):
                                    call_data = check_result
                                    analysis_ready = True
                            except:
                                pass
                
                # Check transfer status
                ended_reason = call_data.get('endedReason', '')
                if ended_reason == 'assistant-forwarded-call':
                    total_transferred += 1
                    print(f"   🔄 Transfer detected!")
                
                # Update Smartsheet with call_notes
                # CRITICAL: This must succeed to record that a call was made
                # Now we have waited for analysis, so call_notes should be complete
                try:
                    print(f"   📝 Updating Smartsheet with call results...")
                    success = update_after_stm1_call(smartsheet_service, customer, call_data)
                    if success:
                        if analysis_ready:
                            print(f"   ✅ Smartsheet updated with complete call_notes")
                        else:
                            print(f"   ⚠️  Smartsheet updated but analysis may be incomplete")
                        total_success += 1
                    else:
                        print(f"   ❌ CRITICAL: Smartsheet update returned False")
                        print(f"   ⚠️  Call was made but NOT recorded in Smartsheet!")
                        print(f"   ⚠️  This means:")
                        print(f"      - called_times was NOT incremented")
                        print(f"      - call_notes was NOT updated")
                        print(f"      - Next run will try to call the same customer again")
                        print(f"   ⚠️  Continuing to next call, but this is a serious issue...")
                        total_failed += 1
                except Exception as e:
                    print(f"   ❌ CRITICAL: Exception during Smartsheet update: {e}")
                    print(f"   ⚠️  Call was made but NOT recorded in Smartsheet!")
                    print(f"   ⚠️  This is a serious error - the call will not be tracked!")
                    import traceback
                    traceback.print_exc()
                    total_failed += 1
                    # Don't break - continue to next call, but log the critical error
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


