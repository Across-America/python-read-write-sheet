"""
N1 Project - Renewal Workflow
Personal Line Policy Renewal Notifications
Implements renewal calling system with dynamic sheet discovery and configurable timeline

Note: This workflow is part of the N1 Project, which includes two workflows based on the renewal sheet:
- Renewal Workflow (this file)
- Non-Renewal Workflow
"""

from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from services import VAPIService, SmartsheetService
from config import (
    RENEWAL_1ST_REMINDER_ASSISTANT_ID,
    RENEWAL_2ND_REMINDER_ASSISTANT_ID,
    RENEWAL_3RD_REMINDER_ASSISTANT_ID,
    RENEWAL_WORKSPACE_NAME,
    RENEWAL_SHEET_NAME_PATTERN,
    RENEWAL_PLR_SHEET_ID,
    RENEWAL_PLR_SHEET_NAME_PATTERN,
    RENEWAL_CALLING_SCHEDULE,
    RENEWAL_CALLING_START_DAY,
    MORTGAGE_BILL_1ST_REMAINDER_ASSISTANT_ID,
    MORTGAGE_BILL_2ND_REMAINDER_ASSISTANT_ID,
    SMARTSHEET_ACCESS_TOKEN
)
import math
import logging
from typing import List, Dict, Optional, Tuple


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

def get_renewal_sheet_by_date(year=None, month=None):
    """
    Get a renewal sheet by year and month
    
    Args:
        year: Year (e.g., 2026). If None, uses current year
        month: Month number (1-12). If None, uses current month
    
    Returns:
        SmartsheetService instance
    
    Location: ASI -> Personal Line -> Task Prototype -> Renewal / Non-Renewal -> {year} -> {month}. {month_name} PLR
    """
    from datetime import datetime
    import smartsheet
    
    # Use current date if not specified
    now = datetime.now()
    target_year = year if year else now.year
    target_month = month if month else now.month
    
    # Validate month
    if target_month < 1 or target_month > 12:
        raise ValueError(f"Invalid month: {target_month}. Month must be between 1 and 12.")
    
    try:
        smart = smartsheet.Smartsheet(access_token=SMARTSHEET_ACCESS_TOKEN)
        smart.errors_as_exceptions(True)
        
        # Find workspace
        workspaces = smart.Workspaces.list_workspaces(pagination_type='token').data
        workspace_id = None
        for ws in workspaces:
            if ws.name.lower() == RENEWAL_WORKSPACE_NAME.lower():
                workspace_id = ws.id
                break
        
        if not workspace_id:
            raise ValueError(f"Workspace '{RENEWAL_WORKSPACE_NAME}' not found")
        
        # Navigate to year folder
        workspace = smart.Workspaces.get_workspace(workspace_id, load_all=True)
        folder_path = ["Personal Line", "Task Prototype", "Renewal / Non-Renewal", str(target_year)]
        
        current = workspace
        for folder_name in folder_path:
            if hasattr(current, 'folders'):
                folders = current.folders
            else:
                folder_details = smart.Folders.get_folder(current.id)
                folders = folder_details.folders if hasattr(folder_details, 'folders') else []
            
            found = False
            for folder in folders:
                if folder.name.lower() == folder_name.lower():
                    if folder_name == str(target_year):
                        # Found year folder, now find the sheet
                        folder_details = smart.Folders.get_folder(folder.id)
                        month_names = [
                            "January", "February", "March", "April", "May", "June",
                            "July", "August", "September", "October", "November", "December"
                        ]
                        month_name = month_names[target_month - 1]
                        
                        # Try different naming patterns
                        patterns = [
                            f"{target_month}. {month_name} PLR",
                            f"{target_month:02d}. {month_name} PLR",
                            f"{month_name} PLR",
                        ]
                        
                        if hasattr(folder_details, 'sheets') and folder_details.sheets:
                            for sheet in folder_details.sheets:
                                sheet_name_lower = sheet.name.lower()
                                for pattern in patterns:
                                    if pattern.lower() in sheet_name_lower:
                                        print(f"✅ Found sheet: '{sheet.name}' (ID: {sheet.id})")
                                        return SmartsheetService(sheet_id=sheet.id)
                        
                        raise ValueError(f"Sheet for {month_name} {target_year} not found in folder")
                    
                    folder_details = smart.Folders.get_folder(folder.id)
                    current = folder_details
                    found = True
                    break
            
            if not found:
                raise ValueError(f"Folder '{folder_name}' not found in path")
        
        raise ValueError(f"Year folder '{target_year}' not found")
    
    except Exception as e:
        print(f"❌ Error finding sheet for {target_year}-{target_month:02d}: {e}")
        raise


def get_current_renewal_sheet():
    """
    Get the current month's renewal sheet
    
    Current Sheet: "11. November PLR" (production sheet)
    Location: ASI -> Personal Line -> Task Prototype -> Renewal/Non-renewal -> {month} PLR
    
    Note: The sheet name pattern is "{month_number}. {month_name} PLR" (e.g., "11. November PLR")
    """
    from datetime import datetime
    
    # Try using sheet ID first (faster and more reliable)
    try:
        print(f"🔍 Using sheet ID: {RENEWAL_PLR_SHEET_ID}")
        smartsheet_service = SmartsheetService(sheet_id=RENEWAL_PLR_SHEET_ID)
        return smartsheet_service
    except Exception as e:
        print(f"⚠️  Failed to use sheet ID, trying dynamic discovery: {e}")
    
    # Fallback: Try dynamic discovery by name
    # Get current month in format "11. November"
    month_number = datetime.now().strftime("%-m")  # 11 (no leading zero)
    month_name = datetime.now().strftime("%B")  # November
    sheet_name = RENEWAL_PLR_SHEET_NAME_PATTERN.format(
        month_number=month_number,
        month_name=month_name
    )
    
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

def validate_renewal_customer_data(customer):
    """
    Comprehensive data validation for renewal customer
    
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
            # Use Pacific timezone for consistent date comparison
            from datetime import date
            from zoneinfo import ZoneInfo
            pacific_tz = ZoneInfo("America/Los_Angeles")
            today_pacific = datetime.now(pacific_tz).date()
            if expiry_date < today_pacific:
                errors.append(f"Policy already expired: {expiry_date}")
            else:
                validated['expiration_date'] = expiry_date
                validated['expiration_date_str'] = expiry_field
    
    # Renewal status validation
    renewal_field = customer.get('renewal / non-renewal', '') or customer.get('renewal___non-renewal', '')
    renewal_status = str(renewal_field).strip().lower()
    if not renewal_status:
        errors.append("Renewal / Non-Renewal is empty")
    elif 'non-renewal' in renewal_status or 'non renewal' in renewal_status or 'nonrenewal' in renewal_status.replace(' ', ''):
        errors.append(f"Not a renewal customer: {renewal_field}")
    else:
        validated['renewal_status'] = renewal_status
    
    # Payee validation
    payee = str(customer.get('payee', '')).strip().lower()
    if 'direct billed' not in payee and 'directbilled' not in payee.replace(' ', ''):
        errors.append(f"Payee is not 'direct billed': {customer.get('payee', 'N/A')}")
    else:
        validated['payee'] = payee
    
    # Payment status validation
    payment_status = str(customer.get('payment_status', '') or customer.get('status', '')).strip().lower()
    if 'pending payment' not in payment_status and 'pendingpayment' not in payment_status.replace(' ', ''):
        status_value = customer.get('payment_status', '') or customer.get('status', 'N/A')
        errors.append(f"Payment status is not 'pending payment': {status_value}")
    else:
        validated['payment_status'] = payment_status
    
    if errors:
        return False, "; ".join(errors), None
    
    return True, "", validated


def should_skip_renewal_row(customer):
    """
    Check if a renewal row should be skipped based on validation rules
    
    Only process rows that meet ALL of:
    - renewal / non-renewal = "renewal" (case-insensitive)
    - payee = "direct billed" (case-insensitive)
    - status/payment_status = "pending payment" (case-insensitive)
    
    Note: N1 Project - Renewal workflow includes payee filtering.
    This workflow handles renewal customers with specific payee conditions.
    
    Skip if ANY of:
    - done is checked/true
    - company is empty
    - client_phone_number is empty
    - expiration_date is empty or invalid
    - renewal / non-renewal is empty or not "renewal"
    - payee is not "direct billed"
    - payment_status is not "pending payment"
    
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
    
    # Must be "renewal" (not "non-renewal")
    if 'non-renewal' in renewal_status or 'non renewal' in renewal_status or 'nonrenewal' in renewal_status.replace(' ', ''):
        return True, f"Renewal / Non-Renewal is not 'renewal' (Status: {renewal_field})"
    
    # Check payee - must be "direct billed"
    payee = str(customer.get('payee', '')).strip().lower()
    if 'direct billed' not in payee and 'directbilled' not in payee.replace(' ', ''):
        return True, f"Payee is not 'direct billed' (Payee: {customer.get('payee', 'N/A')})"
    
    # Check payment_status/status - must be "pending payment"
    # Support both 'payment_status' and 'status' column names
    payment_status = str(customer.get('payment_status', '') or customer.get('status', '')).strip().lower()
    if 'pending payment' not in payment_status and 'pendingpayment' not in payment_status.replace(' ', ''):
        status_value = customer.get('payment_status', '') or customer.get('status', 'N/A')
        return True, f"Payment status is not 'pending payment' (Status: {status_value})"

    return False, ""


def get_renewal_stage(customer):
    """
    Get the current renewal call stage for a customer
    
    Returns:
        int: Stage number (0 for empty/null, 1, 2, 3+)
    """
    # Try multiple possible column names (normalized)
    stage = customer.get('stage', '') or customer.get('renewal_call_stage', '')
    
    if not stage or stage == '' or stage is None:
        return 0
    
    try:
        return int(stage)
    except (ValueError, TypeError):
        return 0


def get_renewal_assistant_id_for_stage(stage):
    """Get the appropriate assistant ID for a given renewal call stage"""
    # Stage 0 & 1 (14 days & 7 days before): Use same Assistant
    # Stage 2 & 3 (1 day before & day of): Use different Assistant
    assistant_map = {
        0: RENEWAL_1ST_REMINDER_ASSISTANT_ID,  # 14 days before (1st Reminder)
        1: RENEWAL_2ND_REMINDER_ASSISTANT_ID,  # 7 days before (2nd Reminder - same as 1st)
        2: RENEWAL_3RD_REMINDER_ASSISTANT_ID,  # 1 day before (3rd Reminder)
        3: RENEWAL_3RD_REMINDER_ASSISTANT_ID   # day of expiry (reuse 3rd)
    }

    return assistant_map.get(stage)


def should_skip_mortgage_bill_row(customer):
    """
    Check if a mortgage bill row should be skipped
    
    Only process rows that meet ALL of:
    - payee = "Mortgage Billed" (case-insensitive)
    - status != "Renewal Paid" (case-insensitive)
    
    Skip if ANY of:
    - done is checked/true
    - company is empty
    - client_phone_number is empty
    - expiration_date is empty or invalid
    - payee is not "Mortgage Billed"
    - status is "Renewal Paid"
    
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

    # Check payee - must be "Mortgage Billed"
    payee = str(customer.get('payee', '')).strip().lower()
    if 'mortgage billed' not in payee and 'mortgagebilled' not in payee.replace(' ', ''):
        return True, f"Payee is not 'Mortgage Billed' (Payee: {customer.get('payee', 'N/A')})"
    
    # Check status - must NOT be "Renewal Paid"
    status = str(customer.get('status', '')).strip().lower()
    if 'renewal paid' in status or 'renewalpaid' in status.replace(' ', ''):
        return True, f"Status is 'Renewal Paid' (Status: {customer.get('status', 'N/A')})"

    return False, ""


def get_mortgage_bill_stage(customer):
    """
    Get the current mortgage bill call stage for a customer
    
    Returns:
        int: Stage number (0 for empty/null, 1, 2+)
    """
    # Try multiple possible column names (normalized)
    stage = customer.get('mortgage_bill_stage', '') or customer.get('stage', '')
    
    if not stage or stage == '' or stage is None:
        return 0
    
    try:
        return int(stage)
    except (ValueError, TypeError):
        return 0


def is_mortgage_bill_ready_for_calling(customer, today):
    """
    Check if a mortgage bill customer is ready for calling based on timeline logic
    
    All date calculations are based on the expiration_date column:
    - 14 days before expiration_date → Stage 0 (1st Call)
    - 7 days before expiration_date → Stage 1 (2nd Call)
    
    Args:
        customer: Customer dict
        today: Current date
        
    Returns:
        tuple: (is_ready: bool, reason: str, stage: int)
    """
    # Skip if today is weekend (no calls on weekends)
    if is_weekend(today):
        return False, f"Today is {today.strftime('%A')} (weekend) - no calls on weekends", -1
    
    # Parse expiration date from sheet
    expiry_date_str = customer.get('expiration_date', '') or customer.get('expiration date', '')
    expiry_date = parse_date(expiry_date_str)
    
    if not expiry_date:
        return False, "Invalid policy expiry date", -1
    
    # Calculate days until expiry
    days_until_expiry = (expiry_date - today).days
    
    # Check if we should stop calling (expired)
    if days_until_expiry < 0:
        return False, f"Policy already expired ({abs(days_until_expiry)} days ago)", -1
    
    # Check if today matches any of the calling schedule days
    # Mortgage Bill: 14 days and 7 days before expiration
    mortgage_bill_schedule = [14, 7]
    
    for stage, days_before in enumerate(mortgage_bill_schedule):
        target_date = expiry_date - timedelta(days=days_before)
        
        # If target date is weekend, adjust to previous Friday
        if is_weekend(target_date):
            # Calculate days to go back to Friday
            if target_date.weekday() == 5:  # Saturday
                days_to_friday = 1
            else:  # Sunday (weekday=6)
                days_to_friday = 2
            
            adjusted_target_date = target_date - timedelta(days=days_to_friday)
            adjusted_days_before = (expiry_date - adjusted_target_date).days
            
            # Check if today matches the adjusted target date
            if today == adjusted_target_date:
                return True, f"Ready for mortgage bill stage {stage} call (adjusted from {days_before} days to {adjusted_days_before} days before expiry - target was {target_date.strftime('%A')})", stage
        else:
            # Target date is weekday, check if today matches
            if today == target_date:
                return True, f"Ready for mortgage bill stage {stage} call ({days_before} days before expiry)", stage
    
    return False, f"Not ready for mortgage bill call (expires in {days_until_expiry} days)", -1


def get_mortgage_bill_customers_ready_for_calls(smartsheet_service):
    """
    Get all mortgage bill customers ready for calls today based on timeline logic
    
    Returns:
        dict: Customers grouped by stage {0: [...], 1: [...]}
    """
    print("=" * 80)
    print("🔍 FETCHING MORTGAGE BILL CUSTOMERS READY FOR CALLS")
    print("=" * 80)

    # Get all customers from sheet
    all_customers = smartsheet_service.get_all_customers_with_stages()

    # Use Pacific Time for "today" to ensure consistent behavior
    pacific_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific_tz).date()
    print(f"📅 Today (Pacific Time): {today}")
    print(f"⏰ Mortgage Bill calling schedule: 14 days and 7 days before expiry")

    customers_by_stage = {0: [], 1: []}  # 2 stages: 14, 7 days before
    skipped_count = 0
    
    for customer in all_customers:
        # Initial validation
        should_skip, skip_reason = should_skip_mortgage_bill_row(customer)
        if should_skip:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: {skip_reason}")
            continue
        
        # Get current stage
        current_stage = get_mortgage_bill_stage(customer)
        
        # Skip if stage >= 2 (call sequence complete - both calls made)
        if current_stage >= 2:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: Mortgage bill sequence complete (stage {current_stage})")
            continue
        
        # Check if ready for calling based on timeline
        is_ready, ready_reason, target_stage = is_mortgage_bill_ready_for_calling(customer, today)
        if not is_ready:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: {ready_reason}")
            continue
        
        # Check if the customer is at the right stage for today's call
        if current_stage != target_stage:
            if current_stage < target_stage:
                # Customer missed earlier stages - allow auto-adjustment
                print(f"   ⚠️  Row {customer.get('row_number')}: Auto-adjusting mortgage bill stage {current_stage} → {target_stage} (missed earlier stages)")
            else:
                # Customer already passed this stage - skip
                skipped_count += 1
                print(f"   ⏭️  Skipping row {customer.get('row_number')}: Already past this stage (current: {current_stage}, needed: {target_stage})")
                continue
        
        customers_by_stage[target_stage].append(customer)
        stage_names = ["14 days before", "7 days before"]
        print(f"   ✅ Row {customer.get('row_number')}: Stage {target_stage} ({stage_names[target_stage]}), ready for mortgage bill call")
    
    print(f"\n📊 Summary:")
    print(f"   Stage 0 (14 days before): {len(customers_by_stage[0])} customers")
    print(f"   Stage 1 (7 days before): {len(customers_by_stage[1])} customers")
    print(f"   Skipped: {skipped_count} rows")
    print(f"   Total ready: {sum(len(v) for v in customers_by_stage.values())}")
    
    return customers_by_stage


# ========================================
# Renewal Timeline Logic
# ========================================

def is_renewal_ready_for_calling(customer, today):
    """
    Check if a renewal customer is ready for calling based on timeline logic
    Weekend-aware: If target date falls on weekend, calls are made on the previous Friday
    
    All date calculations are based on the expiration_date column:
    - 14 days before expiration_date → Stage 0 (1st Reminder)
    - 7 days before expiration_date → Stage 1 (2nd Reminder)
    - 1 day before expiration_date → Stage 2 (3rd Reminder)
    - On expiration_date → Stage 3 (Final Reminder)
    
    Args:
        customer: Customer dict
        today: Current date
        
    Returns:
        tuple: (is_ready: bool, reason: str, stage: int)
    """
    # Skip if today is weekend (no calls on weekends)
    if is_weekend(today):
        return False, f"Today is {today.strftime('%A')} (weekend) - no calls on weekends", -1
    
    # Parse expiration date from sheet (this is the base date for all calculations)
    expiry_date_str = customer.get('expiration_date', '') or customer.get('expiration date', '')
    expiry_date = parse_date(expiry_date_str)
    
    if not expiry_date:
        return False, "Invalid policy expiry date", -1
    
    # Calculate days until expiry (based on expiration_date column)
    days_until_expiry = (expiry_date - today).days
    
    # Check if we should stop calling (expired)
    if days_until_expiry < 0:
        return False, f"Policy already expired ({abs(days_until_expiry)} days ago)", -1
    
    # Check if it's the right day of month to start calling
    if today.day < RENEWAL_CALLING_START_DAY:
        return False, f"Not yet calling day (start on day {RENEWAL_CALLING_START_DAY})", -1
    
    # Check if today matches any of the calling schedule days
    # If target date falls on weekend, adjust to previous Friday
    for stage, days_before in enumerate(RENEWAL_CALLING_SCHEDULE):
        target_date = expiry_date - timedelta(days=days_before)
        
        # If target date is weekend, adjust to previous Friday
        if is_weekend(target_date):
            # Calculate days to go back to Friday
            # Saturday (weekday=5) -> go back 1 day to Friday
            # Sunday (weekday=6) -> go back 2 days to Friday
            if target_date.weekday() == 5:  # Saturday
                days_to_friday = 1
            else:  # Sunday (weekday=6)
                days_to_friday = 2
            
            adjusted_target_date = target_date - timedelta(days=days_to_friday)
            adjusted_days_before = (expiry_date - adjusted_target_date).days
            
            # Check if today matches the adjusted target date
            if today == adjusted_target_date:
                return True, f"Ready for stage {stage} call (adjusted from {days_before} days to {adjusted_days_before} days before expiry - target was {target_date.strftime('%A')})", stage
        else:
            # Target date is weekday, check if today matches
            if today == target_date:
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
    Based on the fixed schedule: 14, 7, 1, 0 days before expiration_date
    
    All calculations are relative to the expiration_date column:
    - Stage 0 → Stage 1: 7 days before expiration_date
    - Stage 1 → Stage 2: 1 day before expiration_date
    - Stage 2 → Stage 3: On expiration_date
    
    Args:
        customer: Customer dict
        current_stage: Current call stage (0, 1, 2, or 3)
    
    Returns:
        date or None: Next follow-up date
    """
    # Use Expiration Date column (this is the base date for all calculations)
    expiry_date_str = customer.get('expiration_date', '') or customer.get('expiration date', '')
    expiry_date = parse_date(expiry_date_str)
    
    if not expiry_date:
        print(f"   ⚠️  Invalid expiry date: {expiry_date_str}")
        return None
    
    # Fixed schedule: 14, 7, 1, 0 days before expiration_date
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


def get_renewal_expired_after_customers(smartsheet_service):
    """
    Get all renewal customers that are expired after (Expiration Date过了一天之后)
    
    Args:
        smartsheet_service: SmartsheetService 实例
    
    Returns:
        list: 过期后的客户列表
    """
    print("=" * 80)
    print("🔍 FETCHING RENEWAL CUSTOMERS EXPIRED AFTER (Expiration Date过了一天之后)")
    print("=" * 80)
    print("📋 筛选条件: 今天 > Expiration Date + 1天")
    print("=" * 80)
    
    # 获取所有客户
    all_customers = smartsheet_service.get_all_customers_with_stages()
    
    # 使用太平洋时区获取今天的日期
    pacific_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific_tz).date()
    print(f"📅 Today (Pacific Time): {today}")
    
    expired_customers = []
    skipped_count = 0
    
    for customer in all_customers:
        row_num = customer.get('row_number', 'N/A')
        
        # 初始验证
        should_skip, skip_reason = should_skip_renewal_row(customer)
        if should_skip:
            skipped_count += 1
            continue
        
        # 获取当前 stage（可选：可以跳过已完成所有电话的客户）
        # 对于过期后保单，我们仍然可以拨打，所以不跳过 stage >= 4 的客户
        
        # 获取 expiration_date
        expiration_date_str = customer.get('expiration_date', '') or customer.get('expiration date', '')
        if not expiration_date_str.strip():
            skipped_count += 1
            continue
        
        expiration_date = parse_date(expiration_date_str)
        if not expiration_date:
            skipped_count += 1
            continue
        
        # 检查是否过期后（今天 > Expiration Date + 1天）
        expiration_plus_one = expiration_date + timedelta(days=1)
        if today <= expiration_plus_one:
            skipped_count += 1
            continue
        
        # 添加到过期后客户列表
        expired_customers.append(customer)
        days_expired = (today - expiration_date).days
        print(f"   ✅ Row {row_num}: 过期后保单 (Expiration Date {expiration_date}, 已过期 {days_expired} 天), 准备拨打")
    
    print(f"\n📊 Summary:")
    print(f"   过期后保单: {len(expired_customers)} 个客户")
    print(f"   跳过: {skipped_count} 行")
    
    return expired_customers


def format_renewal_call_entry(summary, evaluation, call_number):
    """Format a renewal call entry for appending"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entry = f"[Renewal Call {call_number} - {timestamp}]\n{summary}\n"
    eval_entry = f"[Renewal Call {call_number} - {timestamp}]\n{evaluation}\n"
    return entry, eval_entry


def update_after_mortgage_bill_call(smartsheet_service, customer, call_data, call_stage):
    """
    Update Smartsheet after a successful mortgage bill call
    
    Args:
        smartsheet_service: SmartsheetService instance
        customer: Customer dict
        call_data: Call result data from VAPI
        call_stage: Stage at which the call was made (0 or 1)
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

    evaluation = str(evaluation).lower()

    # Determine new stage (advance to next stage after this call)
    new_stage = call_stage + 1

    # Calculate next followup date (None for stage 1 - final call)
    expiry_date_str = customer.get('expiration_date', '') or customer.get('expiration date', '')
    expiry_date = parse_date(expiry_date_str)
    next_followup_date = None
    
    if call_stage == 0 and expiry_date:
        # After 1st call: Next call is 7 days before expiration
        next_followup_date = expiry_date - timedelta(days=7)
        print(f"   📅 Stage 0→1: Next call 7 days before expiration ({next_followup_date})")
    else:
        # Final call - no more follow-ups
        print(f"   📅 Stage {call_stage}: Final mortgage bill call - no more follow-ups")

    # Format entries for appending
    call_number = call_stage + 1
    summary_entry, eval_entry = format_renewal_call_entry(summary, evaluation, call_number)

    # Get existing values
    existing_summary = customer.get('mortgage_bill_call_summary', '') or customer.get('renewal_call_summary', '')
    existing_eval = customer.get('mortgage_bill_call_eval', '') or customer.get('renewal_call_eval', '')
    
    # Format call summary for Call Notes column (same format as renewal calls)
    start_time_str = call_data.get('startedAt') or call_data.get('createdAt', '')
    if start_time_str:
        try:
            start_time_utc = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            pacific_tz = ZoneInfo("America/Los_Angeles")
            start_time_pacific = start_time_utc.astimezone(pacific_tz)
            call_placed_at = start_time_pacific.strftime('%Y-%m-%d %H:%M:%S')
        except:
            call_placed_at = datetime.now(ZoneInfo("America/Los_Angeles")).strftime('%Y-%m-%d %H:%M:%S')
    else:
        call_placed_at = datetime.now(ZoneInfo("America/Los_Angeles")).strftime('%Y-%m-%d %H:%M:%S')
    
    no_answer_reasons = [
        'voicemail',
        'customer-did-not-answer',
        'customer-busy',
        'twilio-failed-to-connect-call',
        'assistant-error'
    ]
    did_client_answer = 'No' if ended_reason in no_answer_reasons else 'Yes'
    
    was_full_message_conveyed = 'No'
    if did_client_answer == 'Yes':
        if ended_reason == 'assistant-forwarded-call':
            was_full_message_conveyed = 'Yes'
        elif ended_reason == 'customer-ended-call':
            if analysis and summary and summary != 'No summary available':
                was_full_message_conveyed = 'Yes'
            else:
                was_full_message_conveyed = 'No'
        else:
            was_full_message_conveyed = 'No'
    
    was_voicemail_left = 'Yes' if is_voicemail else 'No'
    
    call_notes_structured = f"""Call Placed At: {call_placed_at}

Did Client Answer: {did_client_answer}

Was Full Message Conveyed: {was_full_message_conveyed}

Was Voicemail Left: {was_voicemail_left}
"""
    
    if is_voicemail:
        call_notes_summary = 'Left voicemail'
    else:
        call_notes_summary = summary if summary and summary != 'No summary available' else ''
    
    if call_notes_summary:
        call_notes_entry = call_notes_structured + f"\nanalysis:\n\n{call_notes_summary}\n"
    else:
        call_notes_entry = call_notes_structured
    
    existing_notes = customer.get('call_notes', '') or customer.get('mortgage_bill_call_notes', '')
    
    if existing_notes:
        new_call_notes = existing_notes + "\n---\n" + call_notes_entry
    else:
        new_call_notes = call_notes_entry

    if existing_summary:
        new_summary = existing_summary + "\n---\n" + summary_entry
    else:
        new_summary = summary_entry

    if existing_eval:
        new_eval = existing_eval + "\n---\n" + eval_entry
    else:
        new_eval = eval_entry

    pacific_tz = ZoneInfo("America/Los_Angeles")
    current_date = datetime.now(pacific_tz).date()
    last_call_date_str = current_date.strftime('%Y-%m-%d')
    
    updates = {
        'mortgage_bill_stage': new_stage,  # Use mortgage_bill_stage column if exists, otherwise stage
        'call_notes': new_call_notes,
        'last_call_made_date': last_call_date_str,
    }

    if next_followup_date:
        updates['f_u_date'] = next_followup_date.strftime('%Y-%m-%d')

    # Perform update
    success = smartsheet_service.update_customer_fields(customer, updates)

    if success:
        print(f"✅ Smartsheet updated successfully")
        print(f"   • Mortgage Bill Stage: {call_stage} → {new_stage}")
        print(f"   • Call Notes: Updated with summary (Call #{call_number})")
        print(f"   • Last Call Made Date: {last_call_date_str}")
        if next_followup_date:
            print(f"   • Next F/U Date: {next_followup_date}")
    else:
        print(f"❌ Smartsheet update failed")

    return success


def update_after_renewal_call(smartsheet_service, customer, call_data, call_stage):
    """
    Update Smartsheet after a successful renewal call
    
    Args:
        smartsheet_service: SmartsheetService instance
        customer: Customer dict
        call_data: Call result data from VAPI
        call_stage: Stage at which the call was made (0, 1, 2, or 3)
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

    evaluation = str(evaluation).lower()

    # Determine new stage (advance to next stage after this call)
    new_stage = call_stage + 1

    # Calculate next followup date (None for stage 3)
    next_followup_date = calculate_renewal_next_followup_date(customer, call_stage)

    # Format entries for appending
    call_number = call_stage + 1
    summary_entry, eval_entry = format_renewal_call_entry(summary, evaluation, call_number)

    # Get existing values
    existing_summary = customer.get('renewal_call_summary', '')
    existing_eval = customer.get('renewal_call_eval', '')
    
    # Format call summary for Call Notes column (required format for Personal Lines)
    # Required format:
    # Call Placed At: {{start_time}}
    # Did Client Answer: Yes/No
    # Was Full Message Conveyed: Yes/No (Yes = AI reached the transfer question while caller was on the line)
    # Was Voicemail Left: Yes/No
    
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
    was_voicemail_left = 'Yes' if is_voicemail else 'No'
    
    # Format call notes entry in required format
    # Include both the structured format AND the original analysis summary
    call_notes_structured = f"""Call Placed At: {call_placed_at}

Did Client Answer: {did_client_answer}

Was Full Message Conveyed: {was_full_message_conveyed}

Was Voicemail Left: {was_voicemail_left}
"""
    
    # Add the original analysis summary if available (for voicemail, use "Left voicemail")
    if is_voicemail:
        call_notes_summary = 'Left voicemail'
    else:
        call_notes_summary = summary if summary and summary != 'No summary available' else ''
    
    # Combine structured format with summary (add "analysis:" label)
    if call_notes_summary:
        call_notes_entry = call_notes_structured + f"\nanalysis:\n\n{call_notes_summary}\n"
    else:
        call_notes_entry = call_notes_structured
    
    # Get existing call notes
    existing_notes = customer.get('call_notes', '') or customer.get('renewal_call_notes', '')
    
    # Append summary to existing notes (separate each call with separator)
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
    # Use actual column names from Smartsheet:
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
        'call_notes': new_call_notes,  # Store summary in Call Notes (similar to CL1 Project)
        'last_call_made_date': last_call_date_str,  # Record last call date (date only for DATE type column)
    }

    if next_followup_date:
        updates['f_u_date'] = next_followup_date.strftime('%Y-%m-%d')  # Use "F/U Date" column
    
    # Note: renewal_call_summary and renewal_call_eval columns may not exist in the sheet
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

class RenewalWorkflowErrorLogger:
    """Error logger for Renewal workflow"""
    
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


def run_renewal_batch_calling(test_mode=False, schedule_at=None, auto_confirm=False, sheet_id=None, sheet_name=None):
    """
    Main function to run renewal batch calling with comprehensive error handling
    
    Args:
        test_mode: If True, skip actual calls and Smartsheet updates (default: False)
        schedule_at: Optional datetime to schedule calls
        auto_confirm: If True, skip user confirmation prompt (for cron jobs) (default: False)
        sheet_id: Optional sheet ID to use instead of current month's sheet (for batch processing)
        sheet_name: Optional sheet name to use (for batch processing)
    """
    # Initialize error logger
    error_logger = RenewalWorkflowErrorLogger()
    
    print("=" * 80)
    print("🚀 N1 PROJECT - RENEWAL BATCH CALLING SYSTEM")
    if test_mode:
        print("🧪 TEST MODE - No actual calls or updates will be made")
    if schedule_at:
        print(f"⏰ SCHEDULED MODE - Calls will be scheduled for {schedule_at.strftime('%Y-%m-%d %H:%M:%S')}")
    if sheet_id:
        print(f"📋 Using specified sheet ID: {sheet_id}")
    if sheet_name:
        print(f"📋 Using specified sheet: {sheet_name}")
    print("=" * 80)
    print("📋 N1 Project: Renewal notifications with dynamic sheet discovery")
    print("📞 4-stage calling: 14 days → 7 days → 1 day → day of expiry")
    print("=" * 80)
    
    try:
        # Initialize services with dynamic sheet discovery or specified sheet
        if sheet_id:
            smartsheet_service = SmartsheetService(sheet_id=sheet_id)
        elif sheet_name:
            smartsheet_service = SmartsheetService(sheet_name=sheet_name, workspace_name=RENEWAL_WORKSPACE_NAME)
        else:
            smartsheet_service = get_current_renewal_sheet()
        vapi_service = VAPIService()
    except Exception as e:
        error_logger.log_error({}, 0, 'INITIALIZATION_ERROR', f"Failed to initialize services: {e}", e)
        return False
    
    # Get customers grouped by stage
    customers_by_stage = get_renewal_customers_ready_for_calls(smartsheet_service)
    
    # Get mortgage bill customers ready for calls
    mortgage_bill_customers_by_stage = get_mortgage_bill_customers_ready_for_calls(smartsheet_service)
    
    # Get expired after customers (Expiration Date过了一天之后)
    EXPIRED_AFTER_ASSISTANT_ID = "aec4721c-360c-45b5-ba39-87320eab6fc9"
    expired_after_customers = get_renewal_expired_after_customers(smartsheet_service)
    
    total_non_expired = sum(len(v) for v in customers_by_stage.values())
    total_mortgage_bill = sum(len(v) for v in mortgage_bill_customers_by_stage.values())
    total_expired_after = len(expired_after_customers)
    total_customers = total_non_expired + total_mortgage_bill + total_expired_after
    
    if total_customers == 0:
        print("\n" + "=" * 80)
        print("ℹ️  NO CUSTOMERS READY FOR CALLS TODAY")
        print("=" * 80)
        print("   • Renewal customers ready: 0")
        print("   • Mortgage Bill customers ready: 0")
        print("   • Expired after customers ready: 0")
        print("\n   This is normal if:")
        print("   - No customers meet the calling criteria today")
        print("   - All eligible customers have already been called")
        print("   - No customers are in the calling window")
        print("=" * 80)
        return True
    
    # Show summary and ask for confirmation
    print(f"\n{'=' * 80}")
    print(f"📊 RENEWAL & MORTGAGE BILL CUSTOMERS READY FOR CALLS TODAY:")
    print(f"{'=' * 80}")
    
    # Show mortgage bill customers first
    if total_mortgage_bill > 0:
        print(f"\n🏠 MORTGAGE BILL CUSTOMERS - {total_mortgage_bill} customers:")
        for stage, customers in mortgage_bill_customers_by_stage.items():
            if customers:
                stage_names = ["14 days before", "7 days before"]
                assistant_id = MORTGAGE_BILL_1ST_REMAINDER_ASSISTANT_ID if stage == 0 else MORTGAGE_BILL_2ND_REMAINDER_ASSISTANT_ID
                print(f"\n   🔔 Stage {stage} ({stage_names[stage]}) - {len(customers)} customers:")
                print(f"      🤖 Assistant ID: {assistant_id}")
                for i, customer in enumerate(customers[:5], 1):
                    phone = customer.get('phone_number') or customer.get('client_phone_number', 'N/A')
                    print(f"      {i}. {customer.get('company', 'Unknown')} - {phone}")
                if len(customers) > 5:
                    print(f"      ... and {len(customers) - 5} more")
    
    print(f"\n📋 RENEWAL CUSTOMERS:")
    for stage, customers in customers_by_stage.items():
        if customers:
            stage_names_short = ["1st", "2nd", "3rd", "Final"]
            stage_name = stage_names_short[stage] if stage < len(stage_names_short) else f"Stage {stage}"
            assistant_id = get_renewal_assistant_id_for_stage(stage)
            print(f"\n🔔 Stage {stage} ({stage_name} Renewal Reminder) - {len(customers)} customers:")
            print(f"   🤖 Assistant ID: {assistant_id}")
            
            for i, customer in enumerate(customers[:5], 1):
                phone = customer.get('phone_number') or customer.get('client_phone_number', 'N/A')
                print(f"   {i}. {customer.get('company', 'Unknown')} - {phone}")
            
            if len(customers) > 5:
                print(f"   ... and {len(customers) - 5} more")
    
    # Show expired after customers
    if expired_after_customers:
        print(f"\n🔔 过期后保单 (Expired After) - {len(expired_after_customers)} customers:")
        print(f"   🤖 Assistant ID: {EXPIRED_AFTER_ASSISTANT_ID}")
        
        for i, customer in enumerate(expired_after_customers[:5], 1):
            phone = customer.get('phone_number') or customer.get('client_phone_number', 'N/A')
            expiration_date = customer.get('expiration_date', '') or customer.get('expiration date', 'N/A')
            print(f"   {i}. {customer.get('company', 'Unknown')} - {phone} (Expiration: {expiration_date})")
        
        if len(expired_after_customers) > 5:
            print(f"   ... and {len(expired_after_customers) - 5} more")
    
    print(f"\n{'=' * 80}")
    if not test_mode:
        print(f"📞 PRODUCTION MODE: Will make {total_customers} ACTUAL phone calls!")
        print(f"   • Renewal (未过期保单): {total_non_expired} 通")
        print(f"   • Mortgage Bill: {total_mortgage_bill} 通")
        print(f"   • 过期后保单: {total_expired_after} 通")
        print(f"💰 This will incur charges for each call")
        print(f"\n⚠️  CONFIRMATION: Calls will be made automatically (auto_confirm=True)")
    else:
        print(f"🧪 TEST MODE: Will simulate {total_customers} calls (no charges)")
        print(f"   • Renewal (未过期保单): {total_non_expired} 通")
        print(f"   • Mortgage Bill: {total_mortgage_bill} 通")
        print(f"   • 过期后保单: {total_expired_after} 通")
        print(f"\n⚠️  NOTE: No actual calls will be made in test mode")
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
                phone = customer.get('phone_number') or customer.get('client_phone_number', 'N/A')
                print(f"   ✅ [SIMULATED] Would call: {customer.get('company', 'Unknown')} - {phone}")
                total_success += 1
        else:
            # Stage 0: Batch calling (all customers simultaneously)
            if stage == 0:
                print(f"📦 Batch calling mode (simultaneous)")
                # Validate customers before calling
                validated_customers = []
                for customer in customers:
                    is_valid, error_msg, validated_data = validate_renewal_customer_data(customer)
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
                    if not test_mode:
                        print(f"\n🚀 PRODUCTION MODE: Making ACTUAL batch VAPI call to {len(validated_customers)} customers")
                        print(f"   ⚠️  Real calls will be made - charges will apply")
                    results = vapi_service.make_batch_call_with_assistant(
                        validated_customers,
                        assistant_id,
                        schedule_immediately=(schedule_at is None),
                        schedule_at=schedule_at
                    )

                    if results:
                        print(f"\n✅ Stage {stage} renewal batch calls completed")
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
                                        success = update_after_renewal_call(smartsheet_service, customer, call_data, stage)
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
                        print(f"\n❌ Stage {stage} renewal batch calls failed")
                        for customer in validated_customers:
                            error_logger.log_error(customer, stage, 'VAPI_CALL_FAILED', "VAPI API returned no results")
                        total_failed += len(validated_customers)
                except Exception as e:
                    print(f"\n❌ Stage {stage} renewal batch calls failed with exception")
                    for customer in validated_customers:
                        error_logger.log_error(customer, stage, 'VAPI_CALL_EXCEPTION', f"Exception during VAPI call: {e}", e)
                    total_failed += len(validated_customers)

            # Stage 1 & 2: Sequential calling (one customer at a time)
            else:
                print(f"🔄 Sequential calling mode (one at a time)")

                for i, customer in enumerate(customers, 1):
                    print(f"\n   📞 Call {i}/{len(customers)}: {customer.get('company', 'Unknown')}")

                    # Validate customer before calling
                    is_valid, error_msg, validated_data = validate_renewal_customer_data(customer)
                    if not is_valid:
                        error_logger.log_validation_failure(customer, error_msg)
                        error_logger.log_warning(customer, stage, 'VALIDATION_FAILED', error_msg)
                        total_failed += 1
                        continue

                    # Merge validated data into customer (especially phone_number)
                    customer_for_call = {**customer, **validated_data}

                    try:
                        if not test_mode:
                            print(f"\n🚀 PRODUCTION MODE: Making ACTUAL VAPI call to {customer_for_call.get('company', 'Unknown')}")
                            print(f"   ⚠️  Real call will be made - charges will apply")
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
                                    success = update_after_renewal_call(smartsheet_service, customer, call_data, stage)
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

                print(f"\n✅ Stage {stage} renewal sequential calls completed")
    
    # Process expired after customers
    if expired_after_customers:
        print(f"\n{'=' * 80}")
        print(f"📞 RENEWAL CALLING - 过期后保单 (Expired After) - {len(expired_after_customers)} customers")
        print(f"🤖 Using Assistant: {EXPIRED_AFTER_ASSISTANT_ID}")
        print(f"{'=' * 80}")
        print(f"📦 Batch calling mode (simultaneous)")
        
        if test_mode:
            # Test mode: Simulate calls without actual API calls
            print(f"\n🧪 TEST MODE: Simulating {len(expired_after_customers)} expired after calls...")
            for customer in expired_after_customers:
                phone = customer.get('phone_number') or customer.get('client_phone_number', 'N/A')
                print(f"   ✅ [SIMULATED] Would call: {customer.get('company', 'Unknown')} - {phone}")
                total_success += 1
        else:
            # Validate customers before calling
            validated_customers = []
            for customer in expired_after_customers:
                is_valid, error_msg, validated_data = validate_renewal_customer_data(customer)
                if is_valid:
                    # Merge validated data into customer (especially phone_number)
                    customer_for_call = {**customer, **validated_data}
                    validated_customers.append(customer_for_call)
                else:
                    error_logger.log_validation_failure(customer, error_msg)
                    error_logger.log_warning(customer, -1, 'VALIDATION_FAILED', error_msg)
                    total_failed += 1
            
            if not validated_customers:
                print(f"\n⚠️  No valid customers for expired after calls after validation")
            else:
                try:
                    if not test_mode:
                        print(f"\n🚀 PRODUCTION MODE: Making ACTUAL batch VAPI call to {len(validated_customers)} expired customers")
                        print(f"   ⚠️  Real calls will be made - charges will apply")
                    results = vapi_service.make_batch_call_with_assistant(
                        validated_customers,
                        EXPIRED_AFTER_ASSISTANT_ID,
                        schedule_immediately=(schedule_at is None),
                        schedule_at=schedule_at
                    )

                    if results:
                        print(f"\n✅ Expired after renewal batch calls completed")
                        print(f"   📊 Received {len(results)} call result(s) for {len(validated_customers)} customer(s)")

                        # Only update Smartsheet if calls were immediate (not scheduled)
                        if schedule_at is None:
                            for i, customer in enumerate(validated_customers):
                                # Get corresponding call_data
                                if i < len(results):
                                    call_data = results[i]
                                else:
                                    call_data = results[0] if results else None
                                
                                if call_data:
                                    # Check if analysis exists, try to refresh if missing
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
                                    
                                    # Update Smartsheet
                                    try:
                                        # For expired after customers, use current stage (don't increment)
                                        current_stage = get_renewal_stage(customer)
                                        success = update_after_renewal_call(smartsheet_service, customer, call_data, current_stage)
                                        if success:
                                            total_success += 1
                                        else:
                                            error_logger.log_error(customer, -1, 'SMARTSHEET_UPDATE_FAILED', "Failed to update Smartsheet after expired after call")
                                            total_failed += 1
                                    except Exception as e:
                                        error_logger.log_error(customer, -1, 'SMARTSHEET_UPDATE_ERROR', f"Exception during Smartsheet update: {e}", e)
                                        total_failed += 1
                                else:
                                    print(f"   ❌ No call data for customer {i+1} ({customer.get('company', 'Unknown')})")
                                    error_logger.log_error(customer, -1, 'VAPI_CALL_FAILED', "VAPI call returned no data")
                                    total_failed += 1
                        else:
                            print(f"   ⏰ Calls scheduled - Smartsheet will be updated after calls complete")
                            total_success += len(validated_customers)
                    else:
                        print(f"\n❌ Expired after renewal batch calls failed")
                        error_logger.log_error({}, -1, 'VAPI_BATCH_CALL_FAILED', "VAPI batch call returned no results")
                        total_failed += len(validated_customers)
                except Exception as e:
                    print(f"\n❌ Expired after renewal batch calls failed with exception")
                    error_logger.log_error({}, -1, 'VAPI_BATCH_CALL_EXCEPTION', f"Exception during VAPI batch call: {e}", e)
                    total_failed += len(validated_customers)
    
    # Process mortgage bill customers
    if total_mortgage_bill > 0:
        print(f"\n{'=' * 80}")
        print(f"📞 MORTGAGE BILL CALLING - {total_mortgage_bill} customers")
        print(f"{'=' * 80}")
        
        for stage in [0, 1]:
            customers = mortgage_bill_customers_by_stage[stage]
            
            if not customers:
                continue
            
            stage_names = ["14 days before", "7 days before"]
            stage_name = stage_names[stage]
            assistant_id = MORTGAGE_BILL_1ST_REMAINDER_ASSISTANT_ID if stage == 0 else MORTGAGE_BILL_2ND_REMAINDER_ASSISTANT_ID
            
            print(f"\n{'=' * 80}")
            print(f"📞 MORTGAGE BILL CALLING STAGE {stage} ({stage_name}) - {len(customers)} customers")
            print(f"🤖 Using Assistant: {assistant_id}")
            print(f"{'=' * 80}")
            
            if test_mode:
                print(f"\n🧪 TEST MODE: Simulating {len(customers)} mortgage bill calls...")
                for customer in customers:
                    phone = customer.get('phone_number') or customer.get('client_phone_number', 'N/A')
                    print(f"   ✅ [SIMULATED] Would call: {customer.get('company', 'Unknown')} - {phone}")
                    total_success += 1
            else:
                # Stage 0: Batch calling (all customers simultaneously)
                if stage == 0:
                    print(f"📦 Batch calling mode (simultaneous)")
                    try:
                        if not test_mode:
                            print(f"\n🚀 PRODUCTION MODE: Making ACTUAL batch VAPI call to {len(customers)} mortgage bill customers")
                            print(f"   ⚠️  Real calls will be made - charges will apply")
                        results = vapi_service.make_batch_call_with_assistant(
                            customers,
                            assistant_id,
                            schedule_immediately=(schedule_at is None),
                            schedule_at=schedule_at
                        )
                        
                        if results:
                            print(f"\n✅ Stage {stage} mortgage bill batch calls completed")
                            
                            if schedule_at is None:
                                for i, customer in enumerate(customers):
                                    if i < len(results):
                                        call_data = results[i]
                                    else:
                                        call_data = results[0] if results else None
                                    
                                    if call_data:
                                        if 'analysis' not in call_data or not call_data.get('analysis'):
                                            if 'id' in call_data:
                                                call_id = call_data['id']
                                                try:
                                                    refreshed_data = vapi_service.check_call_status(call_id)
                                                    if refreshed_data and refreshed_data.get('analysis'):
                                                        call_data = refreshed_data
                                                except Exception as e:
                                                    print(f"      ❌ Failed to refresh call status: {e}")
                                        
                                        try:
                                            success = update_after_mortgage_bill_call(smartsheet_service, customer, call_data, stage)
                                            if success:
                                                total_success += 1
                                            else:
                                                error_logger.log_error(customer, stage, 'SMARTSHEET_UPDATE_FAILED', "Failed to update Smartsheet after mortgage bill call")
                                                total_failed += 1
                                        except Exception as e:
                                            error_logger.log_error(customer, stage, 'SMARTSHEET_UPDATE_ERROR', f"Exception during Smartsheet update: {e}", e)
                                            total_failed += 1
                                    else:
                                        error_logger.log_error(customer, stage, 'VAPI_CALL_FAILED', "VAPI call returned no data")
                                        total_failed += 1
                            else:
                                print(f"   ⏰ Calls scheduled - Smartsheet will be updated after calls complete")
                                total_success += len(customers)
                        else:
                            print(f"\n❌ Stage {stage} mortgage bill batch calls failed")
                            for customer in customers:
                                error_logger.log_error(customer, stage, 'VAPI_CALL_FAILED', "VAPI API returned no results")
                            total_failed += len(customers)
                    except Exception as e:
                        print(f"\n❌ Stage {stage} mortgage bill batch calls failed with exception")
                        for customer in customers:
                            error_logger.log_error(customer, stage, 'VAPI_CALL_EXCEPTION', f"Exception during VAPI call: {e}", e)
                        total_failed += len(customers)
                
                # Stage 1: Sequential calling (one customer at a time)
                else:
                    print(f"🔄 Sequential calling mode (one at a time)")
                    
                    for i, customer in enumerate(customers, 1):
                        print(f"\n   📞 Call {i}/{len(customers)}: {customer.get('company', 'Unknown')}")
                        
                        try:
                            if not test_mode:
                                print(f"\n🚀 PRODUCTION MODE: Making ACTUAL VAPI call to {customer.get('company', 'Unknown')}")
                                print(f"   ⚠️  Real call will be made - charges will apply")
                            results = vapi_service.make_batch_call_with_assistant(
                                [customer],
                                assistant_id,
                                schedule_immediately=(schedule_at is None),
                                schedule_at=schedule_at
                            )
                            
                            if results and results[0]:
                                call_data = results[0]
                                
                                if 'analysis' not in call_data or not call_data.get('analysis'):
                                    if 'id' in call_data:
                                        call_id = call_data['id']
                                        try:
                                            refreshed_data = vapi_service.check_call_status(call_id)
                                            if refreshed_data and refreshed_data.get('analysis'):
                                                call_data = refreshed_data
                                        except Exception as e:
                                            print(f"   ❌ Failed to refresh call status: {e}")
                                
                                if schedule_at is None:
                                    try:
                                        success = update_after_mortgage_bill_call(smartsheet_service, customer, call_data, stage)
                                        if success:
                                            total_success += 1
                                        else:
                                            error_logger.log_error(customer, stage, 'SMARTSHEET_UPDATE_FAILED', "Failed to update Smartsheet after mortgage bill call")
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
                    
                    print(f"\n✅ Stage {stage} mortgage bill sequential calls completed")
    
    # Final summary
    print(f"\n{'=' * 80}")
    print(f"🏁 RENEWAL BATCH CALLING COMPLETE")
    print(f"{'=' * 80}")
    print(f"   ✅ Successful: {total_success}")
    print(f"   ❌ Failed: {total_failed}")
    print(f"   📊 Total: {total_success + total_failed}")
    print(f"   • Renewal (未过期保单): {total_non_expired}")
    print(f"   • Mortgage Bill: {total_mortgage_bill}")
    print(f"   • 过期后保单: {total_expired_after}")
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

    run_renewal_batch_calling(test_mode=test_mode)
