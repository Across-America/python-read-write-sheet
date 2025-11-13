"""
N1 Project - Cross-Sells Workflow
Offer Auto Quote to Monoline Home Policy Customers
Courtesy outreach to clients with only monoline home policy to offer auto quote

Note: This workflow is part of the N1 Project, based on the renewal sheet.
"""

from datetime import datetime
from zoneinfo import ZoneInfo
from services import VAPIService, SmartsheetService
from config import (
    CROSS_SELLS_ASSISTANT_ID,
    RENEWAL_PLR_SHEET_ID,
    RENEWAL_WORKSPACE_NAME
)
from workflows.renewals import parse_date


def should_skip_cross_sell_row(customer):
    """
    Check if a row should be skipped for cross-sell calling
    
    Skip if ANY of:
    - done is checked/true
    - company is empty
    - client_phone_number is empty
    - LOB is not "Home" or monoline home policy
    
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

    # Use Client Phone Number
    phone_field = customer.get('client_phone_number', '') or customer.get('phone_number', '')
    if not phone_field.strip():
        return True, "Phone number is empty"

    # Check if it's a monoline home policy
    # This logic needs to be confirmed with business team
    # For now, we'll check LOB field
    lob = customer.get('lob', '').strip().lower()
    if lob and 'home' not in lob:
        return True, f"Not a home policy (LOB: {lob})"

    return False, ""


def get_cross_sell_customers_ready_for_calls(smartsheet_service):
    """
    Get all cross-sell customers ready for calls
    These are customers with only monoline home policy
    
    Returns:
        list: Customers ready for cross-sell calls
    """
    print("=" * 80)
    print("🔍 FETCHING CROSS-SELL CUSTOMERS (Monoline Home Policy)")
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
        should_skip, skip_reason = should_skip_cross_sell_row(customer)
        if should_skip:
            skipped_count += 1
            print(f"   ⏭️  Skipping row {customer.get('row_number')}: {skip_reason}")
            continue
        
        # TODO: Add logic to check if customer has ONLY home policy (monoline)
        # This may require checking other sheets or additional fields
        # For now, we'll include all home policy customers
        
        ready_customers.append(customer)
        print(f"   ✅ Row {customer.get('row_number')}: Ready for cross-sell call")
    
    print(f"\n📊 Summary:")
    print(f"   Ready for cross-sell: {len(ready_customers)} customers")
    print(f"   Skipped: {skipped_count} rows")
    
    return ready_customers


def format_cross_sell_call_entry(summary, evaluation):
    """Format a cross-sell call entry for appending"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entry = f"[Cross-Sell Call - {timestamp}]\n{summary}\n"
    eval_entry = f"[Cross-Sell Call - {timestamp}]\n{evaluation}\n"
    return entry, eval_entry


def update_after_cross_sell_call(smartsheet_service, customer, call_data):
    """
    Update Smartsheet after a cross-sell call
    
    Args:
        smartsheet_service: SmartsheetService instance
        customer: Customer dict
        call_data: Call result data from VAPI
    """
    # Extract call analysis
    analysis = call_data.get('analysis', {})
    summary = analysis.get('summary', 'No summary available')

    # Get evaluation
    evaluation = analysis.get('successEvaluation')
    if not evaluation:
        structured_data = analysis.get('structuredData', {})
        if structured_data:
            evaluation = structured_data.get('success', 'N/A')
        else:
            evaluation = 'N/A'

    evaluation = str(evaluation).lower()

    # Format entries
    summary_entry, eval_entry = format_cross_sell_call_entry(summary, evaluation)

    # Get existing values (if there are call tracking fields)
    existing_summary = customer.get('cross_sell_call_summary', '') or customer.get('ai_call_summary', '')
    existing_eval = customer.get('cross_sell_call_eval', '') or customer.get('ai_call_eval', '')

    # Append or create
    if existing_summary:
        new_summary = existing_summary + "\n---\n" + summary_entry
    else:
        new_summary = summary_entry

    if existing_eval:
        new_eval = existing_eval + "\n---\n" + eval_entry
    else:
        new_eval = eval_entry

    # Update fields (adjust field names based on actual sheet structure)
    updates = {
        'cross_sell_call_summary': new_summary,
        'cross_sell_call_eval': new_eval,
    }

    # Perform update
    success = smartsheet_service.update_customer_fields(customer, updates)

    if success:
        print(f"✅ Smartsheet updated successfully")
    else:
        print(f"❌ Smartsheet update failed")

    return success


def run_cross_sells_calling(test_mode=False, schedule_at=None, auto_confirm=False):
    """
    Main function to run cross-sells calling workflow
    
    Args:
        test_mode: If True, skip actual calls and Smartsheet updates (default: False)
        schedule_at: Optional datetime to schedule calls
        auto_confirm: If True, skip user confirmation prompt (for cron jobs) (default: False)
    """
    print("=" * 80)
    print("🚀 CROSS-SELLS CALLING SYSTEM")
    if test_mode:
        print("🧪 TEST MODE - No actual calls or updates will be made")
    print("=" * 80)
    print("📋 Courtesy outreach to monoline home policy customers")
    print("📞 Offering auto quote")
    print("=" * 80)
    
    try:
        # Initialize services
        smartsheet_service = SmartsheetService(sheet_id=RENEWAL_PLR_SHEET_ID)
        vapi_service = VAPIService()
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        return False
    
    # Get customers ready for cross-sell calls
    ready_customers = get_cross_sell_customers_ready_for_calls(smartsheet_service)
    
    if len(ready_customers) == 0:
        print("\n✅ No customers ready for cross-sell calls today")
        return True
    
    # Show summary
    print(f"\n{'=' * 80}")
    print(f"📊 CROSS-SELL CUSTOMERS READY FOR CALLS:")
    print(f"{'=' * 80}")
    print(f"   Total: {len(ready_customers)} customers")
    
    for i, customer in enumerate(ready_customers[:10], 1):
        print(f"   {i}. {customer.get('company', 'Unknown')} - {customer.get('client_phone_number', 'N/A')}")
    
    if len(ready_customers) > 10:
        print(f"   ... and {len(ready_customers) - 10} more")
    
    print(f"\n{'=' * 80}")
    if not test_mode:
        print(f"⚠️  WARNING: This will make {len(ready_customers)} cross-sell phone calls!")
        print(f"💰 This will incur charges for each call")
    else:
        print(f"🧪 TEST MODE: Will simulate {len(ready_customers)} calls (no charges)")
    print(f"{'=' * 80}")

    # Ask for confirmation
    if not test_mode and not auto_confirm:
        response = input(f"\nProceed with cross-sells calling? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ Cross-sells calling cancelled")
            return False
    elif auto_confirm:
        print(f"🤖 AUTO-CONFIRM: Proceeding automatically (cron mode)")
    
    # Process calls
    total_success = 0
    total_failed = 0

    if test_mode:
        print(f"\n🧪 TEST MODE: Simulating {len(ready_customers)} cross-sell calls...")
        for customer in ready_customers:
            print(f"   ✅ [SIMULATED] Would call: {customer.get('company', 'Unknown')}")
            total_success += 1
    else:
        # Make batch calls
        print(f"\n📞 Making cross-sell calls...")
        print(f"🤖 Using Assistant: {CROSS_SELLS_ASSISTANT_ID}")
        
        results = vapi_service.make_batch_call_with_assistant(
            ready_customers,
            CROSS_SELLS_ASSISTANT_ID,
            schedule_immediately=(schedule_at is None),
            schedule_at=schedule_at
        )

        if results:
            print(f"\n✅ Cross-sell calls completed")

            # Update Smartsheet if calls were immediate
            if schedule_at is None:
                for customer, call_data in zip(ready_customers, results):
                    if call_data:
                        update_after_cross_sell_call(smartsheet_service, customer, call_data)
                        total_success += 1
                    else:
                        total_failed += 1
            else:
                print(f"   ⏰ Calls scheduled - Smartsheet will be updated after calls complete")
                total_success += len(ready_customers)
        else:
            print(f"\n❌ Cross-sell calls failed")
            total_failed += len(ready_customers)
    
    # Final summary
    print(f"\n{'=' * 80}")
    print(f"🏁 CROSS-SELLS CALLING COMPLETE")
    print(f"{'=' * 80}")
    print(f"   ✅ Successful: {total_success}")
    print(f"   ❌ Failed: {total_failed}")
    print(f"   📊 Total: {total_success + total_failed}")
    print(f"{'=' * 80}")
    
    return True


if __name__ == "__main__":
    import sys
    test_mode = "--test" in sys.argv or "-t" in sys.argv
    run_cross_sells_calling(test_mode=test_mode)

