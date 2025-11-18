"""
CL1 Project - Cancellation Workflow
Multi-Stage Batch Calling Workflows - Weekend-Aware with Stage-Specific Assistants
Implements 3-stage calling system with business day calculations

Note: This workflow is part of the CL1 Project (Cancellation workflow).
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from services import VAPIService, SmartsheetService
from config import (
    CANCELLATION_SHEET_ID,
    CANCELLATION_1ST_REMINDER_ASSISTANT_ID,
    CANCELLATION_2ND_REMINDER_ASSISTANT_ID,
    CANCELLATION_3RD_REMINDER_ASSISTANT_ID
)
import math


# ========================================
# Business Day Calculation Functions
# ========================================

def is_weekend(date):
    """Check if a date falls on weekend"""
    return date.weekday() >= 5  # 5=Saturday, 6=Sunday


def count_business_days(start_date, end_date):
    """
    Count business days between two dates (excluding weekends)
    Includes both start_date and end_date in the count

    Args:
        start_date: Starting date
        end_date: Ending date

    Returns:
        int: Number of business days (inclusive of both dates)
    """
    business_days = 0
    current_date = start_date

    while current_date <= end_date:
        if not is_weekend(current_date):
            business_days += 1
        current_date += timedelta(days=1)

    return business_days


def add_business_days(start_date, number_of_business_days):
    """
    Add business days to a date (skipping weekends)
    
    Args:
        start_date: Starting date
        number_of_business_days: Number of business days to add
    
    Returns:
        date: Resulting date (guaranteed to be a business day)
    """
    current_date = start_date
    added_days = 0
    
    while added_days < number_of_business_days:
        current_date += timedelta(days=1)
        
        if not is_weekend(current_date):
            added_days += 1
    
    return current_date


def parse_date(date_str):
    """Parse date string to datetime object"""
    if isinstance(date_str, datetime):
        return date_str.date()
    
    if not date_str:
        return None
    
    # Try multiple date formats
    formats = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%m/%d/%y',
        '%Y/%m/%d'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(str(date_str).strip(), fmt).date()
        except ValueError:
            continue
    
    return None


# ========================================
# Data Validation and Filtering
# ========================================

def should_skip_row(customer):
    """
    Check if a row should be skipped based on initial validation rules

    Skip if ANY of:
    - company is empty
    - amount_due is empty
    - cancellation_date is empty
    - done is checked/true
    - cancellation_date is not after f_u_date

    Args:
        customer: Customer dict

    Returns:
        tuple: (should_skip: bool, reason: str)
    """
    # Check done checkbox
    if customer.get('done?') in [True, 'true', 'True', 1]:
        return True, "Done checkbox is checked"

    # Check required fields
    if not customer.get('company', '').strip():
        return True, "Company is empty"

    if not customer.get('amount_due', '').strip():
        return True, "Amount Due is empty"

    if not customer.get('cancellation_date', '').strip():
        return True, "Cancellation Date is empty"

    # Check date relationship: cancellation_date must be after f_u_date
    f_u_date_str = customer.get('f_u_date', '').strip()
    cancellation_date_str = customer.get('cancellation_date', '').strip()

    if f_u_date_str and cancellation_date_str:
        f_u_date = parse_date(f_u_date_str)
        cancellation_date = parse_date(cancellation_date_str)

        if f_u_date and cancellation_date:
            if cancellation_date <= f_u_date:
                return True, f"Cancellation Date ({cancellation_date}) is not after F/U Date ({f_u_date})"

    return False, ""


def get_call_stage(customer):
    """
    Get the current call stage for a customer
    
    Returns:
        int: Stage number (0 for empty/null, 1, 2, 3+)
    """
    stage = customer.get('ai_call_stage', '')
    
    if not stage or stage == '' or stage is None:
        return 0
    
    try:
        return int(stage)
    except (ValueError, TypeError):
        return 0


def get_assistant_id_for_stage(stage):
    """Get the appropriate assistant ID for a given call stage"""
    assistant_map = {
        0: CANCELLATION_1ST_REMINDER_ASSISTANT_ID,
        1: CANCELLATION_2ND_REMINDER_ASSISTANT_ID,
        2: CANCELLATION_3RD_REMINDER_ASSISTANT_ID
    }

    return assistant_map.get(stage)


# ========================================
# Follow-up Date Calculation
# ========================================

def calculate_next_followup_date(customer, current_stage):
    """
    Calculate the next follow-up date based on current stage
    
    Args:
        customer: Customer dict
        current_stage: Current call stage (0, 1, or 2)
    
    Returns:
        date or None: Next follow-up date
    """
    followup_date_str = customer.get('f_u_date', '')
    cancellation_date_str = customer.get('cancellation_date', '')
    
    followup_date = parse_date(followup_date_str)
    cancellation_date = parse_date(cancellation_date_str)
    
    if not followup_date or not cancellation_date:
        print(f"   ⚠️  Invalid dates: followup={followup_date}, cancellation={cancellation_date}")
        return None
    
    if current_stage == 0:
        # After 1st call: Calculate 1/3 of total business days
        total_business_days = count_business_days(followup_date, cancellation_date)
        target_days = round(total_business_days / 3.0)
        
        if target_days < 1:
            target_days = 1
        
        next_date = add_business_days(followup_date, target_days)
        
        print(f"   📅 Stage 0→1: Total {total_business_days} business days, adding {target_days} days")
        print(f"      From {followup_date} → {next_date}")
        
        return next_date
    
    elif current_stage == 1:
        # After 2nd call: Calculate 1/2 of remaining business days
        remaining_business_days = count_business_days(followup_date, cancellation_date)
        target_days = round(remaining_business_days / 2.0)
        
        if target_days < 1:
            target_days = 1
        
        next_date = add_business_days(followup_date, target_days)
        
        print(f"   📅 Stage 1→2: Remaining {remaining_business_days} business days, adding {target_days} days")
        print(f"      From {followup_date} → {next_date}")
        
        return next_date
    
    elif current_stage == 2:
        # After 3rd call: No more follow-ups
        print(f"   📅 Stage 2→3: Final call - no more follow-ups")
        return None
    
    return None


# ========================================
# Main Workflow Functions
# ========================================

def get_customers_ready_for_calls(smartsheet_service):
    """
    Get all customers ready for calls today based on stage logic

    Returns:
        dict: Customers grouped by stage {0: [...], 1: [...], 2: [...]}
    """
    print("=" * 80)
    print("🔍 FETCHING CUSTOMERS READY FOR CALLS")
    print("=" * 80)

    # Get all customers from sheet
    all_customers = smartsheet_service.get_all_customers_with_stages()

    # Use Pacific Time for "today" to ensure consistent behavior across environments
    pacific_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific_tz).date()
    print(f"📅 Today (Pacific Time): {today}")

    customers_by_stage = {0: [], 1: [], 2: []}
    skipped_count = 0
    
    for customer in all_customers:
        # Initial validation
        should_skip, skip_reason = should_skip_row(customer)
        if should_skip:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: {skip_reason}")
            continue
        
        # Get current stage
        stage = get_call_stage(customer)
        
        # Skip if stage >= 3 (call sequence complete)
        if stage >= 3:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: Call sequence complete (stage {stage})")
            continue
        
        # Check f_u_date (Follow-up Date)
        followup_date_str = customer.get('f_u_date', '')

        # For stage 0, f_u_date must not be empty
        if stage == 0 and not followup_date_str.strip():
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: Stage 0 requires F/U Date")
            continue

        # Parse f_u_date
        followup_date = parse_date(followup_date_str)

        if not followup_date:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: Invalid F/U Date")
            continue

        # Check if f_u_date == today
        if followup_date == today:
            customers_by_stage[stage].append(customer)
            print(f"   ✅ Row {customer.get('row_number')}: Stage {stage}, ready for call")
    
    print(f"\n📊 Summary:")
    print(f"   Stage 0 (1st call): {len(customers_by_stage[0])} customers")
    print(f"   Stage 1 (2nd call): {len(customers_by_stage[1])} customers")
    print(f"   Stage 2 (3rd call): {len(customers_by_stage[2])} customers")
    print(f"   Skipped: {skipped_count} rows")
    print(f"   Total ready: {sum(len(v) for v in customers_by_stage.values())}")
    
    return customers_by_stage


def format_call_entry(summary, evaluation, call_number):
    """Format a call entry for appending"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entry = f"[Call {call_number} - {timestamp}]\n{summary}\n"
    eval_entry = f"[Call {call_number} - {timestamp}]\n{evaluation}\n"
    return entry, eval_entry


def update_after_call(smartsheet_service, customer, call_data, current_stage):
    """
    Update Smartsheet after a successful call

    Args:
        smartsheet_service: SmartsheetService instance
        customer: Customer dict
        call_data: Call result data from VAPI
        current_stage: Current stage (0, 1, or 2)
    """
    # Extract call analysis
    analysis = call_data.get('analysis', {})
    summary = analysis.get('summary', 'No summary available')

    # Get evaluation with fallback to structured data
    evaluation = analysis.get('successEvaluation')
    if not evaluation:
        # Try to get from structured data
        structured_data = analysis.get('structuredData', {})
        if structured_data:
            evaluation = structured_data.get('success', 'N/A')
        else:
            evaluation = 'N/A'

    evaluation = str(evaluation).lower()  # Normalize to lowercase for consistency

    # Determine new stage
    new_stage = current_stage + 1

    # Calculate next followup date (None for stage 3)
    next_followup_date = calculate_next_followup_date(customer, current_stage)

    # Determine if done (only for stage 3)
    # mark_done = (new_stage >= 3)  # Commented out - wait for manual verification

    # Format entries for appending
    call_number = current_stage + 1
    summary_entry, eval_entry = format_call_entry(summary, evaluation, call_number)

    # Get existing values
    existing_summary = customer.get('ai_call_summary', '')
    existing_eval = customer.get('ai_call_eval', '')

    # Append or create
    if existing_summary:
        new_summary = existing_summary + "\n---\n" + summary_entry
    else:
        new_summary = summary_entry

    if existing_eval:
        new_eval = existing_eval + "\n---\n" + eval_entry
    else:
        new_eval = eval_entry

    # Update fields
    updates = {
        'ai_call_stage': new_stage,
        'ai_call_summary': new_summary,
        'ai_call_eval': new_eval,
        # 'done?': mark_done  # Commented out - wait for manual verification
    }

    if next_followup_date:
        updates['f_u_date'] = next_followup_date.strftime('%Y-%m-%d')

    # Perform update
    success = smartsheet_service.update_customer_fields(customer, updates)

    if success:
        print(f"✅ Smartsheet updated successfully")
        print(f"   • Stage: {current_stage} → {new_stage}")
        # print(f"   • Done: {mark_done}")  # Commented out - wait for manual verification
        if next_followup_date:
            print(f"   • Next F/U Date: {next_followup_date}")
    else:
        print(f"❌ Smartsheet update failed")

    return success


def run_multi_stage_batch_calling(test_mode=False, schedule_at=None, auto_confirm=False):
    """
    Main function to run multi-stage batch calling

    Args:
        test_mode: If True, skip actual calls and Smartsheet updates (default: False)
        schedule_at: Optional datetime to schedule calls (e.g., today at 4 PM)
                    If None, calls are made immediately
        auto_confirm: If True, skip user confirmation prompt (for cron jobs) (default: False)
    """
    print("=" * 80)
    print("🚀 CL1 PROJECT - MULTI-STAGE BATCH CALLING SYSTEM")
    if test_mode:
        print("🧪 TEST MODE - No actual calls or updates will be made")
    if schedule_at:
        print(f"⏰ SCHEDULED MODE - Calls will be scheduled for {schedule_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("📋 CL1 Project: Weekend-aware with stage-specific assistants")
    print("📞 3-stage calling: 1st Reminder → 2nd Reminder → Final Reminder")
    print("=" * 80)
    
    # Initialize services
    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
    vapi_service = VAPIService()
    
    # Get customers grouped by stage
    customers_by_stage = get_customers_ready_for_calls(smartsheet_service)
    
    total_customers = sum(len(v) for v in customers_by_stage.values())
    
    if total_customers == 0:
        print("\n✅ No customers ready for calls today")
        return True
    
    # Show summary and ask for confirmation
    print(f"\n{'=' * 80}")
    print(f"📊 CUSTOMERS READY FOR CALLS TODAY:")
    print(f"{'=' * 80}")
    
    for stage, customers in customers_by_stage.items():
        if customers:
            stage_name = ["1st", "2nd", "3rd"][stage]
            assistant_id = get_assistant_id_for_stage(stage)
            print(f"\n🔔 Stage {stage} ({stage_name} Reminder) - {len(customers)} customers:")
            print(f"   🤖 Assistant ID: {assistant_id}")
            
            for i, customer in enumerate(customers[:5], 1):
                print(f"   {i}. {customer.get('company', 'Unknown')} - {customer.get('phone_number')}")
            
            if len(customers) > 5:
                print(f"   ... and {len(customers) - 5} more")
    
    print(f"\n{'=' * 80}")
    if not test_mode:
        print(f"⚠️  WARNING: This will make {total_customers} phone calls!")
        print(f"💰 This will incur charges for each call")
    else:
        print(f"🧪 TEST MODE: Will simulate {total_customers} calls (no charges)")
    print(f"{'=' * 80}")

    # Only ask for confirmation if not auto_confirm and not test_mode
    if not test_mode and not auto_confirm:
        response = input(f"\nProceed with multi-stage batch calling? (y/N): ").strip().lower()

        if response not in ['y', 'yes']:
            print("❌ Batch calling cancelled")
            return False
    elif auto_confirm:
        print(f"🤖 AUTO-CONFIRM: Proceeding automatically (cron mode)")
    
    # Process each stage
    total_success = 0
    total_failed = 0

    for stage in [0, 1, 2]:
        customers = customers_by_stage[stage]

        if not customers:
            continue

        stage_name = ["1st", "2nd", "3rd"][stage]
        assistant_id = get_assistant_id_for_stage(stage)

        print(f"\n{'=' * 80}")
        print(f"📞 CALLING STAGE {stage} ({stage_name} Reminder) - {len(customers)} customers")
        print(f"🤖 Using Assistant: {assistant_id}")
        print(f"{'=' * 80}")

        if test_mode:
            # Test mode: Simulate calls without actual API calls
            print(f"\n🧪 TEST MODE: Simulating {len(customers)} calls...")
            for customer in customers:
                print(f"   ✅ [SIMULATED] Would call: {customer.get('company', 'Unknown')} - {customer.get('phone_number')}")
                total_success += 1
        else:
            # Stage 0: Batch calling (all customers simultaneously)
            if stage == 0:
                print(f"📦 Batch calling mode (simultaneous)")
                results = vapi_service.make_batch_call_with_assistant(
                    customers,
                    assistant_id,
                    schedule_immediately=(schedule_at is None),
                    schedule_at=schedule_at
                )

                if results:
                    print(f"\n✅ Stage {stage} batch calls completed")

                    # Only update Smartsheet if calls were immediate (not scheduled)
                    if schedule_at is None:
                        # Check if results length matches customers length
                        if len(results) != len(customers):
                            print(f"   ⚠️  Warning: Results count ({len(results)}) doesn't match customers count ({len(customers)})")
                        
                        for i, customer in enumerate(customers):
                            # Get corresponding call_data (handle different result structures)
                            if i < len(results):
                                call_data = results[i]
                            else:
                                # If results length doesn't match, try to get from first result
                                call_data = results[0] if results else None
                            
                            if call_data:
                                # Check if analysis exists, try to refresh if missing
                                if 'analysis' not in call_data or not call_data.get('analysis'):
                                    print(f"   ⚠️  Customer {i+1} ({customer.get('company', 'Unknown')}): No analysis in call_data")
                                    print(f"      Call data keys: {list(call_data.keys())}")
                                    # Try to refresh call status to get analysis
                                    if 'id' in call_data:
                                        call_id = call_data['id']
                                        print(f"      Attempting to refresh call status for call_id: {call_id}")
                                        try:
                                            refreshed_data = vapi_service.check_call_status(call_id)
                                            if refreshed_data and refreshed_data.get('analysis'):
                                                call_data = refreshed_data
                                                print(f"      ✅ Successfully retrieved analysis from refreshed call status")
                                            else:
                                                print(f"      ⚠️  Refreshed call status also has no analysis")
                                        except Exception as e:
                                            print(f"      ❌ Failed to refresh call status: {e}")
                                
                                # Try to update Smartsheet
                                try:
                                    success = update_after_call(smartsheet_service, customer, call_data, stage)
                                    if success:
                                        total_success += 1
                                    else:
                                        print(f"   ❌ Failed to update Smartsheet for {customer.get('company', 'Unknown')}")
                                        total_failed += 1
                                except Exception as e:
                                    print(f"   ❌ Exception updating Smartsheet for {customer.get('company', 'Unknown')}: {e}")
                                    import traceback
                                    traceback.print_exc()
                                    total_failed += 1
                            else:
                                print(f"   ❌ No call data for customer {i+1} ({customer.get('company', 'Unknown')})")
                                total_failed += 1
                    else:
                        print(f"   ⏰ Calls scheduled - Smartsheet will be updated after calls complete")
                        total_success += len(customers)
                else:
                    print(f"\n❌ Stage {stage} batch calls failed")
                    total_failed += len(customers)

            # Stage 1 & 2: Sequential calling (one customer at a time)
            else:
                print(f"🔄 Sequential calling mode (one at a time)")

                for i, customer in enumerate(customers, 1):
                    print(f"\n   📞 Call {i}/{len(customers)}: {customer.get('company', 'Unknown')}")

                    results = vapi_service.make_batch_call_with_assistant(
                        [customer],  # Only one customer at a time
                        assistant_id,
                        schedule_immediately=(schedule_at is None),
                        schedule_at=schedule_at
                    )

                    if results and results[0]:
                        call_data = results[0]

                        # Only update Smartsheet if calls were immediate (not scheduled)
                        if schedule_at is None:
                            success = update_after_call(smartsheet_service, customer, call_data, stage)
                            if success:
                                total_success += 1
                            else:
                                total_failed += 1
                        else:
                            print(f"      ⏰ Call scheduled - Smartsheet will be updated after call completes")
                            total_success += 1
                    else:
                        print(f"      ❌ Call {i} failed")
                        total_failed += 1

                print(f"\n✅ Stage {stage} sequential calls completed")
    
    # Final summary
    print(f"\n{'=' * 80}")
    print(f"🏁 BATCH CALLING COMPLETE")
    print(f"{'=' * 80}")
    print(f"   ✅ Successful: {total_success}")
    print(f"   ❌ Failed: {total_failed}")
    print(f"   📊 Total: {total_success + total_failed}")
    print(f"{'=' * 80}")
    
    return True


# ========================================
# Entry Point
# ========================================

if __name__ == "__main__":
    import sys

    # Check if test mode is requested
    test_mode = "--test" in sys.argv or "-t" in sys.argv

    run_multi_stage_batch_calling(test_mode=test_mode)
