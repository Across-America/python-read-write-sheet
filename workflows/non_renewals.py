"""
N1 Project - Non-Renewals Workflow
Notify Customers About Non-Renewal and Re-Quoting
Contact insureds who have received non-renewals to let them know about the non-renewal
and that we are working on re-quoting and if anything further is needed we will contact them

Note: This workflow is part of the N1 Project, which includes two workflows based on the renewal sheet:
- Renewal Workflow
- Non-Renewal Workflow (this file)
"""

from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from services import VAPIService, SmartsheetService
from config import (
    NON_RENEWALS_ASSISTANT_ID,
    NON_RENEWAL_CALLING_SCHEDULE,
    NON_RENEWAL_1ST_REMINDER_ASSISTANT_ID,
    NON_RENEWAL_2ND_REMINDER_ASSISTANT_ID,
    NON_RENEWAL_3RD_REMINDER_ASSISTANT_ID,
    RENEWAL_PLR_SHEET_ID,
    RENEWAL_WORKSPACE_NAME
)
from workflows.renewals import parse_date
import logging
from typing import List, Dict, Optional, Tuple


# ========================================
# Data Validation and Filtering
# ========================================

def validate_non_renewal_customer_data(customer):
    """
    Comprehensive data validation for non-renewal customer
    
    Args:
        customer: Customer dict
        
    Returns:
        tuple: (is_valid: bool, error_message: str, validated_data: dict)
    """
    errors = []
    validated = {}
    
    # Required fields validation
    company = customer.get('company', '').strip()
    if not company:
        errors.append("Company name is empty")
    else:
        validated['company'] = company
    
    phone_field = customer.get('client_phone_number', '') or customer.get('phone_number', '')
    phone = phone_field.strip()
    if not phone:
        errors.append("Phone number is empty")
    else:
        # Basic phone validation (should start with + or be numeric)
        if not (phone.startswith('+') or phone.replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit()):
            errors.append(f"Invalid phone number format: {phone}")
        else:
            validated['phone_number'] = phone
    
    expiry_field = customer.get('expiration_date', '') or customer.get('expiration date', '')
    if not expiry_field:
        errors.append("Expiration date is empty")
    else:
        expiry_date = parse_date(expiry_field)
        if not expiry_date:
            errors.append(f"Invalid expiration date format: {expiry_field}")
        else:
            # Check if date is in the past (expired)
            if expiry_date < date.today():
                errors.append(f"Policy already expired: {expiry_date}")
            else:
                validated['expiration_date'] = expiry_date
                validated['expiration_date_str'] = expiry_field
    
    # Non-renewal status validation
    renewal_field = customer.get('renewal / non-renewal', '') or customer.get('renewal___non-renewal', '')
    renewal_status = str(renewal_field).strip().lower()
    if not renewal_status:
        errors.append("Renewal / Non-Renewal is empty")
    elif 'renewal' in renewal_status and 'non-renewal' not in renewal_status and 'non renewal' not in renewal_status and 'nonrenewal' not in renewal_status.replace(' ', ''):
        errors.append(f"Not a non-renewal customer: {renewal_field}")
    else:
        validated['renewal_status'] = renewal_status
    
    # Status validation - must be one of the allowed statuses
    # Required statuses for non-renewal workflow:
    # - u/w questions
    # - missing information
    # - no response client
    # - pending uw cancel
    # - pending photos
    # - pending uw review
    # - re-quote
    status_field = customer.get('status', '') or customer.get('Status', '')
    status = str(status_field).strip().lower()
    
    # Allowed statuses (case-insensitive matching with variants for flexibility)
    allowed_statuses = [
        'u/w questions',
        'uw questions',  # Variant without slash
        'missing information',
        'no response client',
        'no response',  # Variant for flexibility
        'pending uw cancel',
        'pending uwcancel',  # Variant without space
        'pending photos',
        'pending uw review',
        'pending uwreview',  # Variant without space
        're-quote',
        'requote'  # Variant without hyphen
    ]
    
    # Check if status matches any allowed status (case-insensitive, flexible matching)
    status_normalized = status.replace(' ', '').replace('-', '').replace('_', '').replace('/', '')
    matches_allowed = False
    
    for allowed in allowed_statuses:
        allowed_normalized = allowed.replace(' ', '').replace('-', '').replace('_', '').replace('/', '')
        if allowed_normalized in status_normalized or status_normalized in allowed_normalized:
            matches_allowed = True
            break
    
    if not matches_allowed:
        errors.append(f"Status not in allowed list: {status_field}")
    else:
        validated['status'] = status
    
    # Payee validation - No filtering required (any payee is allowed for non-renewal workflow)
    payee = str(customer.get('payee', '')).strip()
    if payee:
        validated['payee'] = payee
    # Note: Non-renewal workflow accepts any payee value (no filtering)
    
    if errors:
        return False, "; ".join(errors), None
    
    return True, "", validated


def should_skip_non_renewal_row(customer):
    """
    Check if a row should be skipped for non-renewal calling
    
    Only process rows that meet ALL of:
    - renewal / non-renewal = "non-renewal" (case-insensitive)
    - status is one of: u/w questions, missing information, no response client,
      pending uw cancel, pending photos, pending uw review, re-quote
    - payee: Any value (no filtering required)
    
    Skip if ANY of:
    - done is checked/true
    - company is empty
    - client_phone_number is empty
    - expiration_date is empty or invalid
    - renewal / non-renewal is empty or not "non-renewal"
    - status is not in the allowed list
    
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

    # Use Client Phone Number (actual column name from sheet)
    phone_field = customer.get('client_phone_number', '') or customer.get('phone_number', '')
    if not phone_field.strip():
        return True, "Phone number is empty"

    # Use Expiration Date (actual column name from sheet)
    expiry_field = customer.get('expiration_date', '') or customer.get('expiration date', '')
    if not expiry_field.strip():
        return True, "Expiration date is empty"

    # Check renewal / non-renewal status (actual column name from sheet)
    renewal_field = customer.get('renewal / non-renewal', '') or customer.get('renewal___non-renewal', '')
    renewal_status = str(renewal_field).strip().lower()
    if not renewal_status:
        return True, "Renewal / Non-Renewal is empty"
    
    # Must be "non-renewal" (not "renewal")
    if 'non-renewal' not in renewal_status and 'non renewal' not in renewal_status and 'nonrenewal' not in renewal_status.replace(' ', ''):
        return True, f"Renewal / Non-Renewal is not 'non-renewal' (Status: {renewal_field})"

    # Check status - must be one of the allowed statuses
    # Required statuses for non-renewal workflow:
    # - u/w questions
    # - missing information
    # - no response client
    # - pending uw cancel
    # - pending photos
    # - pending uw review
    # - re-quote
    status_field = customer.get('status', '') or customer.get('Status', '')
    status = str(status_field).strip().lower()
    
    # Allowed statuses (case-insensitive matching with variants for flexibility)
    allowed_statuses = [
        'u/w questions',
        'uw questions',  # Variant without slash
        'missing information',
        'no response client',
        'no response',  # Variant for flexibility
        'pending uw cancel',
        'pending uwcancel',  # Variant without space
        'pending photos',
        'pending uw review',
        'pending uwreview',  # Variant without space
        're-quote',
        'requote'  # Variant without hyphen
    ]
    
    # Check if status matches any allowed status (case-insensitive, flexible matching)
    status_normalized = status.replace(' ', '').replace('-', '').replace('_', '').replace('/', '')
    matches_allowed = False
    
    for allowed in allowed_statuses:
        allowed_normalized = allowed.replace(' ', '').replace('-', '').replace('_', '').replace('/', '')
        if allowed_normalized in status_normalized or status_normalized in allowed_normalized:
            matches_allowed = True
            break
    
    if not matches_allowed:
        return True, f"Status not in allowed list (Status: {status_field}, Allowed: {', '.join(allowed_statuses)})"

    return False, ""


def get_non_renewal_stage(customer):
    """
    Get the current non-renewal call stage for a customer
    
    Returns:
        int: Stage number (0 for empty/null, 1, 2+)
    """
    # Try multiple possible column names (normalized)
    # Use "stage" column (same as renewal workflow) for consistency
    stage = customer.get('stage', '') or customer.get('non_renewal_call_stage', '') or customer.get('ai_call_stage', '')
    
    if not stage or stage == '' or stage is None:
        return 0
    
    try:
        stage_int = int(stage)
        if stage_int < 0:
            return 0
        return stage_int
    except (ValueError, TypeError):
        return 0


def get_non_renewal_assistant_id_for_stage(stage):
    """
    Get the assistant ID for a given non-renewal stage
    
    Non-Renewal specific Assistant IDs:
    - Stage 0 (14 days before) & Stage 1 (7 days before): NON_RENEWAL_1ST_REMINDER_ASSISTANT_ID
    - Stage 2 (1 day before): NON_RENEWAL_3RD_REMINDER_ASSISTANT_ID
    
    Args:
        stage: Stage number (0, 1, or 2)
            - Stage 0: 14 days before expiration (1st Reminder) - shared with Stage 1
            - Stage 1: 7 days before expiration (2nd Reminder) - shared with Stage 0
            - Stage 2: 1 day before expiration (3rd Reminder)
    
    Returns:
        str: Assistant ID for the stage
    """
    assistant_map = {
        0: NON_RENEWAL_1ST_REMINDER_ASSISTANT_ID,  # 1st Reminder (14 days before)
        1: NON_RENEWAL_2ND_REMINDER_ASSISTANT_ID,  # 2nd Reminder (7 days before) - same as 1st
        2: NON_RENEWAL_3RD_REMINDER_ASSISTANT_ID   # 3rd Reminder (1 day before)
    }
    
    return assistant_map.get(stage)


def is_non_renewal_ready_for_calling(customer, today):
    """
    Check if a non-renewal customer is ready for calling based on timeline logic
    All date calculations are based on the expiration_date column
    
    Args:
        customer: Customer dict
        today: Current date
        
    Returns:
        tuple: (is_ready: bool, reason: str, stage: int)
    """
    # Parse expiration date from sheet (this is the base date for all calculations)
    expiry_date_str = customer.get('expiration_date', '') or customer.get('expiration date', '')
    expiry_date = parse_date(expiry_date_str)
    
    if not expiry_date:
        return False, "Invalid expiration date", -1
    
    # Calculate days until expiry (based on expiration_date column)
    days_until_expiry = (expiry_date - today).days
    
    # Check if already expired (skip if expired)
    if days_until_expiry < 0:
        return False, f"Policy already expired ({abs(days_until_expiry)} days ago)", -1
    
    # Check if today matches any of the calling schedule days (14, 7, or 1 days before)
    for stage, days_before in enumerate(NON_RENEWAL_CALLING_SCHEDULE):
        if days_until_expiry == days_before:
            return True, f"Ready for stage {stage} call ({days_before} days before expiry)", stage
    
    # If within calling window but not on scheduled day
    if days_until_expiry <= max(NON_RENEWAL_CALLING_SCHEDULE):
        return False, f"Within calling window but not on scheduled day (expires in {days_until_expiry} days)", -1
    
    # Too early
    return False, f"Too early to call (expires in {days_until_expiry} days)", -1


def calculate_non_renewal_next_followup_date(customer, current_stage):
    """
    Calculate the next follow-up date for non-renewal calls
    Based on the fixed schedule: 14, 7, 1 days before expiration_date
    
    Args:
        customer: Customer dict
        current_stage: Current call stage (0, 1, or 2)
    
    Returns:
        date or None: Next follow-up date (None for stage 2/final)
    """
    # Use Expiration Date column (this is the base date for all calculations)
    expiry_date_str = customer.get('expiration_date', '') or customer.get('expiration date', '')
    expiry_date = parse_date(expiry_date_str)
    
    if not expiry_date:
        print(f"   ⚠️  Invalid expiry date: {expiry_date_str}")
        return None
    
    # Fixed schedule: 14, 7, 1 days before expiration_date
    if current_stage < len(NON_RENEWAL_CALLING_SCHEDULE) - 1:
        next_stage = current_stage + 1
        days_before_expiry = NON_RENEWAL_CALLING_SCHEDULE[next_stage]
        next_date = expiry_date - timedelta(days=days_before_expiry)
        
        stage_names = ["14 days before", "7 days before", "1 day before"]
        print(f"   📅 Stage {current_stage}→{next_stage}: Next call {stage_names[next_stage]} ({next_date})")
        
        return next_date
    else:
        # Final stage - no more follow-ups
        print(f"   📅 Stage {current_stage}: Final call - no more follow-ups")
        return None


def get_non_renewal_customers_ready_for_calls(smartsheet_service):
    """
    Get all non-renewal customers ready for calls today, grouped by stage
    Based on expiration_date column: 14 days, 7 days, 1 day before expiry
    
    Returns:
        dict: Customers grouped by stage {0: [...], 1: [...], 2: [...]}
    """
    print("=" * 80)
    print("🔍 FETCHING NON-RENEWAL CUSTOMERS READY FOR CALLS")
    print("=" * 80)

    # Get all customers from sheet
    all_customers = smartsheet_service.get_all_customers_with_stages()

    # Use Pacific Time for "today"
    pacific_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific_tz).date()
    print(f"📅 Today (Pacific Time): {today}")
    print(f"⏰ Calling schedule: {NON_RENEWAL_CALLING_SCHEDULE} days before expiry")

    customers_by_stage = {0: [], 1: [], 2: []}  # 3 stages: 14, 7, 1 days before
    skipped_count = 0
    
    for customer in all_customers:
        # Initial validation
        should_skip, skip_reason = should_skip_non_renewal_row(customer)
        if should_skip:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: {skip_reason}")
            continue
        
        # Get current stage
        current_stage = get_non_renewal_stage(customer)
        
        # Skip if stage >= 3 (call sequence complete - all 3 calls made)
        if current_stage >= 3:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: Non-renewal sequence complete (stage {current_stage})")
            continue
        
        # Check if ready for calling based on timeline
        is_ready, ready_reason, target_stage = is_non_renewal_ready_for_calling(customer, today)
        if not is_ready:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: {ready_reason}")
            continue
        
        # Check if the customer is at the right stage for today's call
        # Allow auto-adjustment if customer missed earlier stages (for new workflows)
        if current_stage != target_stage:
            if current_stage < target_stage:
                # Customer missed earlier stages - allow auto-adjustment
                print(f"   ⚠️  Row {customer.get('row_number')}: Auto-adjusting stage {current_stage} → {target_stage} (missed earlier stages)")
                # Continue to add customer - stage will be updated after call
            else:
                # Customer already passed this stage - skip
                skipped_count += 1
                print(f"   ⏭️  Skipping row {customer.get('row_number')}: Already past this stage (current: {current_stage}, needed: {target_stage})")
                continue
        
        customers_by_stage[target_stage].append(customer)
        stage_names = ["14 days before", "7 days before", "1 day before"]
        print(f"   ✅ Row {customer.get('row_number')}: Stage {target_stage} ({stage_names[target_stage]}), ready for non-renewal call")
    
    print(f"\n📊 Summary:")
    print(f"   Stage 0 (14 days before): {len(customers_by_stage[0])} customers")
    print(f"   Stage 1 (7 days before): {len(customers_by_stage[1])} customers")
    print(f"   Stage 2 (1 day before): {len(customers_by_stage[2])} customers")
    print(f"   Skipped: {skipped_count} rows")
    print(f"   Total ready: {sum(len(v) for v in customers_by_stage.values())}")
    
    return customers_by_stage


def format_non_renewal_call_entry(summary, evaluation, call_number):
    """Format a non-renewal call entry for appending"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entry = f"[Non-Renewal Call {call_number} - {timestamp}]\n{summary}\n"
    eval_entry = f"[Non-Renewal Call {call_number} - {timestamp}]\n{evaluation}\n"
    return entry, eval_entry


def update_after_non_renewal_call(smartsheet_service, customer, call_data, call_stage):
    """
    Update Smartsheet after a successful non-renewal call
    
    Args:
        smartsheet_service: SmartsheetService instance
        customer: Customer dict
        call_data: Call result data from VAPI
        call_stage: Stage at which the call was made (0, 1, or 2)
                    This may be different from customer's current_stage if auto-adjustment occurred
    """
    # Extract call analysis
    analysis = call_data.get('analysis', {})
    
    # Debug: Print analysis structure
    if not analysis:
        print(f"⚠️  WARNING: No analysis found in call_data")
        print(f"   Call data keys: {list(call_data.keys())}")
        # Try to get analysis from different possible locations
        if 'result' in call_data and isinstance(call_data['result'], dict):
            analysis = call_data['result'].get('analysis', {})
            print(f"   Found analysis in call_data['result']")
        if not analysis and 'call_data' in call_data:
            analysis = call_data['call_data'].get('analysis', {})
            print(f"   Found analysis in call_data['call_data']")
    
    summary = analysis.get('summary', '') if analysis else ''
    if not summary or summary == '':
        # Try alternative locations for summary
        if analysis:
            summary = analysis.get('transcript', '') or analysis.get('summaryText', '') or 'No summary available'
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

    evaluation = str(evaluation).lower()

    # Determine new stage (advance to next stage after this call)
    new_stage = call_stage + 1

    # Calculate next followup date (None for stage 2)
    next_followup_date = calculate_non_renewal_next_followup_date(customer, call_stage)

    # Format entries for appending
    call_number = call_stage + 1
    summary_entry, eval_entry = format_non_renewal_call_entry(summary, evaluation, call_number)

    # Get existing values
    existing_summary = customer.get('non_renewal_call_summary', '') or customer.get('ai_call_summary', '')
    existing_eval = customer.get('non_renewal_call_eval', '') or customer.get('ai_call_eval', '')
    
    # Format call summary for Call Notes column (similar to CL1 Project and Renewal workflow)
    # Use summary from VAPI analysis instead of full transcript
    timestamp = datetime.now(ZoneInfo("America/Los_Angeles")).strftime('%Y-%m-%d %H:%M:%S')
    call_notes_entry = f"[Non-Renewal Call #{call_number} - {timestamp}]\n{summary}\n"
    
    # Get existing call notes
    existing_notes = customer.get('call_notes', '') or customer.get('non_renewal_call_notes', '')
    
    # Append summary to existing notes (similar to CL1 Project format)
    if existing_notes:
        new_call_notes = existing_notes + "\n---\n" + call_notes_entry
    else:
        new_call_notes = call_notes_entry

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
    # Use actual column names from Smartsheet (same as renewal workflow):
    # - "Stage" (normalized: "stage")
    # - "F/U Date" (normalized: "f_u_date")
    # - "Call Notes" (normalized: "call_notes")
    # - "Last Call Made Date" (normalized: "last_call_made_date")
    
    # Get current date in Pacific Time for Last Call Made Date
    # Note: Smartsheet DATE type columns only accept date format (YYYY-MM-DD), not datetime
    pacific_tz = ZoneInfo("America/Los_Angeles")
    current_date = datetime.now(pacific_tz).date()
    last_call_date_str = current_date.strftime('%Y-%m-%d')
    
    updates = {
        'stage': new_stage,  # Use "Stage" column
        'call_notes': new_call_notes,  # Store summary in Call Notes (similar to CL1 Project and Renewal workflow)
        'last_call_made_date': last_call_date_str,  # Record last call date (date only for DATE type column)
    }

    if next_followup_date:
        updates['f_u_date'] = next_followup_date.strftime('%Y-%m-%d')  # Use "F/U Date" column
    
    # Note: non_renewal_call_summary and non_renewal_call_eval columns may not exist in the sheet
    # They will be skipped automatically by update_customer_fields if not found

    # Perform update
    success = smartsheet_service.update_customer_fields(customer, updates)

    if success:
        print(f"✅ Smartsheet updated successfully")
        print(f"   • Stage: {call_stage} → {new_stage}")
        print(f"   • Call Notes: Updated with summary (Call #{call_number})")
        print(f"   • Last Call Made Date: {last_call_date_str}")
        if next_followup_date:
            print(f"   • Next F/U Date: {next_followup_date}")
    else:
        print(f"❌ Smartsheet update failed")

    return success


# ========================================
# Error Logging and Reporting
# ========================================

class NonRenewalWorkflowErrorLogger:
    """Error logger for Non-Renewal workflow"""
    
    def __init__(self):
        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []
        self.validation_failures: List[Dict] = []
    
    def log_error(self, customer: Dict, stage: int, error_type: str, message: str, exception: Optional[Exception] = None):
        """Log an error with context"""
        error_entry = {
            'timestamp': datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
            'customer': customer.get('company', 'Unknown'),
            'row_number': customer.get('row_number', 'N/A'),
            'stage': stage,
            'error_type': error_type,
            'message': message,
            'exception': str(exception) if exception else None
        }
        self.errors.append(error_entry)
        print(f"❌ ERROR [{error_type}]: {customer.get('company', 'Unknown')} (Row {customer.get('row_number', 'N/A')}) - {message}")
        if exception:
            import traceback
            traceback.print_exc()
    
    def log_warning(self, customer: Dict, stage: int, warning_type: str, message: str):
        """Log a warning with context"""
        warning_entry = {
            'timestamp': datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
            'customer': customer.get('company', 'Unknown'),
            'row_number': customer.get('row_number', 'N/A'),
            'stage': stage,
            'warning_type': warning_type,
            'message': message
        }
        self.warnings.append(warning_entry)
        print(f"⚠️  WARNING [{warning_type}]: {customer.get('company', 'Unknown')} (Row {customer.get('row_number', 'N/A')}) - {message}")
    
    def log_validation_failure(self, customer: Dict, reason: str):
        """Log a validation failure"""
        validation_entry = {
            'timestamp': datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
            'customer': customer.get('company', 'Unknown'),
            'row_number': customer.get('row_number', 'N/A'),
            'reason': reason
        }
        self.validation_failures.append(validation_entry)
    
    def get_summary(self) -> Dict:
        """Get error summary"""
        return {
            'total_errors': len(self.errors),
            'total_warnings': len(self.warnings),
            'total_validation_failures': len(self.validation_failures),
            'errors_by_type': self._group_by_type(self.errors, 'error_type'),
            'warnings_by_type': self._group_by_type(self.warnings, 'warning_type')
        }
    
    def _group_by_type(self, entries: List[Dict], key: str) -> Dict:
        """Group entries by type"""
        grouped = {}
        for entry in entries:
            entry_type = entry.get(key, 'Unknown')
            grouped[entry_type] = grouped.get(entry_type, 0) + 1
        return grouped
    
    def print_summary(self):
        """Print error summary"""
        summary = self.get_summary()
        print(f"\n{'=' * 80}")
        print(f"📊 ERROR SUMMARY")
        print(f"{'=' * 80}")
        print(f"   ❌ Total Errors: {summary['total_errors']}")
        print(f"   ⚠️  Total Warnings: {summary['total_warnings']}")
        print(f"   🔍 Total Validation Failures: {summary['total_validation_failures']}")
        
        if summary['errors_by_type']:
            print(f"\n   Errors by Type:")
            for error_type, count in summary['errors_by_type'].items():
                print(f"      • {error_type}: {count}")
        
        if summary['warnings_by_type']:
            print(f"\n   Warnings by Type:")
            for warning_type, count in summary['warnings_by_type'].items():
                print(f"      • {warning_type}: {count}")
        
        print(f"{'=' * 80}")


def run_non_renewals_calling(test_mode=False, schedule_at=None, auto_confirm=False):
    """
    Main function to run non-renewals calling workflow with comprehensive error handling
    
    Args:
        test_mode: If True, skip actual calls and Smartsheet updates (default: False)
        schedule_at: Optional datetime to schedule calls
        auto_confirm: If True, skip user confirmation prompt (for cron jobs) (default: False)
    """
    # Initialize error logger
    error_logger = NonRenewalWorkflowErrorLogger()
    
    print("=" * 80)
    print("🚀 N1 PROJECT - NON-RENEWALS CALLING SYSTEM")
    if test_mode:
        print("🧪 TEST MODE - No actual calls or updates will be made")
    if schedule_at:
        print(f"⏰ SCHEDULED MODE - Calls will be scheduled for {schedule_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("📋 N1 Project: Non-renewal notifications with dynamic sheet discovery")
    print("📞 3-stage calling: 14 days → 7 days → 1 day before expiry")
    print("=" * 80)
    
    try:
        # Initialize services
        smartsheet_service = SmartsheetService(sheet_id=RENEWAL_PLR_SHEET_ID)
        vapi_service = VAPIService()
    except Exception as e:
        error_logger.log_error({}, 0, 'INITIALIZATION_ERROR', f"Failed to initialize services: {e}", e)
        return False
    
    # Get customers grouped by stage
    customers_by_stage = get_non_renewal_customers_ready_for_calls(smartsheet_service)
    
    total_customers = sum(len(v) for v in customers_by_stage.values())
    
    if total_customers == 0:
        print("\n✅ No non-renewal customers ready for calls today")
        return True
    
    # Show summary and ask for confirmation
    print(f"\n{'=' * 80}")
    print(f"📊 NON-RENEWAL CUSTOMERS READY FOR CALLS TODAY:")
    print(f"{'=' * 80}")
    
    for stage, customers in customers_by_stage.items():
        if customers:
            stage_names = {0: "1st Reminder (14 days before)", 1: "2nd Reminder (7 days before)", 2: "3rd Reminder (1 day before)"}
            assistant_id = get_non_renewal_assistant_id_for_stage(stage)
            print(f"\n🔔 Stage {stage} ({stage_names[stage]}) - {len(customers)} customers:")
            print(f"   🤖 Assistant ID: {assistant_id}")
            
            for i, customer in enumerate(customers[:5], 1):
                print(f"   {i}. {customer.get('company', 'Unknown')} - {customer.get('client_phone_number', 'N/A')}")
            
            if len(customers) > 5:
                print(f"   ... and {len(customers) - 5} more")
    
    print(f"\n{'=' * 80}")
    if not test_mode:
        print(f"⚠️  WARNING: This will make {total_customers} non-renewal phone calls!")
        print(f"💰 This will incur charges for each call")
    else:
        print(f"🧪 TEST MODE: Will simulate {total_customers} non-renewal calls (no charges)")
    print(f"{'=' * 80}")

    # Only ask for confirmation if not auto_confirm and not test_mode
    if not test_mode and not auto_confirm:
        response = input(f"\nProceed with non-renewals calling? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ Non-renewals calling cancelled")
            return False
    elif auto_confirm:
        print(f"🤖 AUTO-CONFIRM: Proceeding automatically (cron mode)")
    
    # Process each stage (3 stages: 14, 7, 1 days before)
    total_success = 0
    total_failed = 0

    for stage in [0, 1, 2]:
        customers = customers_by_stage[stage]

        if not customers:
            continue

        stage_names = {0: "14 days before", 1: "7 days before", 2: "1 day before"}
        stage_name = stage_names[stage]
        assistant_id = get_non_renewal_assistant_id_for_stage(stage)

        print(f"\n{'=' * 80}")
        print(f"📞 NON-RENEWAL CALLING STAGE {stage} ({stage_name}) - {len(customers)} customers")
        print(f"🤖 Using Assistant: {assistant_id}")
        print(f"{'=' * 80}")

        if test_mode:
            # Test mode: Simulate calls without actual API calls
            print(f"\n🧪 TEST MODE: Simulating {len(customers)} non-renewal calls...")
            for customer in customers:
                print(f"   ✅ [SIMULATED] Would call: {customer.get('company', 'Unknown')}")
                total_success += 1
        else:
            # Stage 0: Batch calling (all customers simultaneously)
            if stage == 0:
                print(f"📦 Batch calling mode (simultaneous)")
                # Validate customers before calling
                validated_customers = []
                for customer in customers:
                    is_valid, error_msg, validated_data = validate_non_renewal_customer_data(customer)
                    if is_valid:
                        # Merge validated data into customer (especially phone_number)
                        customer_for_call = {**customer, **validated_data}
                        validated_customers.append(customer_for_call)
                    else:
                        error_logger.log_validation_failure(customer, error_msg)
                        error_logger.log_warning(customer, stage, 'VALIDATION_FAILED', error_msg)
                        total_failed += 1
                
                if not validated_customers:
                    print(f"\n⚠️  No valid customers for Stage {stage} after validation")
                    continue
                
                try:
                    results = vapi_service.make_batch_call_with_assistant(
                        validated_customers,
                        assistant_id,
                        schedule_immediately=(schedule_at is None),
                        schedule_at=schedule_at
                    )

                    if results:
                        print(f"\n✅ Stage {stage} non-renewal batch calls completed")
                        print(f"   📊 Received {len(results)} call result(s) for {len(validated_customers)} customer(s)")

                        # Only update Smartsheet if calls were immediate (not scheduled)
                        if schedule_at is None:
                            # Handle case where results might be a list of lists or single items
                            for i, customer in enumerate(validated_customers):
                                # Get corresponding call_data (handle different result structures)
                                if i < len(results):
                                    call_data = results[i]
                                else:
                                    # If results length doesn't match, try to get from first result
                                    call_data = results[0] if results else None
                                
                                if call_data:
                                    # Debug: Check if analysis exists
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
                                    
                                    try:
                                        success = update_after_non_renewal_call(smartsheet_service, customer, call_data, stage)
                                        if success:
                                            total_success += 1
                                        else:
                                            error_logger.log_error(customer, stage, 'SMARTSHEET_UPDATE_FAILED', "Failed to update Smartsheet after call")
                                            total_failed += 1
                                    except Exception as e:
                                        error_logger.log_error(customer, stage, 'SMARTSHEET_UPDATE_ERROR', f"Exception during Smartsheet update: {e}", e)
                                        total_failed += 1
                                else:
                                    error_logger.log_error(customer, stage, 'VAPI_CALL_FAILED', "VAPI call returned no data")
                                    total_failed += 1
                        else:
                            print(f"   ⏰ Calls scheduled - Smartsheet will be updated after calls complete")
                            total_success += len(validated_customers)
                    else:
                        print(f"\n❌ Stage {stage} non-renewal batch calls failed")
                        for customer in validated_customers:
                            error_logger.log_error(customer, stage, 'VAPI_CALL_FAILED', "VAPI API returned no results")
                        total_failed += len(validated_customers)
                except Exception as e:
                    print(f"\n❌ Stage {stage} non-renewal batch calls failed with exception")
                    for customer in validated_customers:
                        error_logger.log_error(customer, stage, 'VAPI_CALL_EXCEPTION', f"Exception during VAPI call: {e}", e)
                    total_failed += len(validated_customers)

            # Stage 1 & 2: Sequential calling (one customer at a time)
            else:
                print(f"🔄 Sequential calling mode (one at a time)")

                for i, customer in enumerate(customers, 1):
                    print(f"\n   📞 Call {i}/{len(customers)}: {customer.get('company', 'Unknown')}")

                    # Validate customer before calling
                    is_valid, error_msg, validated_data = validate_non_renewal_customer_data(customer)
                    if not is_valid:
                        error_logger.log_validation_failure(customer, error_msg)
                        error_logger.log_warning(customer, stage, 'VALIDATION_FAILED', error_msg)
                        total_failed += 1
                        continue

                    # Merge validated data into customer (especially phone_number)
                    customer_for_call = {**customer, **validated_data}

                    try:
                        results = vapi_service.make_batch_call_with_assistant(
                            [customer_for_call],  # Only one customer at a time
                            assistant_id,
                            schedule_immediately=(schedule_at is None),
                            schedule_at=schedule_at
                        )

                        if results and results[0]:
                            call_data = results[0]
                            
                            # Check if analysis exists, try to refresh if missing
                            if 'analysis' not in call_data or not call_data.get('analysis'):
                                print(f"   ⚠️  No analysis in call_data, attempting to refresh...")
                                if 'id' in call_data:
                                    call_id = call_data['id']
                                    try:
                                        refreshed_data = vapi_service.check_call_status(call_id)
                                        if refreshed_data and refreshed_data.get('analysis'):
                                            call_data = refreshed_data
                                            print(f"   ✅ Successfully retrieved analysis from refreshed call status")
                                        else:
                                            print(f"   ⚠️  Refreshed call status also has no analysis")
                                    except Exception as e:
                                        print(f"   ❌ Failed to refresh call status: {e}")

                            # Only update Smartsheet if calls were immediate (not scheduled)
                            if schedule_at is None:
                                try:
                                    success = update_after_non_renewal_call(smartsheet_service, customer, call_data, stage)
                                    if success:
                                        total_success += 1
                                    else:
                                        error_logger.log_error(customer, stage, 'SMARTSHEET_UPDATE_FAILED', "Failed to update Smartsheet after call")
                                        total_failed += 1
                                except Exception as e:
                                    error_logger.log_error(customer, stage, 'SMARTSHEET_UPDATE_ERROR', f"Exception during Smartsheet update: {e}", e)
                                    total_failed += 1
                            else:
                                print(f"      ⏰ Call scheduled - Smartsheet will be updated after call completes")
                                total_success += 1
                        else:
                            print(f"      ❌ Call {i} failed")
                            error_logger.log_error(customer, stage, 'VAPI_CALL_FAILED', "VAPI call returned no data")
                            total_failed += 1
                    except Exception as e:
                        print(f"      ❌ Call {i} failed with exception")
                        error_logger.log_error(customer, stage, 'VAPI_CALL_EXCEPTION', f"Exception during VAPI call: {e}", e)
                        total_failed += 1

                print(f"\n✅ Stage {stage} non-renewal sequential calls completed")
    
    # Final summary
    print(f"\n{'=' * 80}")
    print(f"🏁 NON-RENEWALS CALLING COMPLETE")
    print(f"{'=' * 80}")
    print(f"   ✅ Successful: {total_success}")
    print(f"   ❌ Failed: {total_failed}")
    print(f"   📊 Total: {total_success + total_failed}")
    print(f"{'=' * 80}")
    
    # Print error summary
    if error_logger.errors or error_logger.warnings or error_logger.validation_failures:
        error_logger.print_summary()
    
    return True


if __name__ == "__main__":
    import sys
    test_mode = "--test" in sys.argv or "-t" in sys.argv
    run_non_renewals_calling(test_mode=test_mode)

