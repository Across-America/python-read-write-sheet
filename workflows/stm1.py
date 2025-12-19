"""
STM1 Project Workflow
Statement Call Workflow - AACS workspace
Automated calling workflow for STM1 project

Note: This workflow implements daily condition-based calling for STM1 project.
Calls are made daily based on conditions (not on a fixed multi-stage schedule).
Uses the "Insured Driver Statement" sheet in the "AACS" workspace.
"""

from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from services import VAPIService, SmartsheetService
from config import (
    STM1_ASSISTANT_ID,
    STM1_SHEET_ID,
    STM1_WORKSPACE_NAME,
    STM1_SHEET_NAME,
    STM1_PHONE_NUMBER_ID,
    STM1_MAX_DAILY_CALLS,
    STM1_CALLING_START_HOUR,
    STM1_CALLING_END_HOUR
)
from workflows.stm1_variables import build_stm1_variable_values
from workflows.cancellations import (
    is_weekend,
    count_business_days,
    add_business_days,
    parse_date
)
import logging
from typing import List, Dict, Optional, Tuple


# ========================================
# Data Validation and Filtering
# ========================================

def validate_stm1_customer_data(customer):
    """
    Comprehensive data validation for STM1 customer
    
    Args:
        customer: Customer dict
        
    Returns:
        tuple: (is_valid: bool, error_message: str, validated_data: dict)
    """
    errors = []
    validated = {}
    
    # Required fields validation
    # Use insured_name column from STM1 sheet (note: Insured Driver Statement sheet uses 'insured_name_')
    company = customer.get('insured_name_', '').strip() or customer.get('insured_name', '').strip() or customer.get('company', '').strip()
    if not company:
        errors.append("Insured name is empty")
    else:
        validated['company'] = company
        validated['insured_name'] = company
        validated['insured_name_'] = company
    
    # Use phone_number column from STM1 sheet (Insured Driver Statement uses 'phone_number')
    phone_field = customer.get('phone_number', '') or customer.get('contact_phone', '') or customer.get('client_phone_number', '')
    phone = phone_field.strip()
    if not phone:
        errors.append("Phone number is empty")
    else:
        # Basic phone validation (should start with + or be numeric)
        if not (phone.startswith('+') or phone.replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit()):
            errors.append(f"Invalid phone number format: {phone}")
        else:
            validated['phone_number'] = phone
    
    # Note: Insured Driver Statement sheet doesn't have due_date column
    # So we skip the due_date validation for this sheet
    # If needed for other sheets, uncomment below:
    # target_date_field = customer.get('due_date', '') or customer.get('current_due_date', '') or customer.get('target_date', '') or customer.get('expiration_date', '')
    # if not target_date_field:
    #     errors.append("Due date is empty")
    # else:
    #     target_date = parse_date(target_date_field)
    #     if not target_date:
    #         errors.append(f"Invalid date format: {target_date_field}")
    #     else:
    #         validated['target_date'] = target_date
    #         validated['target_date_str'] = target_date_field
    #         validated['due_date'] = target_date
    
    # TODO: Add STM1-specific status/condition validation
    # Example: status, payee, or other filtering conditions
    
    if errors:
        return False, "; ".join(errors), None
    
    return True, "", validated


def should_skip_stm1_row(customer):
    """
    Check if a STM1 row should be skipped
    
    Skip if ANY of:
    - done is checked/true
    - recorded_or_not is checked/true (already recorded)
    - company is empty
    - phone_number is empty
    - called_times > 0 (already called before)
    - Other STM1-specific conditions
    
    Args:
        customer: Customer dict
        
    Returns:
        tuple: (should_skip: bool, reason: str)
    """
    # Check done checkbox
    if customer.get('done?') in [True, 'true', 'True', 1]:
        return True, "Done checkbox is checked"
    
    # Check "recorded or not" checkbox - if checked, skip (already recorded)
    recorded_or_not = customer.get('recorded_or_not', '') or customer.get('recorded or not', '')
    if recorded_or_not in [True, 'true', 'True', 1, 'TRUE']:
        return True, "Recorded or not checkbox is checked (already recorded)"

    # Check called_times - skip if already called (called_times > 0)
    # Column name "called times" normalizes to "called_times" (plural - matches sheet)
    # Also check for singular "called_time" and "called time" for backward compatibility
    called_times_str = customer.get('called_times', '') or customer.get('called_time', '') or customer.get('called time', '') or '0'
    try:
        called_times_count = int(str(called_times_str).strip()) if str(called_times_str).strip() else 0
        if called_times_count > 0:
            return True, f"Already called before (called_times: {called_times_count})"
    except (ValueError, TypeError):
        # If parsing fails, treat as 0 (not called yet)
        pass

    # Check required fields
    # Use insured_name column from STM1 sheet (note: Insured Driver Statement sheet uses 'insured_name_')
    insured_name = customer.get('insured_name_', '').strip() or customer.get('insured_name', '').strip() or customer.get('company', '').strip()
    if not insured_name:
        return True, "Insured name is empty"

    # Use phone_number column from STM1 sheet (Insured Driver Statement uses 'phone_number')
    phone_field = customer.get('phone_number', '') or customer.get('contact_phone', '') or customer.get('client_phone_number', '')
    if not phone_field.strip():
        return True, "Phone number is empty"

    # Note: Insured Driver Statement sheet doesn't have due_date column
    # So we skip the due_date check for this sheet
    # If needed for other sheets, uncomment below:
    # target_date_field = customer.get('due_date', '') or customer.get('current_due_date', '') or customer.get('target_date', '') or customer.get('expiration_date', '')
    # if not target_date_field:
    #     return True, "Due date is empty"
    
    # TODO: Add STM1-specific filtering conditions
    # Example:
    # status = str(customer.get('status', '')).strip().lower()
    # if 'some_status' not in status:
    #     return True, f"Status does not match requirement: {status}"
    
    return False, ""


def get_stm1_last_call_date(customer):
    """
    Get the last call date for a customer
    
    Returns:
        date or None: Last call date if available, None otherwise
    """
    last_call_date_str = customer.get('last_call_made_date', '') or customer.get('last_call_date', '')
    if not last_call_date_str:
        return None
    
    return parse_date(last_call_date_str)


# ========================================
# STM1 Timeline Logic
# ========================================

def is_stm1_ready_for_calling(customer, today):
    """
    Check if a STM1 customer is ready for calling based on daily conditions
    
    Conditions:
    - Must not have been called today (check last_call_made_date)
    - Must meet other business conditions (can be customized)
    
    Args:
        customer: Customer dict
        today: Current date
        
    Returns:
        tuple: (is_ready: bool, reason: str)
    """
    # Check if already called today
    last_call_date = get_stm1_last_call_date(customer)
    if last_call_date and last_call_date == today:
        return False, f"Already called today ({last_call_date})"
    
    # TODO: Add additional business condition checks here
    # Example conditions:
    # - Check if target date is in the future
    # - Check status or other fields
    # - Check if done checkbox is not checked
    
    # For now, if not called today and passes basic validation, ready to call
    return True, "Ready for daily call"


# ========================================
# Main Workflow Functions
# ========================================

def get_stm1_sheet():
    """
    Get the STM1 sheet from AACS workspace
    
    Returns:
        SmartsheetService instance
    """
    try:
        if STM1_SHEET_ID and STM1_SHEET_ID != 0:
            print(f"🔍 Using STM1 sheet ID: {STM1_SHEET_ID}")
            smartsheet_service = SmartsheetService(sheet_id=STM1_SHEET_ID)
            return smartsheet_service
        else:
            # Fallback: Try by name in workspace
            print(f"🔍 Looking for STM1 sheet: '{STM1_SHEET_NAME}' in workspace '{STM1_WORKSPACE_NAME}'")
            smartsheet_service = SmartsheetService(
                sheet_name=STM1_SHEET_NAME,
                workspace_name=STM1_WORKSPACE_NAME
            )
            return smartsheet_service
    except Exception as e:
        print(f"❌ Failed to get STM1 sheet: {e}")
        print(f"   Workspace: {STM1_WORKSPACE_NAME}")
        print(f"   Sheet Name: {STM1_SHEET_NAME}")
        raise


def get_stm1_customers_ready_for_calls(smartsheet_service):
    """
    Get all STM1 customers ready for calls today based on daily conditions
    
    Returns:
        list: List of customers ready for calls today
    """
    print("=" * 80)
    print("🔍 FETCHING STM1 CUSTOMERS READY FOR CALLS (Daily Condition-Based)")
    print("=" * 80)

    # Get all customers from sheet
    all_customers = smartsheet_service.get_all_customers_with_stages()

    # Use Pacific Time for "today" to ensure consistent behavior
    pacific_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific_tz).date()
    print(f"📅 Today (Pacific Time): {today}")
    print(f"📋 Calling mode: Daily condition-based (one call per day per customer)")

    ready_customers = []
    skipped_count = 0
    
    for customer in all_customers:
        # Initial validation
        should_skip, skip_reason = should_skip_stm1_row(customer)
        if should_skip:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: {skip_reason}")
            continue
        
        # Check if ready for calling based on daily conditions
        is_ready, ready_reason = is_stm1_ready_for_calling(customer, today)
        if not is_ready:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: {ready_reason}")
            continue
        
        ready_customers.append(customer)
        print(f"   ✅ Row {customer.get('row_number')}: Ready for STM1 call today")
    
    print(f"\n📊 Summary:")
    print(f"   Ready for calls: {len(ready_customers)} customers")
    print(f"   Skipped: {skipped_count} rows")
    
    return ready_customers


def update_after_stm1_call(smartsheet_service, customer, call_data):
    """
    Update Smartsheet after a successful STM1 call
    Uses the same call notes format as CL1 and N1 projects
    
    Args:
        smartsheet_service: SmartsheetService instance
        customer: Customer dict
        call_data: Call result data from VAPI
    """
    # Extract call analysis
    analysis = call_data.get('analysis', {})
    
    if not analysis:
        print(f"⚠️  WARNING: No analysis found in call_data")
        print(f"   Call data keys: {list(call_data.keys())}")
        if 'result' in call_data and isinstance(call_data['result'], dict):
            analysis = call_data['result'].get('analysis', {})
        if not analysis and 'call_data' in call_data:
            analysis = call_data['call_data'].get('analysis', {})
        if not analysis:
            print(f"   Analysis keys: {list(analysis.keys()) if analysis else 'N/A'}")
    
    # Check if this is a voicemail call
    ended_reason = call_data.get('endedReason', '')
    # Debug: Print endedReason for troubleshooting
    if not ended_reason:
        print(f"   ⚠️  WARNING: endedReason is empty or missing in call_data")
        print(f"   📋 Call data keys: {list(call_data.keys())}")
        # Try alternative locations
        if 'result' in call_data:
            ended_reason = call_data.get('result', {}).get('endedReason', '')
            print(f"   🔍 Found endedReason in result: {ended_reason}")
    else:
        print(f"   📋 endedReason: {ended_reason}")
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

    evaluation = str(evaluation).lower()

    # Format call summary for Call Notes column (same format as CL1 and N1)
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
    
    # Format call notes entry in required format (same as CL1 and N1)
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
    
    # Get existing call notes
    existing_notes = customer.get('call_notes', '') or customer.get('stm1_call_notes', '')
    
    # Append call notes entry to existing Call Notes (separate each call with separator)
    if existing_notes:
        new_call_notes = existing_notes + "\n---\n" + call_notes_entry
    else:
        new_call_notes = call_notes_entry

    # Get current date in Pacific Time for Last Call Made Date
    pacific_tz = ZoneInfo("America/Los_Angeles")
    current_date = datetime.now(pacific_tz).date()
    last_call_date_str = current_date.strftime('%Y-%m-%d')
    
    # Update "called times" counter (increment by 1)
    # Column name "called times" normalizes to "called_times" (plural - matches sheet)
    # Also check for singular "called_time" and "called time" for backward compatibility
    current_called_time = customer.get('called_times', '') or customer.get('called_time', '') or customer.get('called time', '') or '0'
    try:
        # Try to parse as integer
        called_time_count = int(str(current_called_time).strip()) if str(current_called_time).strip() else 0
    except (ValueError, TypeError):
        # If parsing fails, default to 0
        called_time_count = 0
    
    # Increment the count
    called_time_count += 1
    
    # Check if call was transferred
    # Transfer occurs when endedReason is 'assistant-forwarded-call'
    was_transferred = 'No'
    if ended_reason == 'assistant-forwarded-call':
        was_transferred = 'Yes'
        print(f"   🔄 Transfer detected! endedReason='{ended_reason}' -> was_transferred='{was_transferred}'")
    else:
        print(f"   📞 No transfer detected. endedReason='{ended_reason}' (expected 'assistant-forwarded-call' for transfer)")
    
    updates = {
        'call_notes': new_call_notes,  # Store formatted call notes (same format as CL1 and N1)
        'last_call_made_date': last_call_date_str,  # Record last call date (used to prevent duplicate calls same day)
        'called_times': str(called_time_count),  # Update call count (increment by 1) - use plural to match sheet
        'transferred_to_aacs_or_not': was_transferred,  # Record if call was transferred (Yes/No) - matches existing column
        'transfer': was_transferred,  # Alternative column name for transfer status
        'was_transferred': was_transferred,  # Another alternative column name
        'transfer_status': was_transferred,  # Another alternative column name
    }

    # Perform update
    success = smartsheet_service.update_customer_fields(customer, updates)

    if success:
        print(f"✅ Smartsheet updated successfully")
        print(f"   • Call Notes: Updated with formatted call notes (same format as CL1/N1)")
        print(f"   • Last Call Made Date: {last_call_date_str}")
        print(f"   • Called Times: Updated to {called_time_count} (incremented from {called_time_count - 1})")
        print(f"   • Transfer Status: {was_transferred} (endedReason: {ended_reason})")
        print(f"   • transferred_to_aacs_or_not column: Updated to '{was_transferred}'")
    else:
        print(f"❌ Smartsheet update failed")

    return success


# ========================================
# Error Logging and Reporting
# ========================================

class STM1WorkflowErrorLogger:
    """Error logger for STM1 workflow"""
    
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


def run_stm1_batch_calling(test_mode=False, schedule_at=None, auto_confirm=False):
    """
    Main function to run STM1 batch calling with comprehensive error handling
    
    Args:
        test_mode: If True, skip actual calls and Smartsheet updates (default: False)
        schedule_at: Optional datetime to schedule calls
        auto_confirm: If True, skip user confirmation prompt (for cron jobs) (default: False)
    """
    # Initialize error logger
    error_logger = STM1WorkflowErrorLogger()
    
    print("=" * 80)
    print("🚀 STM1 PROJECT - STATEMENT CALL BATCH CALLING SYSTEM")
    print("📋 Workspace: AACS")
    print("📄 Sheet: Insured Driver Statement")
    if test_mode:
        print("🧪 TEST MODE - No actual calls or updates will be made")
    if schedule_at:
        print(f"⏰ SCHEDULED MODE - Calls will be scheduled for {schedule_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("📋 STM1 Project: Statement Call automated calling workflow (Daily Condition-Based)")
    
    # Check if assistant ID is configured
    if not STM1_ASSISTANT_ID:
        error_logger.log_error({}, 0, 'CONFIGURATION_ERROR', "STM1_ASSISTANT_ID is not configured. Please configure it in config/settings.py")
        return False
    
    print(f"📞 Calling mode: Daily condition-based (one call per day per customer)")
    print(f"🤖 Assistant ID: {STM1_ASSISTANT_ID}")
    print(f"⏰ Calling hours: {STM1_CALLING_START_HOUR}:00 AM - {STM1_CALLING_END_HOUR}:00 PM Pacific Time")
    print("=" * 80)
    
    # Check if current time is within calling hours
    pacific_tz = ZoneInfo("America/Los_Angeles")
    now_pacific = datetime.now(pacific_tz)
    current_hour = now_pacific.hour
    
    # Check if scheduling for a specific time
    if schedule_at:
        # Ensure schedule_at is in Pacific timezone
        if schedule_at.tzinfo is None:
            schedule_at = schedule_at.replace(tzinfo=pacific_tz)
        elif schedule_at.tzinfo != pacific_tz:
            schedule_at = schedule_at.astimezone(pacific_tz)
        
        schedule_hour = schedule_at.hour
        schedule_date = schedule_at.date()
        today = now_pacific.date()
        
        # Check if scheduled time is within calling hours
        if schedule_date != today:
            print(f"\n⏰ Cannot schedule calls for a different date")
            print(f"   Scheduled date: {schedule_date}")
            print(f"   Today: {today}")
            return False
        
        if schedule_hour < STM1_CALLING_START_HOUR or schedule_hour >= STM1_CALLING_END_HOUR:
            print(f"\n⏰ Scheduled time is outside calling hours ({STM1_CALLING_START_HOUR}:00 - {STM1_CALLING_END_HOUR}:00 Pacific Time)")
            print(f"   Scheduled time: {schedule_at.strftime('%I:%M %p %Z')}")
            print(f"   STM1 calls can only be made between {STM1_CALLING_START_HOUR}:00 AM and {STM1_CALLING_END_HOUR}:00 PM Pacific Time")
            return False
        
        # Safety check: Don't schedule calls too close to end time (within last 5 minutes)
        if schedule_hour == STM1_CALLING_END_HOUR - 1:
            schedule_minute = schedule_at.minute
            if schedule_minute >= 55:  # 4:55 PM or later
                print(f"\n⏰ Scheduled time is too close to end of calling hours")
                print(f"   Scheduled time: {schedule_at.strftime('%I:%M %p %Z')}")
                print(f"   Calling hours end at {STM1_CALLING_END_HOUR}:00 PM Pacific Time")
                print(f"   Please schedule calls for earlier in the day")
                return False
        
        print(f"✅ Scheduled time: {schedule_at.strftime('%I:%M %p %Z')} - Within calling hours")
    else:
        # For immediate calls, check current time
        if current_hour < STM1_CALLING_START_HOUR or current_hour >= STM1_CALLING_END_HOUR:
            print(f"\n⏰ Outside calling hours ({STM1_CALLING_START_HOUR}:00 - {STM1_CALLING_END_HOUR}:00 Pacific Time)")
            print(f"   Current time: {now_pacific.strftime('%I:%M %p %Z')}")
            print(f"   STM1 calls can only be made between {STM1_CALLING_START_HOUR}:00 AM and {STM1_CALLING_END_HOUR}:00 PM Pacific Time")
            print(f"   Please run again during calling hours or schedule calls for later")
            return False
        
        # Safety check: Don't start calls too close to end time (within last 5 minutes)
        # This ensures calls have time to complete before 5 PM
        if current_hour == STM1_CALLING_END_HOUR - 1:
            current_minute = now_pacific.minute
            if current_minute >= 55:  # 4:55 PM or later
                print(f"\n⏰ Too close to end of calling hours")
                print(f"   Current time: {now_pacific.strftime('%I:%M %p %Z')}")
                print(f"   Calling hours end at {STM1_CALLING_END_HOUR}:00 PM Pacific Time")
                print(f"   Please schedule calls for earlier in the day or wait until tomorrow")
                return False
        
        print(f"✅ Current time: {now_pacific.strftime('%I:%M %p %Z')} - Within calling hours")
    
    print()
    
    try:
        # Initialize services
        smartsheet_service = get_stm1_sheet()
        # Use STM1 dedicated phone number for caller ID
        vapi_service = VAPIService(phone_number_id=STM1_PHONE_NUMBER_ID)
    except Exception as e:
        error_logger.log_error({}, 0, 'INITIALIZATION_ERROR', f"Failed to initialize services: {e}", e)
        return False
    
    # Get customers ready for calls today
    ready_customers = get_stm1_customers_ready_for_calls(smartsheet_service)
    
    total_customers = len(ready_customers)
    
    if total_customers == 0:
        print("\n✅ No STM1 customers ready for calls today")
        return True
    
    # Apply daily call limit
    if STM1_MAX_DAILY_CALLS and total_customers > STM1_MAX_DAILY_CALLS:
        print(f"\n⚠️  Daily call limit applied: {total_customers} ready customers limited to {STM1_MAX_DAILY_CALLS} calls")
        ready_customers = ready_customers[:STM1_MAX_DAILY_CALLS]
        total_customers = len(ready_customers)
        print(f"📊 Processing first {total_customers} customers (remaining will be processed on subsequent days)")
    else:
        print(f"\n📊 All {total_customers} ready customers will be processed today")
    
    # Show summary and ask for confirmation
    print(f"\n{'=' * 80}")
    print(f"📊 STM1 CUSTOMERS READY FOR CALLS TODAY:")
    print(f"{'=' * 80}")
    print(f"\n🔔 Ready customers: {total_customers}")
    print(f"   🤖 Assistant ID: {STM1_ASSISTANT_ID}")
    
    for i, customer in enumerate(ready_customers[:10], 1):
        company = customer.get('company', 'Unknown') or customer.get('insured_name', 'Unknown')
        phone = customer.get('phone_number', '') or customer.get('contact_phone', '')
        print(f"   {i}. {company} - {phone}")
    
    if len(ready_customers) > 10:
        print(f"   ... and {len(ready_customers) - 10} more")
    
    print(f"\n{'=' * 80}")
    if not test_mode:
        print(f"⚠️  WARNING: This will make {total_customers} STM1 phone calls!")
        print(f"💰 This will incur charges for each call")
    else:
        print(f"🧪 TEST MODE: Will simulate {total_customers} STM1 calls (no charges)")
    print(f"{'=' * 80}")

    # Only ask for confirmation if not auto_confirm and not test_mode
    if not test_mode and not auto_confirm:
        response = input(f"\nProceed with STM1 batch calling? (y/N): ").strip().lower()

        if response not in ['y', 'yes']:
            print("❌ STM1 batch calling cancelled")
            return False
    elif auto_confirm:
        print(f"🤖 AUTO-CONFIRM: Proceeding automatically (cron mode)")
    
    # Process all ready customers
    total_success = 0
    total_failed = 0

    print(f"\n{'=' * 80}")
    print(f"📞 STM1 CALLING - {total_customers} customers")
    print(f"🤖 Using Assistant: {STM1_ASSISTANT_ID}")
    print(f"📱 Using Phone Number ID: {STM1_PHONE_NUMBER_ID}")
    print(f"{'=' * 80}")

    if test_mode:
        # Test mode: Simulate calls without actual API calls
        print(f"\n🧪 TEST MODE: Simulating {total_customers} STM1 calls...")
        for customer in ready_customers:
            company = customer.get('company', 'Unknown') or customer.get('insured_name', 'Unknown')
            phone = customer.get('phone_number', '') or customer.get('contact_phone', '')
            print(f"   ✅ [SIMULATED] Would call: {company} - {phone}")
            total_success += 1
    else:
        # Batch calling (all customers simultaneously)
        print(f"📦 Batch calling mode (simultaneous)")
        # Validate customers before calling
        validated_customers = []
        for customer in ready_customers:
            is_valid, error_msg, validated_data = validate_stm1_customer_data(customer)
            if is_valid:
                customer_for_call = {**customer, **validated_data}
                validated_customers.append(customer_for_call)
            else:
                error_logger.log_validation_failure(customer, error_msg)
                error_logger.log_warning(customer, 0, 'VALIDATION_FAILED', error_msg)
                total_failed += 1
        
        if not validated_customers:
            print(f"\n⚠️  No valid customers after validation")
        else:
            try:
                # Use STM1-specific variable builder for VAPI assistant
                results = vapi_service.make_batch_call_with_assistant(
                    validated_customers,
                    STM1_ASSISTANT_ID,
                    schedule_immediately=(schedule_at is None),
                    schedule_at=schedule_at,
                    custom_variable_builder=build_stm1_variable_values
                )

                if results:
                    print(f"\n✅ STM1 batch calls completed")
                    print(f"   📊 Received {len(results)} call result(s) for {len(validated_customers)} customer(s)")

                    # Only update Smartsheet if calls were immediate (not scheduled)
                    if schedule_at is None:
                        for i, customer in enumerate(validated_customers):
                            if i < len(results):
                                call_data = results[i]
                            else:
                                call_data = results[0] if results else None
                            
                            if call_data:
                                if 'analysis' not in call_data or not call_data.get('analysis'):
                                    company = customer.get('company', 'Unknown') or customer.get('insured_name', 'Unknown')
                                    print(f"   ⚠️  Customer {i+1} ({company}): No analysis in call_data")
                                    if 'id' in call_data:
                                        call_id = call_data['id']
                                        try:
                                            refreshed_data = vapi_service.check_call_status(call_id)
                                            if refreshed_data and refreshed_data.get('analysis'):
                                                call_data = refreshed_data
                                                print(f"      ✅ Successfully retrieved analysis from refreshed call status")
                                        except Exception as e:
                                            print(f"      ❌ Failed to refresh call status: {e}")
                                
                                try:
                                    success = update_after_stm1_call(smartsheet_service, customer, call_data)
                                    if success:
                                        total_success += 1
                                    else:
                                        error_logger.log_error(customer, 0, 'SMARTSHEET_UPDATE_FAILED', "Failed to update Smartsheet after call")
                                        total_failed += 1
                                except Exception as e:
                                    error_logger.log_error(customer, 0, 'SMARTSHEET_UPDATE_ERROR', f"Exception during Smartsheet update: {e}", e)
                                    total_failed += 1
                            else:
                                error_logger.log_error(customer, 0, 'VAPI_CALL_FAILED', "VAPI call returned no data")
                                total_failed += 1
                    else:
                        print(f"   ⏰ Calls scheduled - Smartsheet will be updated after calls complete")
                        total_success += len(validated_customers)
                else:
                    print(f"\n❌ STM1 batch calls failed")
                    for customer in validated_customers:
                        error_logger.log_error(customer, 0, 'VAPI_CALL_FAILED', "VAPI API returned no results")
                    total_failed += len(validated_customers)
            except Exception as e:
                print(f"\n❌ STM1 batch calls failed with exception")
                for customer in validated_customers:
                    error_logger.log_error(customer, 0, 'VAPI_CALL_EXCEPTION', f"Exception during VAPI call: {e}", e)
                total_failed += len(validated_customers)
    
    # Final summary
    print(f"\n{'=' * 80}")
    print(f"🏁 STM1 BATCH CALLING COMPLETE")
    print(f"{'=' * 80}")
    print(f"   ✅ Successful: {total_success}")
    print(f"   ❌ Failed: {total_failed}")
    print(f"   📊 Total: {total_success + total_failed}")
    print(f"{'=' * 80}")
    
    # Print error summary
    if error_logger.errors or error_logger.warnings or error_logger.validation_failures:
        error_logger.print_summary()
    
    return True


# ========================================
# Entry Point
# ========================================

if __name__ == "__main__":
    import sys

    # Check if test mode is requested
    test_mode = "--test" in sys.argv or "-t" in sys.argv

    run_stm1_batch_calling(test_mode=test_mode)

