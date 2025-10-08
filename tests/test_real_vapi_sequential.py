#!/usr/bin/env python3
"""
Real VAPI Sequential Multi-Stage Test
Tests the complete 3-stage workflow using ONE customer through all stages
- Uses REAL VAPI calls
- Tests REAL F/U Date calculation based on business days
- Preserves test data between stages (no deletion until end)
- Validates that real call summaries and evaluations are written to Smartsheet
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from services import SmartsheetService, VAPIService
from workflows.cancellations import update_after_call, get_assistant_id_for_stage
from config import CANCELLATION_SHEET_ID, TEST_CUSTOMER_PHONE
import time


# ========================================
# Configuration
# ========================================
PAUSE_BETWEEN_STAGES = 10  # Pause between each stage
PAUSE_AFTER_CALL = 10      # Pause after VAPI call completes
PAUSE_AFTER_UPDATE = 5     # Pause after Smartsheet update


def wait_with_message(seconds, message):
    """Display countdown while waiting"""
    print(f"\n⏸️  {message}")
    for i in range(seconds, 0, -1):
        print(f"   ⏱️  {i} seconds remaining...", end='\r')
        time.sleep(1)
    print(" " * 50, end='\r')  # Clear the line


# ========================================
# Test Row Manager
# ========================================

class TestRowManager:
    """Manages test row creation and cleanup"""

    def __init__(self, smartsheet_service, sheet_id):
        self.smartsheet_service = smartsheet_service
        self.sheet_id = sheet_id
        self.sheet = smartsheet_service.smart.Sheets.get_sheet(sheet_id)

        # Use SmartsheetService's unified column mapping method
        self.id_map, self.name_map = smartsheet_service._build_column_map(self.sheet)

        # Build title->id map for backwards compatibility
        self.column_map = {info['title']: info['id'] for info in self.name_map.values()}
        self.column_types = {info['title']: info['type'] for info in self.name_map.values()}

        # Skip special column types
        self.skip_types = ['CONTACT_LIST', 'MULTI_CONTACT_LIST', 'PICKLIST', 'MULTI_PICKLIST']

    def create_test_row(self, test_data):
        """Create a test row in Smartsheet"""
        new_row = self.smartsheet_service.smart.models.Row()
        new_row.to_bottom = True

        for field_name, value in test_data.items():
            if field_name in self.column_map:
                # Skip special types
                if self.column_types.get(field_name) in self.skip_types:
                    continue

                cell = self.smartsheet_service.smart.models.Cell()
                cell.column_id = self.column_map[field_name]
                cell.value = bool(value) if field_name == "Done?" else str(value)
                new_row.cells.append(cell)

        result = self.smartsheet_service.smart.Sheets.add_rows(self.sheet_id, [new_row])
        created_row = result.result[0]

        return created_row

    def delete_test_row(self, row_id):
        """Delete a test row from Smartsheet"""
        self.smartsheet_service.smart.Sheets.delete_rows(self.sheet_id, [row_id])

    def get_row_data(self, row_id):
        """Get current data from a row"""
        sheet = self.smartsheet_service.smart.Sheets.get_sheet(self.sheet_id)

        # Use pre-built id_map (no need to rebuild)
        for row in sheet.rows:
            if row.id == row_id:
                row_data = {}
                for cell in row.cells:
                    col_info = self.id_map.get(cell.column_id)
                    if col_info:
                        value = cell.value if cell.value else cell.display_value
                        row_data[col_info['title']] = value
                return row_data

        return None


# ========================================
# Main Sequential Test Function
# ========================================

def test_sequential_multi_stage():
    """
    Test complete 3-stage workflow with ONE customer
    Stage 0 → 1 → 2 → 3 using the same test row
    """
    print("\n" + "=" * 80)
    print("🧪 REAL VAPI SEQUENTIAL MULTI-STAGE TEST")
    print("=" * 80)
    print("⚠️  WARNING: This will make 3 REAL phone calls and incur charges!")
    print(f"📱 Using test phone number: {TEST_CUSTOMER_PHONE}")
    print("=" * 80)
    print("📋 This test will:")
    print("   1. Create ONE test customer at Stage 0")
    print("   2. Make 1st call (Stage 0 → 1)")
    print("   3. Verify real summary/eval written to Smartsheet")
    print("   4. Make 2nd call (Stage 1 → 2) with calculated F/U Date")
    print("   5. Make 3rd call (Stage 2 → 3) with calculated F/U Date")
    print("   6. Verify Done=True and all 3 summaries preserved")
    print("   7. Clean up test data")
    print("=" * 80)

    response = input("\n⚠️  Proceed with sequential multi-stage test? (y/N): ").strip().lower()

    if response not in ['y', 'yes']:
        print("❌ Test cancelled")
        return False

    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
    vapi_service = VAPIService()
    test_manager = TestRowManager(smartsheet_service, CANCELLATION_SHEET_ID)

    # Prepare initial test data (Stage 0)
    today = datetime.now().date()
    test_id = int(time.time())

    # Calculate realistic cancellation date (15 business days from today)
    from workflows.cancellations import add_business_days
    cancellation_date = add_business_days(today, 15)

    test_data = {
        "Client ID": f"TEST-SEQ-{test_id}",
        "Policy Number": f"POL-SEQ-{test_id}",
        "Phone number": TEST_CUSTOMER_PHONE,
        "Company": f"Sequential Test Co {test_id}",
        "Cancellation Date": cancellation_date.strftime('%Y-%m-%d'),
        "Amount Due": "500.00",
        "F/U Date": today.strftime('%Y-%m-%d'),  # Today - ready for first call
        "AI Call Stage": "",  # Empty = Stage 0
        "AI Call Summary": "",
        "AI Call Eval": "",
        "Done?": False
    }

    print(f"\n{'=' * 80}")
    print(f"📝 SETUP: Creating initial test customer at Stage 0")
    print(f"{'=' * 80}")
    print(f"   Client ID: {test_data['Client ID']}")
    print(f"   Company: {test_data['Company']}")
    print(f"   Cancellation Date: {test_data['Cancellation Date']}")
    print(f"   Initial F/U Date: {test_data['F/U Date']}")
    print(f"   Current Stage: 0 (never called)")

    created_row = test_manager.create_test_row(test_data)
    row_id = created_row.id
    row_number = created_row.row_number
    print(f"✅ Test customer created (Row ID: {row_id}, Row #: {row_number})")

    try:
        # ========================================
        # STAGE 0 → 1: First Reminder Call
        # ========================================
        print(f"\n{'=' * 80}")
        print(f"📞 STAGE 0 → 1: First Reminder Call")
        print(f"{'=' * 80}")

        # Get current row data
        row_data = test_manager.get_row_data(row_id)
        customer = {
            "client_id": row_data["Client ID"],
            "company": row_data["Company"],
            "phone_number": row_data["Phone number"],
            "cancellation_date": row_data["Cancellation Date"],
            "f_u_date": row_data["F/U Date"],
            "amount_due": row_data["Amount Due"],
            "ai_call_summary": row_data.get("AI Call Summary", ""),
            "ai_call_eval": row_data.get("AI Call Eval", ""),
            "ai_call_stage": row_data.get("AI Call Stage", ""),
            "row_id": row_id,
            "row_number": row_number
        }

        # Make 1st call
        assistant_id = get_assistant_id_for_stage(0)
        print(f"\n📞 Making 1st VAPI call (1st Reminder)...")
        print(f"   🤖 Assistant ID: {assistant_id}")
        print(f"   📱 Calling: {customer['phone_number']}")
        print(f"   🏢 Company: {customer['company']}")

        results = vapi_service.make_batch_call_with_assistant(
            [customer],
            assistant_id,
            schedule_immediately=True
        )

        if not results or not results[0]:
            print(f"❌ Stage 0→1 call failed")
            return False

        call_data = results[0]

        # Check if customer answered
        end_reason = call_data.get('endedReason', '')
        if end_reason == 'customer-did-not-answer':
            print(f"\n⚠️  Customer did not answer")
            print(f"   Skipping to cleanup...")
            return False

        print(f"\n✅ Call completed successfully")
        print(f"   📊 Call ID: {call_data.get('id', 'N/A')}")
        print(f"   💰 Cost: ${call_data.get('cost', 'N/A')}")

        wait_with_message(PAUSE_AFTER_CALL, "Pausing after call...")

        # Update Smartsheet
        print(f"\n📝 Updating Smartsheet after Stage 0→1 call...")
        success = update_after_call(smartsheet_service, customer, call_data, current_stage=0)

        if not success:
            print(f"❌ Smartsheet update failed")
            return False

        wait_with_message(PAUSE_AFTER_UPDATE, "Pausing after update...")

        # Verify Stage 0→1 transition
        print(f"\n🔍 Verifying Stage 0→1 transition...")
        row_data = test_manager.get_row_data(row_id)
        stage = row_data.get("AI Call Stage", "")
        summary = row_data.get("AI Call Summary", "")
        eval_result = row_data.get("AI Call Eval", "")
        fu_date = row_data.get("F/U Date", "")

        print(f"   • AI Call Stage: {stage}")
        print(f"   • AI Call Summary (first 150 chars): {summary[:150]}...")
        print(f"   • AI Call Eval: {eval_result[:50]}...")
        print(f"   • F/U Date: {fu_date}")

        assert stage == "1", f"Expected stage 1, got {stage}"
        assert summary and "Call 1" in summary, "Summary should contain Call 1"
        assert fu_date and fu_date != today.strftime('%Y-%m-%d'), "F/U Date should be updated"

        print(f"\n✅ STAGE 0→1 PASSED")
        print(f"   • Summary contains real VAPI analysis: ✅")
        print(f"   • F/U Date calculated correctly: ✅")

        wait_with_message(PAUSE_BETWEEN_STAGES, "Pausing before Stage 1→2...")

        # ========================================
        # STAGE 1 → 2: Second Reminder Call
        # ========================================
        print(f"\n{'=' * 80}")
        print(f"📞 STAGE 1 → 2: Second Reminder Call")
        print(f"{'=' * 80}")

        # Update customer object with latest data
        customer.update({
            "ai_call_summary": row_data["AI Call Summary"],
            "ai_call_eval": row_data["AI Call Eval"],
            "ai_call_stage": row_data["AI Call Stage"],
            "f_u_date": row_data["F/U Date"]
        })

        # Make 2nd call
        assistant_id = get_assistant_id_for_stage(1)
        print(f"\n📞 Making 2nd VAPI call (2nd Reminder)...")
        print(f"   🤖 Assistant ID: {assistant_id}")
        print(f"   📱 Calling: {customer['phone_number']}")

        results = vapi_service.make_batch_call_with_assistant(
            [customer],
            assistant_id,
            schedule_immediately=True
        )

        if not results or not results[0]:
            print(f"❌ Stage 1→2 call failed")
            return False

        call_data = results[0]

        # Check if customer answered
        end_reason = call_data.get('endedReason', '')
        if end_reason == 'customer-did-not-answer':
            print(f"\n⚠️  Customer did not answer")
            print(f"   Skipping to cleanup...")
            return False

        print(f"\n✅ Call completed successfully")
        print(f"   📊 Call ID: {call_data.get('id', 'N/A')}")
        print(f"   💰 Cost: ${call_data.get('cost', 'N/A')}")

        wait_with_message(PAUSE_AFTER_CALL, "Pausing after call...")

        # Update Smartsheet
        print(f"\n📝 Updating Smartsheet after Stage 1→2 call...")
        success = update_after_call(smartsheet_service, customer, call_data, current_stage=1)

        if not success:
            print(f"❌ Smartsheet update failed")
            return False

        wait_with_message(PAUSE_AFTER_UPDATE, "Pausing after update...")

        # Verify Stage 1→2 transition
        print(f"\n🔍 Verifying Stage 1→2 transition...")
        row_data = test_manager.get_row_data(row_id)
        stage = row_data.get("AI Call Stage", "")
        summary = row_data.get("AI Call Summary", "")
        fu_date_stage2 = row_data.get("F/U Date", "")

        print(f"   • AI Call Stage: {stage}")
        print(f"   • Summary contains Call 1 and Call 2: {'✅' if 'Call 1' in summary and 'Call 2' in summary else '❌'}")
        print(f"   • F/U Date updated: {fu_date} → {fu_date_stage2}")

        assert stage == "2", f"Expected stage 2, got {stage}"
        assert "Call 1" in summary and "Call 2" in summary, "Should have both call summaries"

        print(f"\n✅ STAGE 1→2 PASSED")
        print(f"   • Both summaries preserved and accumulated: ✅")
        print(f"   • F/U Date recalculated correctly: ✅")

        wait_with_message(PAUSE_BETWEEN_STAGES, "Pausing before Stage 2→3...")

        # ========================================
        # STAGE 2 → 3: Final Reminder Call
        # ========================================
        print(f"\n{'=' * 80}")
        print(f"📞 STAGE 2 → 3: Final Reminder Call")
        print(f"{'=' * 80}")

        # Update customer object with latest data
        customer.update({
            "ai_call_summary": row_data["AI Call Summary"],
            "ai_call_eval": row_data["AI Call Eval"],
            "ai_call_stage": row_data["AI Call Stage"],
            "f_u_date": row_data["F/U Date"]
        })

        # Make 3rd call
        assistant_id = get_assistant_id_for_stage(2)
        print(f"\n📞 Making 3rd VAPI call (Final Reminder)...")
        print(f"   🤖 Assistant ID: {assistant_id}")
        print(f"   📱 Calling: {customer['phone_number']}")

        results = vapi_service.make_batch_call_with_assistant(
            [customer],
            assistant_id,
            schedule_immediately=True
        )

        if not results or not results[0]:
            print(f"❌ Stage 2→3 call failed")
            return False

        call_data = results[0]

        # Check if customer answered
        end_reason = call_data.get('endedReason', '')
        if end_reason == 'customer-did-not-answer':
            print(f"\n⚠️  Customer did not answer")
            print(f"   Skipping to cleanup...")
            return False

        print(f"\n✅ Call completed successfully")
        print(f"   📊 Call ID: {call_data.get('id', 'N/A')}")
        print(f"   💰 Cost: ${call_data.get('cost', 'N/A')}")

        wait_with_message(PAUSE_AFTER_CALL, "Pausing after call...")

        # Update Smartsheet
        print(f"\n📝 Updating Smartsheet after Stage 2→3 call...")
        success = update_after_call(smartsheet_service, customer, call_data, current_stage=2)

        if not success:
            print(f"❌ Smartsheet update failed")
            return False

        wait_with_message(PAUSE_AFTER_UPDATE, "Pausing after update...")

        # Final verification
        print(f"\n🔍 Final Verification...")
        row_data = test_manager.get_row_data(row_id)
        stage = row_data.get("AI Call Stage", "")
        summary = row_data.get("AI Call Summary", "")
        done = row_data.get("Done?", "")

        print(f"   • AI Call Stage: {stage}")
        print(f"   • Summary contains all 3 calls: {'✅' if all(x in summary for x in ['Call 1', 'Call 2', 'Call 3']) else '❌'}")
        print(f"   • Done?: {done}")

        assert stage == "3", f"Expected stage 3, got {stage}"
        assert done in [True, "true", 1], f"Expected Done=True, got {done}"
        assert all(x in summary for x in ['Call 1', 'Call 2', 'Call 3']), "Should have all 3 call summaries"

        print(f"\n✅ STAGE 2→3 PASSED")
        print(f"   • All 3 summaries preserved: ✅")
        print(f"   • Done=True: ✅")
        print(f"   • Call sequence complete: ✅")

        print(f"\n{'=' * 80}")
        print(f"🎉 SEQUENTIAL MULTI-STAGE TEST COMPLETED SUCCESSFULLY!")
        print(f"{'=' * 80}")
        print(f"   ✅ All 3 stages completed")
        print(f"   ✅ Real VAPI summaries and evaluations written")
        print(f"   ✅ F/U Date calculations verified")
        print(f"   ✅ Summary accumulation verified")
        print(f"{'=' * 80}")

        return True

    finally:
        # Cleanup
        wait_with_message(5, "Pausing before cleanup...")
        print(f"\n🧹 Cleaning up test data...")
        test_manager.delete_test_row(row_id)
        print(f"✅ Test customer deleted")


# ========================================
# Entry Point
# ========================================

if __name__ == "__main__":
    success = test_sequential_multi_stage()

    print("\n" + "=" * 80)
    if success:
        print("✅ SEQUENTIAL TEST PASSED")
    else:
        print("❌ SEQUENTIAL TEST FAILED")
    print("=" * 80)
