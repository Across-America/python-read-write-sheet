"""
N1 Project - Direct Bill Workflow
Payment Reminder Calls for Direct Billed Policies
3-stage calling: 14 days before, 7 days before, day of (if payment not made)
EFT policies do not need follow-ups

Note: This workflow is part of the N1 Project, based on the renewal sheet.
It handles the same customers as Renewal workflow but based on payment_due_date instead of expiration_date.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from services import VAPIService, SmartsheetService
from config import (
    DIRECT_BILL_1ST_REMAINDER_ASSISTANT_ID,
    DIRECT_BILL_2ND_REMAINDER_ASSISTANT_ID,
    DIRECT_BILL_3RD_REMAINDER_ASSISTANT_ID,
    DIRECT_BILL_CALLING_SCHEDULE,
    CANCELLATION_SHEET_ID  # TODO: Replace with actual Direct Bill sheet ID
)
from workflows.cancellations import (
    is_weekend,
    count_business_days,
    add_business_days,
    parse_date
)
import math


def get_direct_bill_assistant_id_for_stage(stage):
    """
    Get the assistant ID for a given direct bill stage
    
    Assistant sharing:
    - Stage 0 (14 days before) & Stage 1 (7 days before): Shared Assistant
    - Stage 2 (1 day before): Shared with Non-Renewal workflow
    
    Args:
        stage: Stage number (0, 1, or 2)
            - Stage 0: 14 days before payment due (1st Reminder) - shared with Stage 1
            - Stage 1: 7 days before payment due (2nd Reminder) - shared with Stage 0
            - Stage 2: 1 day before payment due (3rd Reminder) - shared with Non-Renewal
    
    Returns:
        str: Assistant ID for the stage
    """
    assistant_map = {
        0: DIRECT_BILL_1ST_REMAINDER_ASSISTANT_ID,  # Shared with Stage 1
        1: DIRECT_BILL_2ND_REMAINDER_ASSISTANT_ID,  # Same as Stage 0 (shared)
        2: DIRECT_BILL_3RD_REMAINDER_ASSISTANT_ID   # Shared with Non-Renewal workflow (1 day before)
    }
    
    return assistant_map.get(stage)


def should_skip_direct_bill_row(customer):
    """
    Check if a direct bill row should be skipped
    
    Only process rows that meet ALL of:
    - payee = "direct billed" (case-insensitive)
    - payment_status = "pending payment" (case-insensitive)
    - renewal / non-renewal = "renewal" (case-insensitive)
    
    Skip if ANY of:
    - done is checked/true
    - company is empty
    - phone_number is empty
    - payment_due_date is empty
    - payee is not "direct billed"
    - payment_status is not "pending payment"
    - renewal / non-renewal is not "renewal"
    
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

    # Check payment due date
    payment_due_date = customer.get('payment_due_date', '') or customer.get('due_date', '')
    if not payment_due_date:
        return True, "Payment due date is empty"

    # Check payee - must be "direct billed"
    payee = str(customer.get('payee', '')).strip().lower()
    if 'direct billed' not in payee and 'directbilled' not in payee.replace(' ', ''):
        return True, f"Payee is not 'direct billed' (Payee: {customer.get('payee', 'N/A')})"

    # Check payment_status - must be "pending payment"
    payment_status = str(customer.get('payment_status', '')).strip().lower()
    if 'pending payment' not in payment_status and 'pendingpayment' not in payment_status.replace(' ', ''):
        return True, f"Payment status is not 'pending payment' (Status: {customer.get('payment_status', 'N/A')})"

    # Check renewal / non-renewal - must be "renewal"
    renewal_field = customer.get('renewal / non-renewal', '') or customer.get('renewal___non-renewal', '')
    renewal_status = str(renewal_field).strip().lower()
    if 'renewal' not in renewal_status or 'non-renewal' in renewal_status or 'non renewal' in renewal_status:
        return True, f"Renewal / Non-Renewal is not 'renewal' (Status: {renewal_field})"
    
    return False, ""


def is_direct_bill_ready_for_calling(customer, today):
    """
    Check if a direct bill customer is ready for calling based on timeline logic
    
    Args:
        customer: Customer dict
        today: Current date
        
    Returns:
        tuple: (is_ready: bool, reason: str, stage: int)
    """
    # Parse payment due date
    payment_due_date_str = customer.get('payment_due_date', '') or customer.get('due_date', '')
    payment_due_date = parse_date(payment_due_date_str)
    
    if not payment_due_date:
        return False, "Invalid payment due date", -1
    
    # Calculate days until payment due
    days_until_due = (payment_due_date - today).days
    
    # Check if payment is overdue (skip if overdue)
    if days_until_due < 0:
        return False, f"Payment overdue by {abs(days_until_due)} days (skip)", -1
    
    # Check if it matches any scheduled day (14, 7, or 1 days before)
    for stage, days_before in enumerate(DIRECT_BILL_CALLING_SCHEDULE):
        if days_until_due == days_before:
            return True, f"Ready for stage {stage} call ({days_before} days before due)", stage
    
    # If within calling window but not on scheduled day
    if days_until_due <= max(DIRECT_BILL_CALLING_SCHEDULE):
        return False, f"Within calling window but not on scheduled day (due in {days_until_due} days)", -1
    
    # Too early
    return False, f"Too early to call (due in {days_until_due} days)", -1


def get_direct_bill_stage(customer):
    """
    Get the current direct bill call stage for a customer
    
    Args:
        customer: Customer dict
        
    Returns:
        int: Current stage (0, 1, or 2), or None if not started
    """
    stage_str = customer.get('direct_bill_call_stage', '') or customer.get('ai_call_stage', '')
    
    if not stage_str:
        return 0  # Start at stage 0
    
    try:
        stage = int(stage_str)
        if stage < 0 or stage > 2:
            return 0  # Reset if invalid
        return stage
    except (ValueError, TypeError):
        return 0  # Default to stage 0


def calculate_direct_bill_next_followup_date(customer, current_stage):
    """
    Calculate the next follow-up date for direct bill calls
    Based on the fixed schedule: 14, 7, 1 days before payment due
    
    Args:
        customer: Customer dict
        current_stage: Current call stage (0, 1, or 2)
    
    Returns:
        date or None: Next follow-up date (None for stage 2/final)
    """
    payment_due_date_str = customer.get('payment_due_date', '') or customer.get('due_date', '')
    payment_due_date = parse_date(payment_due_date_str)
    
    if not payment_due_date:
        print(f"   ⚠️  Invalid payment due date: {payment_due_date_str}")
        return None
    
    # Stage 0 → 1: Next call at 7 days before (from schedule)
    if current_stage == 0:
        next_days_before = DIRECT_BILL_CALLING_SCHEDULE[1]  # 7 days
        next_date = payment_due_date - timedelta(days=next_days_before)
        return next_date
    
    # Stage 1 → 2: Next call at 1 day before (from schedule)
    elif current_stage == 1:
        next_days_before = DIRECT_BILL_CALLING_SCHEDULE[2]  # 1 day before
        next_date = payment_due_date - timedelta(days=next_days_before)
        return next_date
    
    # Stage 2: No more calls
    else:
        return None


def get_direct_bill_customers_ready_for_calls(smartsheet_service):
    """
    Get all direct bill customers ready for calls, grouped by stage
    
    Returns:
        dict: {stage: [customers]} mapping
    """
    print("=" * 80)
    print("🔍 FETCHING DIRECT BILL CUSTOMERS")
    print("=" * 80)

    # Get all customers from sheet
    all_customers = smartsheet_service.get_all_customers_with_stages()

    # Use Pacific Time for "today"
    pacific_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific_tz).date()
    print(f"📅 Today (Pacific Time): {today}")

    customers_by_stage = {0: [], 1: [], 2: []}
    skipped_count = 0
    
    for customer in all_customers:
        # Initial validation
        should_skip, skip_reason = should_skip_direct_bill_row(customer)
        if should_skip:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: {skip_reason}")
            continue
        
        # Check if ready for calling
        is_ready, reason, stage = is_direct_bill_ready_for_calling(customer, today)
        
        if is_ready:
            # Verify stage matches current stage in Smartsheet
            current_stage = get_direct_bill_stage(customer)
            if current_stage == stage:
                customers_by_stage[stage].append(customer)
                print(f"   ✅ Row {customer.get('row_number')}: {reason}")
            elif current_stage < stage:
                # Customer missed earlier stages - allow auto-adjustment (for new workflows)
                print(f"   ⚠️  Row {customer.get('row_number')}: Auto-adjusting stage {current_stage} → {stage} (missed earlier stages)")
                customers_by_stage[stage].append(customer)
                print(f"   ✅ Row {customer.get('row_number')}: {reason}")
            else:
                # Customer already passed this stage - skip
                skipped_count += 1
                print(f"   ⏭️  Skipping row {customer.get('row_number')}: Already past this stage (current: {current_stage}, expected: {stage})")
        else:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: {reason}")
    
    print(f"\n📊 Summary:")
    for stage in [0, 1, 2]:
        print(f"   Stage {stage}: {len(customers_by_stage[stage])} customers")
    print(f"   Skipped: {skipped_count} rows")
    
    return customers_by_stage


def format_direct_bill_call_entry(summary, evaluation, call_number):
    """Format a direct bill call entry for appending"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entry = f"[Direct Bill Call #{call_number} - {timestamp}]\n{summary}\n"
    eval_entry = f"[Direct Bill Call #{call_number} - {timestamp}]\n{evaluation}\n"
    return entry, eval_entry


def update_after_direct_bill_call(smartsheet_service, customer, call_data, current_stage):
    """
    Update Smartsheet after a successful direct bill call
    
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

    # Calculate next followup date (None for stage 2)
    next_followup_date = calculate_direct_bill_next_followup_date(customer, current_stage)

    # Format entries for appending
    call_number = current_stage + 1
    summary_entry, eval_entry = format_direct_bill_call_entry(summary, evaluation, call_number)

    # Get existing values
    existing_summary = customer.get('direct_bill_call_summary', '') or customer.get('ai_call_summary', '')
    existing_eval = customer.get('direct_bill_call_eval', '') or customer.get('ai_call_eval', '')

    # Append or create
    if existing_summary:
        new_summary = existing_summary + "\n---\n" + summary_entry
    else:
        new_summary = summary_entry

    if existing_eval:
        new_eval = existing_eval + "\n---\n" + eval_entry
    else:
        new_eval = eval_entry

    # Prepare updates
    updates = {
        'direct_bill_call_stage': str(new_stage),
        'direct_bill_call_summary': new_summary,
        'direct_bill_call_eval': new_eval,
    }

    # Add follow-up date if not final stage
    if next_followup_date:
        updates['f_u_date'] = next_followup_date.strftime('%Y-%m-%d')
    else:
        # Stage 2 complete - no more calls
        updates['f_u_date'] = ''  # Clear follow-up date

    # Perform update
    success = smartsheet_service.update_customer_fields(customer, updates)

    if success:
        print(f"✅ Smartsheet updated: Stage {current_stage} → {new_stage}")
        if next_followup_date:
            print(f"   📅 Next follow-up: {next_followup_date.strftime('%Y-%m-%d')}")
        else:
            print(f"   ✅ Direct bill calling sequence complete")
    else:
        print(f"❌ Smartsheet update failed")

    return success


def run_direct_bill_batch_calling(test_mode=False, schedule_at=None, auto_confirm=False):
    """
    Main function to run direct bill batch calling workflow
    
    Args:
        test_mode: If True, skip actual calls and Smartsheet updates (default: False)
        schedule_at: Optional datetime to schedule calls
        auto_confirm: If True, skip user confirmation prompt (for cron jobs) (default: False)
    """
    print("=" * 80)
    print("🚀 DIRECT BILL BATCH CALLING SYSTEM")
    if test_mode:
        print("🧪 TEST MODE - No actual calls or updates will be made")
    if schedule_at:
        print(f"⏰ SCHEDULED MODE - Calls will be scheduled for {schedule_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("📋 3-stage calling: 14 days before → 7 days before → Day of (if payment not made)")
    print("⏭️  EFT policies are skipped (no follow-ups needed)")
    print("=" * 80)
    
    # Initialize services
    # TODO: Replace CANCELLATION_SHEET_ID with actual Direct Bill sheet ID
    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
    vapi_service = VAPIService()
    
    # Get customers grouped by stage
    customers_by_stage = get_direct_bill_customers_ready_for_calls(smartsheet_service)
    
    total_customers = sum(len(v) for v in customers_by_stage.values())
    
    if total_customers == 0:
        print("\n✅ No customers ready for direct bill calls today")
        return True
    
    # Show summary and ask for confirmation
    print(f"\n{'=' * 80}")
    print(f"📊 DIRECT BILL CUSTOMERS READY FOR CALLS TODAY:")
    print(f"{'=' * 80}")
    
    for stage, customers in customers_by_stage.items():
        if customers:
            stage_names = {0: "1st Reminder (14 days before)", 1: "2nd Reminder (7 days before)", 2: "3rd Reminder (day of)"}
            print(f"\n   Stage {stage} - {stage_names[stage]}: {len(customers)} customers")
            for i, customer in enumerate(customers[:5], 1):
                payment_due = customer.get('payment_due_date', '') or customer.get('due_date', 'N/A')
                print(f"      {i}. {customer.get('company', 'Unknown')} - Due: {payment_due}")
            if len(customers) > 5:
                print(f"      ... and {len(customers) - 5} more")
    
    print(f"\n{'=' * 80}")
    if not test_mode:
        print(f"⚠️  WARNING: This will make {total_customers} direct bill phone calls!")
        print(f"💰 This will incur charges for each call")
    else:
        print(f"🧪 TEST MODE: Will simulate {total_customers} calls (no charges)")
    print(f"{'=' * 80}")

    # Ask for confirmation
    if not test_mode and not auto_confirm:
        response = input(f"\nProceed with direct bill calling? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ Direct bill calling cancelled")
            return False
    elif auto_confirm:
        print(f"🤖 AUTO-CONFIRM: Proceeding automatically (cron mode)")
    
    # Process calls by stage
    total_success = 0
    total_failed = 0

    for stage, customers in customers_by_stage.items():
        if not customers:
            continue
        
        assistant_id = get_direct_bill_assistant_id_for_stage(stage)
        stage_names = {0: "1st Reminder", 1: "2nd Reminder", 2: "3rd Reminder"}
        
        print(f"\n{'=' * 80}")
        print(f"📞 STAGE {stage} - {stage_names[stage]}")
        print(f"{'=' * 80}")
        print(f"   Customers: {len(customers)}")
        print(f"   Assistant: {assistant_id}")
        
        if test_mode:
            print(f"\n🧪 TEST MODE: Simulating {len(customers)} calls...")
            for customer in customers:
                print(f"   ✅ [SIMULATED] Would call: {customer.get('company', 'Unknown')}")
                total_success += 1
        else:
            # Stage 0: Batch calling (all customers simultaneously)
            if stage == 0:
                print(f"\n🔄 Batch calling mode (all customers simultaneously)")
                
                results = vapi_service.make_batch_call_with_assistant(
                    customers,
                    assistant_id,
                    schedule_immediately=(schedule_at is None),
                    schedule_at=schedule_at
                )

                if results:
                    print(f"\n✅ Stage {stage} batch calls completed")

                    # Update Smartsheet if calls were immediate
                    if schedule_at is None:
                        for customer, call_data in zip(customers, results):
                            if call_data:
                                success = update_after_direct_bill_call(smartsheet_service, customer, call_data, stage)
                                if success:
                                    total_success += 1
                                else:
                                    total_failed += 1
                            else:
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
                            success = update_after_direct_bill_call(smartsheet_service, customer, call_data, stage)
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
    print(f"🏁 DIRECT BILL BATCH CALLING COMPLETE")
    print(f"{'=' * 80}")
    print(f"   ✅ Successful: {total_success}")
    print(f"   ❌ Failed: {total_failed}")
    print(f"   📊 Total: {total_success + total_failed}")
    print(f"{'=' * 80}")
    
    return True


if __name__ == "__main__":
    import sys
    test_mode = "--test" in sys.argv or "-t" in sys.argv
    run_direct_bill_batch_calling(test_mode=test_mode)

