"""
Multi-Stage Batch Calling Workflows - Weekend-Aware with Stage-Specific Assistants
Implements 3-stage calling system with business day calculations
"""

from datetime import datetime, timedelta
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
    
    Args:
        start_date: Starting date
        end_date: Ending date
    
    Returns:
        int: Number of business days
    """
    business_days = 0
    current_date = start_date
    
    while current_date < end_date:
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
    followup_date_str = customer.get('followup_date', '')
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
    
    today = datetime.now().date()
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
        
        # Check followup_date
        followup_date_str = customer.get('followup_date', '')
        
        # For stage 0, followup_date must not be empty
        if stage == 0 and not followup_date_str.strip():
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: Stage 0 requires followup_date")
            continue
        
        # Parse followup_date
        followup_date = parse_date(followup_date_str)
        
        if not followup_date:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: Invalid followup_date")
            continue
        
        # Check if followup_date == today
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
    print(f"\n📝 Updating Smartsheet after Stage {current_stage} call...")
    
    # Extract call analysis
    analysis = call_data.get('analysis', {})
    summary = analysis.get('summary', 'No summary available')
    evaluation = str(analysis.get('successEvaluation', 'N/A'))
    
    # Determine new stage
    new_stage = current_stage + 1
    
    # Calculate next followup date (None for stage 3)
    next_followup_date = calculate_next_followup_date(customer, current_stage)
    
    # Determine if done (only for stage 3)
    mark_done = (new_stage >= 3)
    
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
        'done?': mark_done
    }
    
    if next_followup_date:
        updates['f_u_date'] = next_followup_date.strftime('%Y-%m-%d')
    
    # Perform update
    success = smartsheet_service.update_customer_fields(customer, updates)
    
    if success:
        print(f"   ✅ Updated: Stage={new_stage}, Done={mark_done}")
        if next_followup_date:
            print(f"   📅 Next followup: {next_followup_date}")
        else:
            print(f"   🏁 Call sequence complete")
    else:
        print(f"   ❌ Failed to update Smartsheet")
    
    return success


def run_multi_stage_batch_calling():
    """
    Main function to run multi-stage batch calling
    """
    print("=" * 80)
    print("🚀 MULTI-STAGE BATCH CALLING SYSTEM")
    print("=" * 80)
    print("📋 Weekend-aware with stage-specific assistants")
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
    print(f"⚠️  WARNING: This will make {total_customers} phone calls!")
    print(f"💰 This will incur charges for each call")
    print(f"{'=' * 80}")
    
    response = input(f"\nProceed with multi-stage batch calling? (y/N): ").strip().lower()
    
    if response not in ['y', 'yes']:
        print("❌ Batch calling cancelled")
        return False
    
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
        
        # Make calls for this stage
        results = vapi_service.make_batch_call_with_assistant(
            customers, 
            assistant_id,
            schedule_immediately=True
        )
        
        if results:
            print(f"\n✅ Stage {stage} calls initiated successfully")
            
            # Update each customer after call
            for customer, call_data in zip(customers, results):
                if call_data:
                    update_after_call(smartsheet_service, customer, call_data, stage)
                    total_success += 1
                else:
                    total_failed += 1
        else:
            print(f"\n❌ Stage {stage} calls failed")
            total_failed += len(customers)
    
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
    run_multi_stage_batch_calling()
