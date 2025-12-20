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

def get_cancellation_type(customer):
    """
    Determine the cancellation type based on cancellation reason
    
    Returns:
        str: 'general', 'non_payment', or 'other'
    """
    cancellation_reason = str(customer.get('cancellation_reason', '') or customer.get('cancellation reason', '')).strip().lower()
    
    general_reasons = ['uw reason', 'uwreason', 'underwriter declined', 'underwriterdeclined', 'unresponsive insured', 'unresponsiveinsured']
    if any(reason in cancellation_reason for reason in general_reasons):
        return 'general'
    
    if 'non-payment' in cancellation_reason or 'nonpayment' in cancellation_reason.replace('-', '').replace(' ', ''):
        return 'non_payment'
    
    return 'other'


def should_skip_row(customer):
    """
    Check if a row should be skipped based on initial validation rules

    For General cancellation calls (UW Reason, Underwriter Declined, Unresponsive Insured):
    - NO PAYMENT AMOUNT NEEDED
    - expiration_date is required (not cancellation_date)
    - Status must not be "Paid"
    
    For Non-Payment cancellation calls:
    - amount_due is required
    - cancellation_date is required
    - Status must not be "Paid"

    Skip if ANY of:
    - done is checked/true
    - Status is "Paid"
    - For General: expiration_date is empty
    - For Non-Payment: amount_due is empty or cancellation_date is empty
    - For Non-Payment: cancellation_date is not after f_u_date

    Note: Company field is not required (removed validation)

    Args:
        customer: Customer dict

    Returns:
        tuple: (should_skip: bool, reason: str)
    """
    # Check done checkbox
    if customer.get('done?') in [True, 'true', 'True', 1]:
        return True, "Done checkbox is checked"
    
    # Check status - must not be "Paid"
    status = str(customer.get('status', '')).strip().lower()
    if 'paid' in status:
        return True, f"Status is 'Paid' (Status: {customer.get('status', 'N/A')})"
    
    # Determine cancellation type
    cancellation_type = get_cancellation_type(customer)
    
    if cancellation_type == 'general':
        # General cancellation: NO PAYMENT AMOUNT NEEDED, use expiration_date
        expiration_date_str = customer.get('expiration_date', '') or customer.get('expiration date', '')
        if not expiration_date_str.strip():
            return True, "Expiration Date is empty (required for General cancellation)"
        return False, ""
    
    elif cancellation_type == 'non_payment':
        # Non-Payment cancellation: amount_due and cancellation_date required
        if not customer.get('amount_due', '').strip():
            return True, "Amount Due is empty (required for Non-Payment cancellation)"
        
        if not customer.get('cancellation_date', '').strip():
            return True, "Cancellation Date is empty (required for Non-Payment cancellation)"
        
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
    
    else:
        # Other cancellation types: use original logic (require amount_due and cancellation_date)
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
    Calculate the next follow-up date based on current stage and cancellation type
    
    For General cancellation:
    - Stage 0 → Stage 1: 7 days before expiration_date
    - Stage 1 → Stage 2: 3 days before expiration_date
    - Stage 2: Final call - no more follow-ups
    
    For Non-Payment cancellation:
    - Stage 0 → Stage 1: Calculate based on business days (1/3 of remaining)
    - Stage 1 → Stage 2: Calculate based on business days (1/2 of remaining)
    - Stage 2: Final call - no more follow-ups
    
    Args:
        customer: Customer dict
        current_stage: Current call stage (0, 1, or 2)
    
    Returns:
        date or None: Next follow-up date
    """
    cancellation_type = get_cancellation_type(customer)
    
    if cancellation_type == 'general':
        # General cancellation: use expiration_date and calendar days
        expiration_date_str = customer.get('expiration_date', '') or customer.get('expiration date', '')
        expiration_date = parse_date(expiration_date_str)
        
        if not expiration_date:
            print(f"   ⚠️  Invalid expiration date: {expiration_date_str}")
            return None
        
        if current_stage == 0:
            # After 1st call: Next call is 7 days before expiration
            next_date = expiration_date - timedelta(days=7)
            print(f"   📅 Stage 0→1: Next call 7 days before expiration ({next_date})")
            return next_date
        elif current_stage == 1:
            # After 2nd call: Next call is 3 days before expiration
            next_date = expiration_date - timedelta(days=3)
            print(f"   📅 Stage 1→2: Next call 3 days before expiration ({next_date})")
            return next_date
        elif current_stage == 2:
            # After 3rd call: No more follow-ups
            print(f"   📅 Stage 2: Final call - no more follow-ups")
            return None
    
    elif cancellation_type == 'non_payment':
        # Non-Payment cancellation: use cancellation_date and business days
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
            print(f"   📅 Stage 2: Final call - no more follow-ups")
            return None
    
    # Default: use original logic for other types
    followup_date_str = customer.get('f_u_date', '')
    cancellation_date_str = customer.get('cancellation_date', '')
    
    followup_date = parse_date(followup_date_str)
    cancellation_date = parse_date(cancellation_date_str)
    
    if not followup_date or not cancellation_date:
        print(f"   ⚠️  Invalid dates: followup={followup_date}, cancellation={cancellation_date}")
        return None
    
    if current_stage == 0:
        total_business_days = count_business_days(followup_date, cancellation_date)
        target_days = round(total_business_days / 3.0)
        if target_days < 1:
            target_days = 1
        next_date = add_business_days(followup_date, target_days)
        print(f"   📅 Stage 0→1: Total {total_business_days} business days, adding {target_days} days")
        return next_date
    elif current_stage == 1:
        remaining_business_days = count_business_days(followup_date, cancellation_date)
        target_days = round(remaining_business_days / 2.0)
        if target_days < 1:
            target_days = 1
        next_date = add_business_days(followup_date, target_days)
        print(f"   📅 Stage 1→2: Remaining {remaining_business_days} business days, adding {target_days} days")
        return next_date
    elif current_stage == 2:
        print(f"   📅 Stage 2: Final call - no more follow-ups")
        return None
    
    return None


# ========================================
# Main Workflow Functions
# ========================================

def is_general_cancellation_ready_for_calling(customer, today):
    """
    Check if a General cancellation customer is ready for calling
    Uses expiration_date and calendar days (14, 7, 3 days before)
    
    Args:
        customer: Customer dict
        today: Current date
        
    Returns:
        tuple: (is_ready: bool, reason: str, stage: int)
    """
    # Parse expiration date
    expiration_date_str = customer.get('expiration_date', '') or customer.get('expiration date', '')
    expiration_date = parse_date(expiration_date_str)
    
    if not expiration_date:
        return False, "Invalid expiration date", -1
    
    # Calculate days until expiration
    days_until_expiration = (expiration_date - today).days
    
    # Check if expired
    if days_until_expiration < 0:
        return False, f"Policy already expired ({abs(days_until_expiration)} days ago)", -1
    
    # General cancellation schedule: 14 days, 7 days, 3 days before expiration
    general_schedule = [14, 7, 3]
    
    for stage, days_before in enumerate(general_schedule):
        target_date = expiration_date - timedelta(days=days_before)
        
        # If target date is weekend, adjust to previous Friday
        if is_weekend(target_date):
            if target_date.weekday() == 5:  # Saturday
                days_to_friday = 1
            else:  # Sunday
                days_to_friday = 2
            adjusted_target_date = target_date - timedelta(days=days_to_friday)
            
            if today == adjusted_target_date:
                return True, f"Ready for General cancellation stage {stage} call (adjusted from {days_before} days to {adjusted_target_date} - target was {target_date.strftime('%A')})", stage
        else:
            if today == target_date:
                return True, f"Ready for General cancellation stage {stage} call ({days_before} days before expiration)", stage
    
    return False, f"Not ready for General cancellation call (expires in {days_until_expiration} days)", -1


def is_non_payment_cancellation_ready_for_calling(customer, today):
    """
    Check if a Non-Payment cancellation customer is ready for calling
    Uses cancellation_date and business days (14, 7, 1 business days before)
    
    Args:
        customer: Customer dict
        today: Current date
        
    Returns:
        tuple: (is_ready: bool, reason: str, stage: int)
    """
    # Parse cancellation date
    cancellation_date_str = customer.get('cancellation_date', '')
    cancellation_date = parse_date(cancellation_date_str)
    
    if not cancellation_date:
        return False, "Invalid cancellation date", -1
    
    # Calculate business days until cancellation
    business_days_until = count_business_days(today, cancellation_date)
    
    # Check if already cancelled
    if business_days_until < 0:
        return False, f"Policy already cancelled ({abs(business_days_until)} business days ago)", -1
    
    # Non-Payment cancellation schedule: 14, 7, 1 business days before cancellation
    non_payment_schedule = [14, 7, 1]
    
    for stage, business_days_before in enumerate(non_payment_schedule):
        # Calculate target date by going back business days from cancellation_date
        target_date = cancellation_date
        business_days_back = 0
        while business_days_back < business_days_before:
            target_date = target_date - timedelta(days=1)
            if not is_weekend(target_date):
                business_days_back += 1
        
        if today == target_date:
            return True, f"Ready for Non-Payment cancellation stage {stage} call ({business_days_before} business days before cancellation)", stage
    
    return False, f"Not ready for Non-Payment cancellation call ({business_days_until} business days until cancellation)", -1


def get_customers_ready_for_calls(smartsheet_service):
    """
    Get all customers ready for calls today based on cancellation type and stage logic
    
    Handles two types of cancellation calls:
    1. General cancellation (UW Reason, Underwriter Declined, Unresponsive Insured):
       - Uses expiration_date
       - Calendar days: 14, 7, 3 days before expiration
       - NO PAYMENT AMOUNT NEEDED
    
    2. Non-Payment cancellation:
       - Uses cancellation_date
       - Business days: 14, 7, 1 business days before cancellation
       - Requires amount_due

    Returns:
        dict: Customers grouped by type and stage {
            'general': {0: [...], 1: [...], 2: [...]},
            'non_payment': {0: [...], 1: [...], 2: [...]}
        }
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

    customers_by_type_stage = {
        'general': {0: [], 1: [], 2: []},
        'non_payment': {0: [], 1: [], 2: []}
    }
    skipped_count = 0
    
    for customer in all_customers:
        # Initial validation
        should_skip, skip_reason = should_skip_row(customer)
        if should_skip:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: {skip_reason}")
            continue
        
        # Determine cancellation type
        cancellation_type = get_cancellation_type(customer)
        
        if cancellation_type == 'other':
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: Unknown cancellation type")
            continue
        
        # Get current stage
        stage = get_call_stage(customer)
        
        # Skip if stage >= 3 (call sequence complete)
        if stage >= 3:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: Call sequence complete (stage {stage})")
            continue
        
        # Check if ready for calling based on cancellation type
        if cancellation_type == 'general':
            is_ready, reason, target_stage = is_general_cancellation_ready_for_calling(customer, today)
            if is_ready:
                # Check if customer is at the right stage
                if stage == target_stage:
                    customers_by_type_stage['general'][target_stage].append(customer)
                    print(f"   ✅ Row {customer.get('row_number')}: General cancellation Stage {target_stage}, ready for call")
                else:
                    skipped_count += 1
                    print(f"   ⏭️  Skipping row {customer.get('row_number')}: Stage mismatch (current: {stage}, needed: {target_stage})")
            else:
                skipped_count += 1
                print(f"   ⏭️  Skipping row {customer.get('row_number')}: {reason}")
        
        elif cancellation_type == 'non_payment':
            # For Non-Payment, check f_u_date (Follow-up Date) - use existing logic
            followup_date_str = customer.get('f_u_date', '')
            
            if stage == 0 and not followup_date_str.strip():
                skipped_count += 1
                print(f"   ⏭️  Skipping row {customer.get('row_number')}: Stage 0 requires F/U Date")
                continue
            
            followup_date = parse_date(followup_date_str)
            if not followup_date:
                skipped_count += 1
                print(f"   ⏭️  Skipping row {customer.get('row_number')}: Invalid F/U Date")
                continue
            
            # Check if f_u_date == today
            if followup_date == today:
                customers_by_type_stage['non_payment'][stage].append(customer)
                print(f"   ✅ Row {customer.get('row_number')}: Non-Payment cancellation Stage {stage}, ready for call")
            else:
                skipped_count += 1
                print(f"   ⏭️  Skipping row {customer.get('row_number')}: F/U Date ({followup_date}) is not today")
    
    # Flatten to old format for backward compatibility
    customers_by_stage = {0: [], 1: [], 2: []}
    for cancel_type in ['general', 'non_payment']:
        for stage in [0, 1, 2]:
            customers_by_stage[stage].extend(customers_by_type_stage[cancel_type][stage])
    
    print(f"\n📊 Summary:")
    print(f"   General Cancellation:")
    print(f"      Stage 0 (14 days before): {len(customers_by_type_stage['general'][0])} customers")
    print(f"      Stage 1 (7 days before): {len(customers_by_type_stage['general'][1])} customers")
    print(f"      Stage 2 (3 days before): {len(customers_by_type_stage['general'][2])} customers")
    print(f"   Non-Payment Cancellation:")
    print(f"      Stage 0 (14 business days before): {len(customers_by_type_stage['non_payment'][0])} customers")
    print(f"      Stage 1 (7 business days before): {len(customers_by_type_stage['non_payment'][1])} customers")
    print(f"      Stage 2 (1 business day before): {len(customers_by_type_stage['non_payment'][2])} customers")
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
    Uses the same call notes format as N1 project (renewals)

    Args:
        smartsheet_service: SmartsheetService instance
        customer: Customer dict
        call_data: Call result data from VAPI
        current_stage: Current stage (0, 1, or 2)
    """
    # Extract call analysis
    analysis = call_data.get('analysis', {})
    
    # Check if this is a voicemail call
    ended_reason = call_data.get('endedReason', '')
    is_voicemail = (ended_reason == 'voicemail')
    
    summary = analysis.get('summary', '') if analysis else ''
    if not summary or summary == '':
        # Try alternative locations for summary
        if analysis:
            summary = analysis.get('transcript', '') or analysis.get('summaryText', '') or 'No summary available'
        else:
            # If no analysis and it's voicemail, use "Left voicemail" instead of "No summary available"
            if is_voicemail:
                summary = 'Left voicemail'
            else:
                summary = 'No summary available'
        if summary == 'No summary available':
            print(f"⚠️  WARNING: No summary found in analysis")
            print(f"   Analysis keys: {list(analysis.keys()) if analysis else 'N/A'}")

    # Get evaluation with fallback to structured data
    evaluation = analysis.get('successEvaluation')
    if not evaluation:
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

    # Format entries for appending (for ai_call_eval column - keep old format for eval)
    call_number = current_stage + 1
    _, eval_entry = format_call_entry(summary, evaluation, call_number)

    # Get existing values
    existing_eval = customer.get('ai_call_eval', '')

    # Append or create for eval (keep old format)
    if existing_eval:
        new_eval = existing_eval + "\n---\n" + eval_entry
    else:
        new_eval = eval_entry

    # Format call summary for AI Call Summary column (same format as N1 project Call Notes)
    # Required format:
    # Call Placed At: {{start_time}}
    # Did Client Answer: Yes/No
    # Was Full Message Conveyed: Yes/No (Yes = AI reached the transfer question while caller was on the line)
    # Was Voicemail Left: Yes/No
    # analysis:
    # {{summary}}
    
    # Get call start time
    start_time_str = call_data.get('startedAt') or call_data.get('createdAt', '')
    if start_time_str:
        try:
            # Parse ISO format and convert to Pacific Time
            start_time_utc = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            pacific_tz = ZoneInfo("America/Los_Angeles")
            start_time_pacific = start_time_utc.astimezone(pacific_tz)
            call_placed_at = start_time_pacific.strftime('%Y-%m-%d %H:%M:%S')
        except:
            # Fallback to current time if parsing fails
            call_placed_at = datetime.now(ZoneInfo("America/Los_Angeles")).strftime('%Y-%m-%d %H:%M:%S')
    else:
        call_placed_at = datetime.now(ZoneInfo("America/Los_Angeles")).strftime('%Y-%m-%d %H:%M:%S')
    
    # Determine if client answered
    # Client answered if endedReason is NOT: voicemail, customer-did-not-answer, customer-busy, twilio-failed-to-connect-call
    no_answer_reasons = [
        'voicemail',
        'customer-did-not-answer',
        'customer-busy',
        'twilio-failed-to-connect-call',
        'assistant-error'
    ]
    did_client_answer = 'No' if ended_reason in no_answer_reasons else 'Yes'
    
    # Determine if full message was conveyed
    # Full message conveyed = AI reached the transfer question while caller was on the line
    # This means: client answered AND (transfer occurred OR conversation happened)
    was_full_message_conveyed = 'No'
    if did_client_answer == 'Yes':
        # Check if transfer occurred or if there was meaningful conversation
        if ended_reason == 'assistant-forwarded-call':
            was_full_message_conveyed = 'Yes'  # Transfer means full message was conveyed
        elif ended_reason == 'customer-ended-call':
            # Check if there's analysis/summary indicating conversation happened
            if analysis and summary and summary != 'No summary available':
                # If there's a meaningful summary, assume message was conveyed
                was_full_message_conveyed = 'Yes'
            else:
                was_full_message_conveyed = 'No'
        else:
            was_full_message_conveyed = 'No'
    
    # Determine if voicemail was left
    # Check multiple indicators:
    # 1. endedReason == 'voicemail' (explicit voicemail)
    # 2. endedReason == 'customer-did-not-answer' AND there's a transcript (assistant left voicemail)
    # 3. Check transcript for voicemail indicators
    was_voicemail_left = 'No'
    duration = call_data.get('duration', 0) or 0
    
    if is_voicemail:
        was_voicemail_left = 'Yes'
    elif ended_reason == 'customer-did-not-answer':
        # For customer-did-not-answer, check if there's a transcript indicating voicemail was left
        transcript = call_data.get('transcript', '') or (analysis.get('transcript', '') if analysis else '')
        
        # Only mark as voicemail if:
        # 1. There's a transcript (meaning call connected and assistant spoke)
        # 2. Duration > 0 (call actually connected)
        # 3. Transcript contains voicemail-related keywords OR assistant spoke the full message
        if transcript and duration > 0:
            # Check if transcript contains voicemail-related keywords
            transcript_lower = transcript.lower()
            has_voicemail_keywords = any(keyword in transcript_lower for keyword in [
                'voicemail', 'voice mail', 'left a message', 'leaving a message', 
                'message left', 'recording', 'beep'
            ])
            
            # If assistant spoke (has transcript) and call duration > 0, likely left voicemail
            # Check if the transcript shows the assistant completed the message
            if has_voicemail_keywords:
                was_voicemail_left = 'Yes'
            elif len(transcript) > 100:  # If transcript is substantial, assistant likely left voicemail
                was_voicemail_left = 'Yes'
            # If duration is 0 or no transcript, call didn't connect - no voicemail left
    
    # Format call notes entry in required format (same as N1 project)
    call_notes_structured = f"""Call Placed At: {call_placed_at}

Did Client Answer: {did_client_answer}

Was Full Message Conveyed: {was_full_message_conveyed}

Was Voicemail Left: {was_voicemail_left}
"""
    
    # Add the original analysis summary if available (for voicemail, use "Left voicemail")
    if is_voicemail or was_voicemail_left == 'Yes':
        call_notes_summary = 'Left voicemail'
    else:
        call_notes_summary = summary if summary and summary != 'No summary available' else ''
    
    # Combine structured format with summary (add "analysis:" label)
    if call_notes_summary:
        call_notes_entry = call_notes_structured + f"\nanalysis:\n\n{call_notes_summary}\n"
    else:
        call_notes_entry = call_notes_structured
    
    # Get existing AI Call Summary (this is the column we update)
    existing_ai_call_summary = customer.get('ai_call_summary', '')
    
    # Append call notes entry to existing AI Call Summary (separate each call with separator)
    if existing_ai_call_summary:
        new_ai_call_summary = existing_ai_call_summary + "\n---\n" + call_notes_entry
    else:
        new_ai_call_summary = call_notes_entry

    # Update fields
    updates = {
        'ai_call_stage': new_stage,
        'ai_call_summary': new_ai_call_summary,  # Update with formatted call notes (same format as N1 project Call Notes)
        'ai_call_eval': new_eval,  # Keep old format for eval
        # 'done?': mark_done  # Commented out - wait for manual verification
    }

    if next_followup_date:
        updates['f_u_date'] = next_followup_date.strftime('%Y-%m-%d')

    # Perform update
    success = smartsheet_service.update_customer_fields(customer, updates)

    if success:
        print(f"✅ Smartsheet updated successfully")
        print(f"   • Stage: {current_stage} → {new_stage}")
        print(f"   • AI Call Summary: Updated with formatted call notes (Call #{call_number})")
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
