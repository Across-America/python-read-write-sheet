"""
Renewal/Non-Renewal Workflow - Personal Line Policy Renewal Notifications
Implements renewal calling system with dynamic sheet discovery and configurable timeline
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from services import VAPIService, SmartsheetService
from config import (
    RENEWAL_1ST_REMINDER_ASSISTANT_ID,
    RENEWAL_2ND_REMINDER_ASSISTANT_ID,
    RENEWAL_3RD_REMINDER_ASSISTANT_ID,
    RENEWAL_WORKSPACE_NAME,
    RENEWAL_SHEET_NAME_PATTERN,
    RENEWAL_CALLING_SCHEDULE,
    RENEWAL_CALLING_START_DAY
)
import math


# ========================================
# Business Day Calculation Functions (reused from cancellations)
# ========================================

def is_weekend(date):
    """Check if a date falls on weekend"""
    return date.weekday() >= 5  # 5=Saturday, 6=Sunday


def count_business_days(start_date, end_date):
    """
    Count business days between two dates (excluding weekends)
    Includes both start_date and end_date in the count
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
# Dynamic Sheet Discovery
# ========================================

def get_current_renewal_sheet():
    """
    Dynamically get the current month's renewal sheet
    """
    from datetime import datetime
    
    # Get current month in format "Nov 2024"
    current_month = datetime.now().strftime("%b %Y")
    sheet_name = RENEWAL_SHEET_NAME_PATTERN.format(month_year=current_month)
    
    print(f"🔍 Looking for renewal sheet: '{sheet_name}'")
    
    try:
        smartsheet_service = SmartsheetService(
            sheet_name=sheet_name,
            workspace_name=RENEWAL_WORKSPACE_NAME
        )
        return smartsheet_service
    except ValueError as e:
        print(f"❌ Failed to find renewal sheet: {e}")
        print(f"   Expected name: {sheet_name}")
        print(f"   Workspace: {RENEWAL_WORKSPACE_NAME}")
        raise


# ========================================
# Data Validation and Filtering
# ========================================

def should_skip_renewal_row(customer):
    """
    Check if a renewal row should be skipped based on validation rules
    
    Skip if ANY of:
    - done is checked/true
    - company is empty
    - phone_number is empty
    - policy_expiry_date is empty
    - renewal_status is not 'renewal' or 'non-renewal'
    
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

    if not customer.get('phone_number', '').strip():
        return True, "Phone number is empty"

    if not customer.get('policy_expiry_date', '').strip():
        return True, "Policy expiry date is empty"

    # Check renewal status
    renewal_status = customer.get('renewal_status', '').strip().lower()
    if renewal_status not in ['renewal', 'non-renewal']:
        return True, f"Invalid renewal status: {renewal_status}"

    return False, ""


def get_renewal_stage(customer):
    """
    Get the current renewal call stage for a customer
    
    Returns:
        int: Stage number (0 for empty/null, 1, 2, 3+)
    """
    stage = customer.get('renewal_call_stage', '')
    
    if not stage or stage == '' or stage is None:
        return 0
    
    try:
        return int(stage)
    except (ValueError, TypeError):
        return 0


def get_renewal_assistant_id_for_stage(stage):
    """Get the appropriate assistant ID for a given renewal call stage"""
    # For now, use the same assistant for all stages
    # TODO: Configure different assistants for each stage if needed
    assistant_map = {
        0: RENEWAL_1ST_REMINDER_ASSISTANT_ID,  # 2 weeks before
        1: RENEWAL_2ND_REMINDER_ASSISTANT_ID,  # 1 week before  
        2: RENEWAL_3RD_REMINDER_ASSISTANT_ID,  # 1 day before
        3: RENEWAL_3RD_REMINDER_ASSISTANT_ID   # day of expiry (reuse 3rd)
    }

    return assistant_map.get(stage)


# ========================================
# Renewal Timeline Logic
# ========================================

def is_renewal_ready_for_calling(customer, today):
    """
    Check if a renewal customer is ready for calling based on timeline logic
    
    Args:
        customer: Customer dict
        today: Current date
        
    Returns:
        tuple: (is_ready: bool, reason: str, stage: int)
    """
    # Parse policy expiry date
    expiry_date_str = customer.get('policy_expiry_date', '')
    expiry_date = parse_date(expiry_date_str)
    
    if not expiry_date:
        return False, "Invalid policy expiry date", -1
    
    # Calculate days until expiry
    days_until_expiry = (expiry_date - today).days
    
    # Check if we should stop calling (expired)
    if days_until_expiry < 0:
        return False, f"Policy already expired ({abs(days_until_expiry)} days ago)", -1
    
    # Check if it's the right day of month to start calling
    if today.day < RENEWAL_CALLING_START_DAY:
        return False, f"Not yet calling day (start on day {RENEWAL_CALLING_START_DAY})", -1
    
    # Check if today matches any of the calling schedule days
    for stage, days_before in enumerate(RENEWAL_CALLING_SCHEDULE):
        if days_until_expiry == days_before:
            return True, f"Ready for stage {stage} call ({days_before} days before expiry)", stage
    
    # Check if we're within the calling window but not on a scheduled day
    if days_until_expiry <= max(RENEWAL_CALLING_SCHEDULE):
        return False, f"Within calling window but not on scheduled day (expires in {days_until_expiry} days)", -1
    
    return False, f"Too early to call (expires in {days_until_expiry} days)", -1


# ========================================
# Follow-up Date Calculation for Renewals
# ========================================

def calculate_renewal_next_followup_date(customer, current_stage):
    """
    Calculate the next follow-up date for renewal calls
    Based on the fixed schedule: 14, 7, 1, 0 days before expiry
    
    Args:
        customer: Customer dict
        current_stage: Current call stage (0, 1, 2, or 3)
    
    Returns:
        date or None: Next follow-up date
    """
    expiry_date_str = customer.get('policy_expiry_date', '')
    expiry_date = parse_date(expiry_date_str)
    
    if not expiry_date:
        print(f"   ⚠️  Invalid expiry date: {expiry_date_str}")
        return None
    
    # Fixed schedule: 14, 7, 1, 0 days before expiry
    if current_stage < len(RENEWAL_CALLING_SCHEDULE) - 1:
        next_stage = current_stage + 1
        days_before_expiry = RENEWAL_CALLING_SCHEDULE[next_stage]
        next_date = expiry_date - timedelta(days=days_before_expiry)
        
        stage_names = ["2 weeks before", "1 week before", "1 day before", "day of expiry"]
        print(f"   📅 Stage {current_stage}→{next_stage}: Next call {stage_names[next_stage]} ({next_date})")
        
        return next_date
    else:
        # Final stage - no more follow-ups
        print(f"   📅 Stage {current_stage}: Final call - no more follow-ups")
        return None


# ========================================
# Main Workflow Functions
# ========================================

def get_renewal_customers_ready_for_calls(smartsheet_service):
    """
    Get all renewal customers ready for calls today based on timeline logic
    
    Returns:
        dict: Customers grouped by stage {0: [...], 1: [...], 2: [...], 3: [...]}
    """
    print("=" * 80)
    print("🔍 FETCHING RENEWAL CUSTOMERS READY FOR CALLS")
    print("=" * 80)

    # Get all customers from sheet
    all_customers = smartsheet_service.get_all_customers_with_stages()

    # Use Pacific Time for "today" to ensure consistent behavior
    pacific_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific_tz).date()
    print(f"📅 Today (Pacific Time): {today}")
    print(f"⏰ Calling schedule: {RENEWAL_CALLING_SCHEDULE} days before expiry")
    print(f"📅 Start calling on day: {RENEWAL_CALLING_START_DAY} of each month")

    customers_by_stage = {0: [], 1: [], 2: [], 3: []}  # 4 stages: 14, 7, 1, 0 days before
    skipped_count = 0
    
    for customer in all_customers:
        # Initial validation
        should_skip, skip_reason = should_skip_renewal_row(customer)
        if should_skip:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: {skip_reason}")
            continue
        
        # Get current stage
        current_stage = get_renewal_stage(customer)
        
        # Skip if stage >= 4 (call sequence complete - all 4 calls made)
        if current_stage >= 4:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: Renewal sequence complete (stage {current_stage})")
            continue
        
        # Check if ready for calling based on timeline
        is_ready, ready_reason, target_stage = is_renewal_ready_for_calling(customer, today)
        if not is_ready:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: {ready_reason}")
            continue
        
        # Check if the customer is at the right stage for today's call
        if current_stage != target_stage:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: Wrong stage (current: {current_stage}, needed: {target_stage})")
            continue
        
        customers_by_stage[target_stage].append(customer)
        stage_names = ["2 weeks before", "1 week before", "1 day before", "day of expiry"]
        print(f"   ✅ Row {customer.get('row_number')}: Stage {target_stage} ({stage_names[target_stage]}), ready for renewal call")
    
    print(f"\n📊 Summary:")
    print(f"   Stage 0 (2 weeks before): {len(customers_by_stage[0])} customers")
    print(f"   Stage 1 (1 week before): {len(customers_by_stage[1])} customers")
    print(f"   Stage 2 (1 day before): {len(customers_by_stage[2])} customers")
    print(f"   Stage 3 (day of expiry): {len(customers_by_stage[3])} customers")
    print(f"   Skipped: {skipped_count} rows")
    print(f"   Total ready: {sum(len(v) for v in customers_by_stage.values())}")
    
    return customers_by_stage


def format_renewal_call_entry(summary, evaluation, call_number):
    """Format a renewal call entry for appending"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entry = f"[Renewal Call {call_number} - {timestamp}]\n{summary}\n"
    eval_entry = f"[Renewal Call {call_number} - {timestamp}]\n{evaluation}\n"
    return entry, eval_entry


def update_after_renewal_call(smartsheet_service, customer, call_data, current_stage):
    """
    Update Smartsheet after a successful renewal call
    
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
        structured_data = analysis.get('structuredData', {})
        if structured_data:
            evaluation = structured_data.get('success', 'N/A')
        else:
            evaluation = 'N/A'

    evaluation = str(evaluation).lower()

    # Determine new stage
    new_stage = current_stage + 1

    # Calculate next followup date (None for stage 3)
    next_followup_date = calculate_renewal_next_followup_date(customer, current_stage)

    # Format entries for appending
    call_number = current_stage + 1
    summary_entry, eval_entry = format_renewal_call_entry(summary, evaluation, call_number)

    # Get existing values
    existing_summary = customer.get('renewal_call_summary', '')
    existing_eval = customer.get('renewal_call_eval', '')

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
        'renewal_call_stage': new_stage,
        'renewal_call_summary': new_summary,
        'renewal_call_eval': new_eval,
    }

    if next_followup_date:
        updates['renewal_f_u_date'] = next_followup_date.strftime('%Y-%m-%d')

    # Perform update
    success = smartsheet_service.update_customer_fields(customer, updates)

    if success:
        print(f"✅ Smartsheet updated successfully")
        print(f"   • Stage: {current_stage} → {new_stage}")
        if next_followup_date:
            print(f"   • Next F/U Date: {next_followup_date}")
    else:
        print(f"❌ Smartsheet update failed")

    return success


def run_renewal_batch_calling(test_mode=False, schedule_at=None, auto_confirm=False):
    """
    Main function to run renewal batch calling
    
    Args:
        test_mode: If True, skip actual calls and Smartsheet updates (default: False)
        schedule_at: Optional datetime to schedule calls
        auto_confirm: If True, skip user confirmation prompt (for cron jobs) (default: False)
    """
    print("=" * 80)
    print("🚀 RENEWAL BATCH CALLING SYSTEM")
    if test_mode:
        print("🧪 TEST MODE - No actual calls or updates will be made")
    if schedule_at:
        print(f"⏰ SCHEDULED MODE - Calls will be scheduled for {schedule_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("📋 Renewal/Non-Renewal notifications with dynamic sheet discovery")
    print("📞 3-stage calling: 1st Reminder → 2nd Reminder → Final Reminder")
    print("=" * 80)
    
    try:
        # Initialize services with dynamic sheet discovery
        smartsheet_service = get_current_renewal_sheet()
        vapi_service = VAPIService()
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        return False
    
    # Get customers grouped by stage
    customers_by_stage = get_renewal_customers_ready_for_calls(smartsheet_service)
    
    total_customers = sum(len(v) for v in customers_by_stage.values())
    
    if total_customers == 0:
        print("\n✅ No renewal customers ready for calls today")
        return True
    
    # Show summary and ask for confirmation
    print(f"\n{'=' * 80}")
    print(f"📊 RENEWAL CUSTOMERS READY FOR CALLS TODAY:")
    print(f"{'=' * 80}")
    
    for stage, customers in customers_by_stage.items():
        if customers:
            stage_name = ["1st", "2nd", "3rd"][stage]
            assistant_id = get_renewal_assistant_id_for_stage(stage)
            print(f"\n🔔 Stage {stage} ({stage_name} Renewal Reminder) - {len(customers)} customers:")
            print(f"   🤖 Assistant ID: {assistant_id}")
            
            for i, customer in enumerate(customers[:5], 1):
                print(f"   {i}. {customer.get('company', 'Unknown')} - {customer.get('phone_number')}")
            
            if len(customers) > 5:
                print(f"   ... and {len(customers) - 5} more")
    
    print(f"\n{'=' * 80}")
    if not test_mode:
        print(f"⚠️  WARNING: This will make {total_customers} renewal phone calls!")
        print(f"💰 This will incur charges for each call")
    else:
        print(f"🧪 TEST MODE: Will simulate {total_customers} renewal calls (no charges)")
    print(f"{'=' * 80}")

    # Only ask for confirmation if not auto_confirm and not test_mode
    if not test_mode and not auto_confirm:
        response = input(f"\nProceed with renewal batch calling? (y/N): ").strip().lower()

        if response not in ['y', 'yes']:
            print("❌ Renewal batch calling cancelled")
            return False
    elif auto_confirm:
        print(f"🤖 AUTO-CONFIRM: Proceeding automatically (cron mode)")
    
    # Process each stage (4 stages: 14, 7, 1, 0 days before expiry)
    total_success = 0
    total_failed = 0

    for stage in [0, 1, 2, 3]:
        customers = customers_by_stage[stage]

        if not customers:
            continue

        stage_names = ["2 weeks before", "1 week before", "1 day before", "day of expiry"]
        stage_name = stage_names[stage]
        assistant_id = get_renewal_assistant_id_for_stage(stage)

        print(f"\n{'=' * 80}")
        print(f"📞 RENEWAL CALLING STAGE {stage} ({stage_name}) - {len(customers)} customers")
        print(f"🤖 Using Assistant: {assistant_id}")
        print(f"{'=' * 80}")

        if test_mode:
            # Test mode: Simulate calls without actual API calls
            print(f"\n🧪 TEST MODE: Simulating {len(customers)} renewal calls...")
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
                    print(f"\n✅ Stage {stage} renewal batch calls completed")

                    # Only update Smartsheet if calls were immediate (not scheduled)
                    if schedule_at is None:
                        for customer, call_data in zip(customers, results):
                            if call_data:
                                update_after_renewal_call(smartsheet_service, customer, call_data, stage)
                                total_success += 1
                            else:
                                total_failed += 1
                    else:
                        print(f"   ⏰ Calls scheduled - Smartsheet will be updated after calls complete")
                        total_success += len(customers)
                else:
                    print(f"\n❌ Stage {stage} renewal batch calls failed")
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
                            success = update_after_renewal_call(smartsheet_service, customer, call_data, stage)
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

                print(f"\n✅ Stage {stage} renewal sequential calls completed")
    
    # Final summary
    print(f"\n{'=' * 80}")
    print(f"🏁 RENEWAL BATCH CALLING COMPLETE")
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

    run_renewal_batch_calling(test_mode=test_mode)
