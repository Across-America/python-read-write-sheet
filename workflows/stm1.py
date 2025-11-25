"""
STM1 Project Workflow
Statement Call Workflow - All American Claims workspace
Automated calling workflow for STM1 project

Note: This workflow implements a multi-stage calling system for STM1 project.
Uses the "statements call" sheet in the "All American Claims" workspace.
"""

from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from services import VAPIService, SmartsheetService
from config import (
    STM1_1ST_REMINDER_ASSISTANT_ID,
    STM1_2ND_REMINDER_ASSISTANT_ID,
    STM1_3RD_REMINDER_ASSISTANT_ID,
    STM1_SHEET_ID,
    STM1_WORKSPACE_NAME,
    STM1_SHEET_NAME,
    STM1_CALLING_SCHEDULE,
    STM1_CALLING_START_DAY
)
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
    # Use insured_name column from STM1 sheet (statements call)
    company = customer.get('insured_name', '').strip() or customer.get('company', '').strip()
    if not company:
        errors.append("Insured name is empty")
    else:
        validated['company'] = company
        validated['insured_name'] = company
    
    # Use contact_phone column from STM1 sheet
    phone_field = customer.get('contact_phone', '') or customer.get('client_phone_number', '') or customer.get('phone_number', '')
    phone = phone_field.strip()
    if not phone:
        errors.append("Phone number is empty")
    else:
        # Basic phone validation (should start with + or be numeric)
        if not (phone.startswith('+') or phone.replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit()):
            errors.append(f"Invalid phone number format: {phone}")
        else:
            validated['phone_number'] = phone
    
    # Use due_date or current_due_date column from STM1 sheet
    target_date_field = customer.get('due_date', '') or customer.get('current_due_date', '') or customer.get('target_date', '') or customer.get('expiration_date', '')
    if not target_date_field:
        errors.append("Due date is empty")
    else:
        target_date = parse_date(target_date_field)
        if not target_date:
            errors.append(f"Invalid date format: {target_date_field}")
        else:
            validated['target_date'] = target_date
            validated['target_date_str'] = target_date_field
            validated['due_date'] = target_date
    
    # TODO: Add STM1-specific status/condition validation
    # Example: status, payee, or other filtering conditions
    
    if errors:
        return False, "; ".join(errors), None
    
    return True, "", validated


def should_skip_stm1_row(customer):
    """
    Check if a STM1 row should be skipped
    
    TODO: Customize filtering logic based on STM1 requirements
    
    Skip if ANY of:
    - done is checked/true
    - company is empty
    - phone_number is empty
    - target_date is empty or invalid
    - Other STM1-specific conditions
    
    Args:
        customer: Customer dict
        
    Returns:
        tuple: (should_skip: bool, reason: str)
    """
    # Check done checkbox
    if customer.get('done?') in [True, 'true', 'True', 1]:
        return True, "Done checkbox is checked"

    # Check required fields
    # Use insured_name column from STM1 sheet
    insured_name = customer.get('insured_name', '').strip() or customer.get('company', '').strip()
    if not insured_name:
        return True, "Insured name is empty"

    # Use contact_phone column from STM1 sheet
    phone_field = customer.get('contact_phone', '') or customer.get('client_phone_number', '') or customer.get('phone_number', '')
    if not phone_field.strip():
        return True, "Phone number is empty"

    # Check due date - use due_date or current_due_date column from STM1 sheet
    target_date_field = customer.get('due_date', '') or customer.get('current_due_date', '') or customer.get('target_date', '') or customer.get('expiration_date', '')
    if not target_date_field:
        return True, "Due date is empty"
    
    # TODO: Add STM1-specific filtering conditions
    # Example:
    # status = str(customer.get('status', '')).strip().lower()
    # if 'some_status' not in status:
    #     return True, f"Status does not match requirement: {status}"
    
    return False, ""


def get_stm1_stage(customer):
    """
    Get the current STM1 call stage for a customer
    
    Returns:
        int: Stage number (0 for empty/null, 1, 2, 3+)
    """
    # Try multiple possible column names (normalized)
    stage = customer.get('stage', '') or customer.get('stm1_call_stage', '')
    
    if not stage or stage == '' or stage is None:
        return 0
    
    try:
        return int(stage)
    except (ValueError, TypeError):
        return 0


def get_stm1_assistant_id_for_stage(stage):
    """Get the appropriate assistant ID for a given STM1 call stage"""
    assistant_map = {
        0: STM1_1ST_REMINDER_ASSISTANT_ID,  # 1st Reminder
        1: STM1_2ND_REMINDER_ASSISTANT_ID,  # 2nd Reminder
        2: STM1_3RD_REMINDER_ASSISTANT_ID   # 3rd Reminder
    }
    
    return assistant_map.get(stage)


# ========================================
# STM1 Timeline Logic
# ========================================

def is_stm1_ready_for_calling(customer, today):
    """
    Check if a STM1 customer is ready for calling based on timeline logic
    
    Args:
        customer: Customer dict
        today: Current date
        
    Returns:
        tuple: (is_ready: bool, reason: str, stage: int)
    """
    # Parse target date from sheet - use due_date or current_due_date column
    target_date_str = customer.get('due_date', '') or customer.get('current_due_date', '') or customer.get('target_date', '') or customer.get('expiration_date', '')
    target_date = parse_date(target_date_str)
    
    if not target_date:
        return False, "Invalid target date", -1
    
    # Calculate days until target date
    days_until_target = (target_date - today).days
    
    # Check if we should stop calling (past target date)
    if days_until_target < 0:
        return False, f"Target date passed ({abs(days_until_target)} days ago)", -1
    
    # Check if it's the right day of month to start calling
    if today.day < STM1_CALLING_START_DAY:
        return False, f"Not yet calling day (start on day {STM1_CALLING_START_DAY})", -1
    
    # Check if today matches any of the calling schedule days
    for stage, days_before in enumerate(STM1_CALLING_SCHEDULE):
        if days_until_target == days_before:
            return True, f"Ready for stage {stage} call ({days_before} days before target)", stage
    
    # Check if we're within the calling window but not on a scheduled day
    if days_until_target <= max(STM1_CALLING_SCHEDULE):
        return False, f"Within calling window but not on scheduled day (target in {days_until_target} days)", -1
    
    return False, f"Too early to call (target in {days_until_target} days)", -1


def calculate_stm1_next_followup_date(customer, current_stage):
    """
    Calculate the next follow-up date for STM1 calls
    Based on the fixed schedule defined in STM1_CALLING_SCHEDULE
    
    Args:
        customer: Customer dict
        current_stage: Current call stage (0, 1, 2, etc.)
    
    Returns:
        date or None: Next follow-up date
    """
    target_date_str = customer.get('due_date', '') or customer.get('current_due_date', '') or customer.get('target_date', '') or customer.get('expiration_date', '')
    target_date = parse_date(target_date_str)
    
    if not target_date:
        print(f"   ⚠️  Invalid target date: {target_date_str}")
        return None
    
    # Fixed schedule based on STM1_CALLING_SCHEDULE
    if current_stage < len(STM1_CALLING_SCHEDULE) - 1:
        next_stage = current_stage + 1
        days_before_target = STM1_CALLING_SCHEDULE[next_stage]
        next_date = target_date - timedelta(days=days_before_target)
        
        stage_names = ["1st", "2nd", "3rd"]
        stage_name = stage_names[next_stage] if next_stage < len(stage_names) else f"{next_stage + 1}th"
        print(f"   📅 Stage {current_stage}→{next_stage}: Next call ({stage_name} reminder) on {next_date}")
        
        return next_date
    else:
        # Final stage - no more follow-ups
        print(f"   📅 Stage {current_stage}: Final call - no more follow-ups")
        return None


# ========================================
# Main Workflow Functions
# ========================================

def get_stm1_sheet():
    """
    Get the STM1 sheet from All American Claims workspace
    
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
    Get all STM1 customers ready for calls today based on timeline logic
    
    Returns:
        dict: Customers grouped by stage {0: [...], 1: [...], 2: [...]}
    """
    print("=" * 80)
    print("🔍 FETCHING STM1 CUSTOMERS READY FOR CALLS")
    print("=" * 80)

    # Check if configuration is set
    if STM1_CALLING_SCHEDULE is None:
        raise ValueError("STM1_CALLING_SCHEDULE is not configured. Please configure it in config/settings.py")
    if STM1_CALLING_START_DAY is None:
        raise ValueError("STM1_CALLING_START_DAY is not configured. Please configure it in config/settings.py")

    # Get all customers from sheet
    all_customers = smartsheet_service.get_all_customers_with_stages()

    # Use Pacific Time for "today" to ensure consistent behavior
    pacific_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific_tz).date()
    print(f"📅 Today (Pacific Time): {today}")
    print(f"⏰ Calling schedule: {STM1_CALLING_SCHEDULE} days before target")
    print(f"📅 Start calling on day: {STM1_CALLING_START_DAY} of each month")

    num_stages = len(STM1_CALLING_SCHEDULE)
    customers_by_stage = {i: [] for i in range(num_stages)}
    skipped_count = 0
    
    for customer in all_customers:
        # Initial validation
        should_skip, skip_reason = should_skip_stm1_row(customer)
        if should_skip:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: {skip_reason}")
            continue
        
        # Get current stage
        current_stage = get_stm1_stage(customer)
        
        # Skip if stage >= num_stages (call sequence complete)
        if current_stage >= num_stages:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: STM1 sequence complete (stage {current_stage})")
            continue
        
        # Check if ready for calling based on timeline
        is_ready, ready_reason, target_stage = is_stm1_ready_for_calling(customer, today)
        if not is_ready:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: {ready_reason}")
            continue
        
        # Check if the customer is at the right stage for today's call
        # Allow auto-adjustment if customer missed earlier stages
        if current_stage != target_stage:
            if current_stage < target_stage:
                # Customer missed earlier stages - allow auto-adjustment
                print(f"   ⚠️  Row {customer.get('row_number')}: Auto-adjusting stage {current_stage} → {target_stage} (missed earlier stages)")
            else:
                # Customer already passed this stage - skip
                skipped_count += 1
                print(f"   ⏭️  Skipping row {customer.get('row_number')}: Already past this stage (current: {current_stage}, needed: {target_stage})")
                continue
        
        customers_by_stage[target_stage].append(customer)
        stage_names = ["1st", "2nd", "3rd"]
        stage_name = stage_names[target_stage] if target_stage < len(stage_names) else f"{target_stage + 1}th"
        print(f"   ✅ Row {customer.get('row_number')}: Stage {target_stage} ({stage_name} reminder), ready for STM1 call")
    
    print(f"\n📊 Summary:")
    for stage in range(num_stages):
        stage_names = ["1st", "2nd", "3rd"]
        stage_name = stage_names[stage] if stage < len(stage_names) else f"{stage + 1}th"
        print(f"   Stage {stage} ({stage_name} reminder): {len(customers_by_stage[stage])} customers")
    print(f"   Skipped: {skipped_count} rows")
    print(f"   Total ready: {sum(len(v) for v in customers_by_stage.values())}")
    
    return customers_by_stage


def format_stm1_call_entry(summary, evaluation, call_number):
    """Format a STM1 call entry for appending"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entry = f"[STM1 Call {call_number} - {timestamp}]\n{summary}\n"
    eval_entry = f"[STM1 Call {call_number} - {timestamp}]\n{evaluation}\n"
    return entry, eval_entry


def update_after_stm1_call(smartsheet_service, customer, call_data, call_stage):
    """
    Update Smartsheet after a successful STM1 call
    
    Args:
        smartsheet_service: SmartsheetService instance
        customer: Customer dict
        call_data: Call result data from VAPI
        call_stage: Stage at which the call was made
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
    
    summary = analysis.get('summary', '') if analysis else ''
    if not summary or summary == '':
        if analysis:
            summary = analysis.get('transcript', '') or analysis.get('summaryText', '') or 'No summary available'
        else:
            summary = 'No summary available'
        if summary == 'No summary available':
            print(f"⚠️  WARNING: No summary found in analysis")

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

    # Calculate next followup date
    next_followup_date = calculate_stm1_next_followup_date(customer, call_stage)

    # Format entries for appending
    call_number = call_stage + 1
    summary_entry, eval_entry = format_stm1_call_entry(summary, evaluation, call_number)

    # Format call summary for Call Notes column
    timestamp = datetime.now(ZoneInfo("America/Los_Angeles")).strftime('%Y-%m-%d %H:%M:%S')
    call_notes_entry = f"[STM1 Call #{call_number} - {timestamp}]\n{summary}\n"
    
    # Get existing call notes
    existing_notes = customer.get('call_notes', '') or customer.get('stm1_call_notes', '')
    
    # Append summary to existing notes
    if existing_notes:
        new_call_notes = existing_notes + "\n---\n" + call_notes_entry
    else:
        new_call_notes = call_notes_entry

    # Get current date in Pacific Time for Last Call Made Date
    pacific_tz = ZoneInfo("America/Los_Angeles")
    current_date = datetime.now(pacific_tz).date()
    last_call_date_str = current_date.strftime('%Y-%m-%d')
    
    updates = {
        'stage': new_stage,  # Use "Stage" column
        'call_notes': new_call_notes,  # Store summary in Call Notes
        'last_call_made_date': last_call_date_str,  # Record last call date
    }

    if next_followup_date:
        updates['f_u_date'] = next_followup_date.strftime('%Y-%m-%d')  # Use "F/U Date" column

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
    print("📋 Workspace: All American Claims")
    print("📄 Sheet: statements call")
    if test_mode:
        print("🧪 TEST MODE - No actual calls or updates will be made")
    if schedule_at:
        print(f"⏰ SCHEDULED MODE - Calls will be scheduled for {schedule_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("📋 STM1 Project: Statement Call automated calling workflow")
    
    # Check if configuration is set
    if STM1_CALLING_SCHEDULE is None:
        error_logger.log_error({}, 0, 'CONFIGURATION_ERROR', "STM1_CALLING_SCHEDULE is not configured. Please configure it in config/settings.py")
        return False
    if STM1_CALLING_START_DAY is None:
        error_logger.log_error({}, 0, 'CONFIGURATION_ERROR', "STM1_CALLING_START_DAY is not configured. Please configure it in config/settings.py")
        return False
    
    print(f"📞 {len(STM1_CALLING_SCHEDULE)}-stage calling: {', '.join([f'{d} days before' for d in STM1_CALLING_SCHEDULE])}")
    print("=" * 80)
    
    try:
        # Initialize services
        smartsheet_service = get_stm1_sheet()
        vapi_service = VAPIService()
    except Exception as e:
        error_logger.log_error({}, 0, 'INITIALIZATION_ERROR', f"Failed to initialize services: {e}", e)
        return False
    
    # Get customers grouped by stage
    customers_by_stage = get_stm1_customers_ready_for_calls(smartsheet_service)
    
    total_customers = sum(len(v) for v in customers_by_stage.values())
    
    if total_customers == 0:
        print("\n✅ No STM1 customers ready for calls today")
        return True
    
    # Show summary and ask for confirmation
    print(f"\n{'=' * 80}")
    print(f"📊 STM1 CUSTOMERS READY FOR CALLS TODAY:")
    print(f"{'=' * 80}")
    
    num_stages = len(STM1_CALLING_SCHEDULE)
    for stage in range(num_stages):
        customers = customers_by_stage[stage]
        if customers:
            stage_names = ["1st", "2nd", "3rd"]
            stage_name = stage_names[stage] if stage < len(stage_names) else f"{stage + 1}th"
            assistant_id = get_stm1_assistant_id_for_stage(stage)
            print(f"\n🔔 Stage {stage} ({stage_name} Reminder) - {len(customers)} customers:")
            print(f"   🤖 Assistant ID: {assistant_id}")
            
            for i, customer in enumerate(customers[:5], 1):
                print(f"   {i}. {customer.get('company', 'Unknown')} - {customer.get('phone_number')}")
            
            if len(customers) > 5:
                print(f"   ... and {len(customers) - 5} more")
    
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
    
    # Process each stage
    total_success = 0
    total_failed = 0

    for stage in range(num_stages):
        customers = customers_by_stage[stage]

        if not customers:
            continue

        stage_names = ["1st", "2nd", "3rd"]
        stage_name = stage_names[stage] if stage < len(stage_names) else f"{stage + 1}th"
        assistant_id = get_stm1_assistant_id_for_stage(stage)

        print(f"\n{'=' * 80}")
        print(f"📞 STM1 CALLING STAGE {stage} ({stage_name} Reminder) - {len(customers)} customers")
        print(f"🤖 Using Assistant: {assistant_id}")
        print(f"{'=' * 80}")

        if test_mode:
            # Test mode: Simulate calls without actual API calls
            print(f"\n🧪 TEST MODE: Simulating {len(customers)} STM1 calls...")
            for customer in customers:
                print(f"   ✅ [SIMULATED] Would call: {customer.get('company', 'Unknown')} - {customer.get('phone_number')}")
                total_success += 1
        else:
            # Stage 0: Batch calling (all customers simultaneously)
            if stage == 0:
                print(f"📦 Batch calling mode (simultaneous)")
                # Validate customers before calling
                validated_customers = []
                for customer in customers:
                    is_valid, error_msg, validated_data = validate_stm1_customer_data(customer)
                    if is_valid:
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
                        print(f"\n✅ Stage {stage} STM1 batch calls completed")
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
                                        print(f"   ⚠️  Customer {i+1} ({customer.get('company', 'Unknown')}): No analysis in call_data")
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
                                        success = update_after_stm1_call(smartsheet_service, customer, call_data, stage)
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
                        print(f"\n❌ Stage {stage} STM1 batch calls failed")
                        for customer in validated_customers:
                            error_logger.log_error(customer, stage, 'VAPI_CALL_FAILED', "VAPI API returned no results")
                        total_failed += len(validated_customers)
                except Exception as e:
                    print(f"\n❌ Stage {stage} STM1 batch calls failed with exception")
                    for customer in validated_customers:
                        error_logger.log_error(customer, stage, 'VAPI_CALL_EXCEPTION', f"Exception during VAPI call: {e}", e)
                    total_failed += len(validated_customers)

            # Stage 1+: Sequential calling (one customer at a time)
            else:
                print(f"🔄 Sequential calling mode (one at a time)")

                for i, customer in enumerate(customers, 1):
                    print(f"\n   📞 Call {i}/{len(customers)}: {customer.get('company', 'Unknown')}")

                    # Validate customer before calling
                    is_valid, error_msg, validated_data = validate_stm1_customer_data(customer)
                    if not is_valid:
                        error_logger.log_validation_failure(customer, error_msg)
                        error_logger.log_warning(customer, stage, 'VALIDATION_FAILED', error_msg)
                        total_failed += 1
                        continue

                    customer_for_call = {**customer, **validated_data}

                    try:
                        results = vapi_service.make_batch_call_with_assistant(
                            [customer_for_call],
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
                                    except Exception as e:
                                        print(f"   ❌ Failed to refresh call status: {e}")

                            # Only update Smartsheet if calls were immediate (not scheduled)
                            if schedule_at is None:
                                try:
                                    success = update_after_stm1_call(smartsheet_service, customer, call_data, stage)
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

                print(f"\n✅ Stage {stage} STM1 sequential calls completed")
    
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

