"""
Mortgage Bill Workflow - Payment Reminder Calls for Mortgage Billed Policies
Only reach out if payment is not made (single call on day of payment due)
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from services import VAPIService, SmartsheetService
from config import (
    MORTGAGE_BILL_1ST_REMAINDER_ASSISTANT_ID,
    MORTGAGE_BILL_2ND_REMAINDER_ASSISTANT_ID,
    CANCELLATION_SHEET_ID  # TODO: Replace with actual Mortgage Bill sheet ID
)
from workflows.cancellations import (
    is_weekend,
    count_business_days,
    add_business_days,
    parse_date
)


def should_skip_mortgage_bill_row(customer):
    """
    Check if a mortgage bill row should be skipped
    
    Skip if ANY of:
    - done is checked/true
    - company is empty
    - phone_number is empty
    - payment_due_date is empty
    - payee is not "Mortgage" or "Mortgage Bill"
    - payment_status indicates payment already made
    
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

    # Check payee - only process Mortgage Bill
    payee = str(customer.get('payee', '')).strip().lower()
    if 'mortgage' not in payee:
        return True, f"Not a mortgage bill policy (Payee: {customer.get('payee', 'N/A')})"

    # Check if payment already made
    payment_status = str(customer.get('payment_status', '')).strip().lower()
    if 'paid' in payment_status or 'received' in payment_status:
        return True, "Payment already made"

    return False, ""


def is_mortgage_bill_ready_for_calling(customer, today):
    """
    Check if a mortgage bill customer is ready for calling
    Only call on the day payment is due (if payment not made)
    
    Args:
        customer: Customer dict
        today: Current date
        
    Returns:
        tuple: (is_ready: bool, reason: str)
    """
    # Parse payment due date
    payment_due_date_str = customer.get('payment_due_date', '') or customer.get('due_date', '')
    payment_due_date = parse_date(payment_due_date_str)
    
    if not payment_due_date:
        return False, "Invalid payment due date"
    
    # Calculate days until payment due
    days_until_due = (payment_due_date - today).days
    
    # Only call on the day payment is due (day 0) or if overdue
    if days_until_due == 0:
        # Double-check payment status
        payment_status = str(customer.get('payment_status', '')).strip().lower()
        if 'paid' in payment_status or 'received' in payment_status:
            return False, "Payment already made"
        return True, "Day of payment due (payment not made)"
    elif days_until_due < 0:
        # Overdue - still call if payment not made
        payment_status = str(customer.get('payment_status', '')).strip().lower()
        if 'paid' in payment_status or 'received' in payment_status:
            return False, "Payment already made"
        return True, f"Payment overdue by {abs(days_until_due)} days (payment not made)"
    else:
        return False, f"Too early to call (due in {days_until_due} days)"


def get_mortgage_bill_customers_ready_for_calls(smartsheet_service):
    """
    Get all mortgage bill customers ready for calls
    Only customers with payment due today (or overdue) and payment not made
    
    Returns:
        list: Customers ready for mortgage bill calls
    """
    print("=" * 80)
    print("🔍 FETCHING MORTGAGE BILL CUSTOMERS")
    print("=" * 80)

    # Get all customers from sheet
    all_customers = smartsheet_service.get_all_customers_with_stages()

    # Use Pacific Time for "today"
    pacific_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific_tz).date()
    print(f"📅 Today (Pacific Time): {today}")

    ready_customers = []
    skipped_count = 0
    
    for customer in all_customers:
        # Initial validation
        should_skip, skip_reason = should_skip_mortgage_bill_row(customer)
        if should_skip:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: {skip_reason}")
            continue
        
        # Check if ready for calling
        is_ready, reason = is_mortgage_bill_ready_for_calling(customer, today)
        
        if is_ready:
            ready_customers.append(customer)
            print(f"   ✅ Row {customer.get('row_number')}: {reason}")
        else:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: {reason}")
    
    print(f"\n📊 Summary:")
    print(f"   Ready for mortgage bill call: {len(ready_customers)} customers")
    print(f"   Skipped: {skipped_count} rows")
    
    return ready_customers


def format_mortgage_bill_call_entry(summary, evaluation):
    """Format a mortgage bill call entry for appending"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entry = f"[Mortgage Bill Call - {timestamp}]\n{summary}\n"
    eval_entry = f"[Mortgage Bill Call - {timestamp}]\n{evaluation}\n"
    return entry, eval_entry


def update_after_mortgage_bill_call(smartsheet_service, customer, call_data):
    """
    Update Smartsheet after a mortgage bill call
    
    Args:
        smartsheet_service: SmartsheetService instance
        customer: Customer dict
        call_data: Call result data from VAPI
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

    # Format entries
    summary_entry, eval_entry = format_mortgage_bill_call_entry(summary, evaluation)

    # Get existing values
    existing_summary = customer.get('mortgage_bill_call_summary', '') or customer.get('ai_call_summary', '')
    existing_eval = customer.get('mortgage_bill_call_eval', '') or customer.get('ai_call_eval', '')

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
        'mortgage_bill_call_summary': new_summary,
        'mortgage_bill_call_eval': new_eval,
        'mortgage_bill_called': 'Yes',  # Mark as called
    }

    # Perform update
    success = smartsheet_service.update_customer_fields(customer, updates)

    if success:
        print(f"✅ Smartsheet updated successfully")
    else:
        print(f"❌ Smartsheet update failed")

    return success


def run_mortgage_bill_calling(test_mode=False, schedule_at=None, auto_confirm=False):
    """
    Main function to run mortgage bill calling workflow
    
    Args:
        test_mode: If True, skip actual calls and Smartsheet updates (default: False)
        schedule_at: Optional datetime to schedule calls
        auto_confirm: If True, skip user confirmation prompt (for cron jobs) (default: False)
    """
    print("=" * 80)
    print("🚀 MORTGAGE BILL CALLING SYSTEM")
    if test_mode:
        print("🧪 TEST MODE - No actual calls or updates will be made")
    if schedule_at:
        print(f"⏰ SCHEDULED MODE - Calls will be scheduled for {schedule_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("📋 Single call on day of payment due (if payment not made)")
    print("⏭️  Only reaches out if payment is not made")
    print("=" * 80)
    
    # Initialize services
    # TODO: Replace CANCELLATION_SHEET_ID with actual Mortgage Bill sheet ID
    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
    vapi_service = VAPIService()
    
    # Get customers ready for mortgage bill calls
    ready_customers = get_mortgage_bill_customers_ready_for_calls(smartsheet_service)
    
    if len(ready_customers) == 0:
        print("\n✅ No customers ready for mortgage bill calls today")
        return True
    
    # Show summary
    print(f"\n{'=' * 80}")
    print(f"📊 MORTGAGE BILL CUSTOMERS READY FOR CALLS:")
    print(f"{'=' * 80}")
    print(f"   Total: {len(ready_customers)} customers")
    
    for i, customer in enumerate(ready_customers[:10], 1):
        payment_due = customer.get('payment_due_date', '') or customer.get('due_date', 'N/A')
        print(f"   {i}. {customer.get('company', 'Unknown')} - Due: {payment_due}")
    
    if len(ready_customers) > 10:
        print(f"   ... and {len(ready_customers) - 10} more")
    
    print(f"\n{'=' * 80}")
    if not test_mode:
        print(f"⚠️  WARNING: This will make {len(ready_customers)} mortgage bill phone calls!")
        print(f"💰 This will incur charges for each call")
    else:
        print(f"🧪 TEST MODE: Will simulate {len(ready_customers)} calls (no charges)")
    print(f"{'=' * 80}")

    # Ask for confirmation
    if not test_mode and not auto_confirm:
        response = input(f"\nProceed with mortgage bill calling? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ Mortgage bill calling cancelled")
            return False
    elif auto_confirm:
        print(f"🤖 AUTO-CONFIRM: Proceeding automatically (cron mode)")
    
    # Process calls
    total_success = 0
    total_failed = 0

    if test_mode:
        print(f"\n🧪 TEST MODE: Simulating {len(ready_customers)} mortgage bill calls...")
        for customer in ready_customers:
            print(f"   ✅ [SIMULATED] Would call: {customer.get('company', 'Unknown')}")
            total_success += 1
    else:
        # Make batch calls
        print(f"\n📞 Making mortgage bill calls...")
        print(f"🤖 Using Assistant: {MORTGAGE_BILL_1ST_REMAINDER_ASSISTANT_ID}")
        
        results = vapi_service.make_batch_call_with_assistant(
            ready_customers,
            MORTGAGE_BILL_1ST_REMAINDER_ASSISTANT_ID,
            schedule_immediately=(schedule_at is None),
            schedule_at=schedule_at
        )

        if results:
            print(f"\n✅ Mortgage bill calls completed")

            # Update Smartsheet if calls were immediate
            if schedule_at is None:
                for customer, call_data in zip(ready_customers, results):
                    if call_data:
                        update_after_mortgage_bill_call(smartsheet_service, customer, call_data)
                        total_success += 1
                    else:
                        total_failed += 1
            else:
                print(f"   ⏰ Calls scheduled - Smartsheet will be updated after calls complete")
                total_success += len(ready_customers)
        else:
            print(f"\n❌ Mortgage bill calls failed")
            total_failed += len(ready_customers)
    
    # Final summary
    print(f"\n{'=' * 80}")
    print(f"🏁 MORTGAGE BILL CALLING COMPLETE")
    print(f"{'=' * 80}")
    print(f"   ✅ Successful: {total_success}")
    print(f"   ❌ Failed: {total_failed}")
    print(f"   📊 Total: {total_success + total_failed}")
    print(f"{'=' * 80}")
    
    return True


if __name__ == "__main__":
    import sys
    test_mode = "--test" in sys.argv or "-t" in sys.argv
    run_mortgage_bill_calling(test_mode=test_mode)

