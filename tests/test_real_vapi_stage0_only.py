#!/usr/bin/env python3
"""
Real VAPI Stage 0 Test (First Call Only)
Quick test for Stage 0 → 1 transition (1st Reminder Call) with REAL VAPI call
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
PAUSE_AFTER_CREATE = 5    # Pause after creating test row
PAUSE_AFTER_CALL = 10     # Pause after VAPI call completes
PAUSE_AFTER_UPDATE = 5    # Pause after Smartsheet update
PAUSE_BEFORE_DELETE = 5   # Pause before cleanup


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
# Main Test Function
# ========================================

def test_stage_0_only():
    """Test Stage 0 → 1 with REAL VAPI call (1st Reminder)"""
    print("\n" + "=" * 80)
    print("🧪 REAL VAPI TEST: Stage 0 → 1 (1st Reminder Call)")
    print("=" * 80)
    print("⚠️  WARNING: This will make a REAL phone call and incur charges!")
    print(f"📱 Using test phone number: {TEST_CUSTOMER_PHONE}")
    print("=" * 80)

    response = input("\n⚠️  Proceed with real VAPI call? (y/N): ").strip().lower()

    if response not in ['y', 'yes']:
        print("❌ Test cancelled")
        return False

    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
    vapi_service = VAPIService()
    test_manager = TestRowManager(smartsheet_service, CANCELLATION_SHEET_ID)

    # Prepare test data (Stage 0 - never called before)
    today = datetime.now().date()
    test_id = int(time.time())

    test_data = {
        "Client ID": f"TEST-STAGE0-{test_id}",
        "Policy Number": f"POL-TEST-{test_id}",
        "Phone number": TEST_CUSTOMER_PHONE,  # From config.TEST_CUSTOMER_PHONE
        "Company": f"Test Company Stage0 {test_id}",
        "Cancellation Date": (today + timedelta(days=15)).strftime('%Y-%m-%d'),
        "Amount Due": "500.00",
        "F/U Date": today.strftime('%Y-%m-%d'),
        "AI Call Stage": "",  # Empty = Stage 0 (never called)
        "AI Call Summary": "",
        "AI Call Eval": "",
        "Done?": False
    }

    print(f"\n📝 Step 1: Creating test row at Stage 0...")
    print(f"   Client ID: {test_data['Client ID']}")
    print(f"   Company: {test_data['Company']}")
    print(f"   Current Stage: 0 (never called)")
    print(f"   F/U Date: {test_data['F/U Date']}")

    created_row = test_manager.create_test_row(test_data)
    row_id = created_row.id
    print(f"✅ Test row created (Row ID: {row_id})")

    wait_with_message(PAUSE_AFTER_CREATE, "Pausing after row creation (check Smartsheet)...")

    try:
        customer = {
            "client_id": test_data["Client ID"],
            "company": test_data["Company"],
            "phone_number": test_data["Phone number"],
            "cancellation_date": test_data["Cancellation Date"],
            "f_u_date": test_data["F/U Date"],
            "amount_due": test_data["Amount Due"],
            "ai_call_summary": "",
            "ai_call_eval": "",
            "ai_call_stage": "",
            "row_id": row_id,
            "row_number": created_row.row_number
        }

        # Get assistant ID for Stage 0 (1st reminder)
        assistant_id = get_assistant_id_for_stage(0)
        print(f"\n📞 Step 2: Making REAL VAPI call (1st Reminder)...")
        print(f"   🤖 Using Assistant ID: {assistant_id}")
        print(f"   📱 Calling: {customer['phone_number']}")
        print(f"   🏢 Company: {customer['company']}")

        # Make REAL VAPI call
        results = vapi_service.make_batch_call_with_assistant(
            [customer],
            assistant_id,
            schedule_immediately=True
        )

        if not results or not results[0]:
            print(f"❌ VAPI call failed")
            return False

        call_data = results[0]
        print(f"\n✅ Call completed successfully")
        print(f"   📊 Call ID: {call_data.get('id', 'N/A')}")
        print(f"   ⏱️  Duration: {call_data.get('duration', 'N/A')}s")
        print(f"   💰 Cost: ${call_data.get('cost', 'N/A')}")

        wait_with_message(PAUSE_AFTER_CALL, "Pausing after VAPI call...")

        # Update Smartsheet
        print(f"\n📝 Step 3: Updating Smartsheet...")
        success = update_after_call(smartsheet_service, customer, call_data, current_stage=0)

        if not success:
            print(f"❌ Smartsheet update failed")
            return False

        wait_with_message(PAUSE_AFTER_UPDATE, "Pausing after update...")

        # Verify
        print(f"\n🔍 Step 4: Verifying update...")
        row_data = test_manager.get_row_data(row_id)

        if row_data:
            stage = row_data.get("AI Call Stage", "")
            summary = row_data.get("AI Call Summary", "")
            eval_result = row_data.get("AI Call Eval", "")
            fu_date = row_data.get("F/U Date", "")

            print(f"   • AI Call Stage: {stage}")
            print(f"   • AI Call Summary: {summary[:100]}..." if len(summary) > 100 else f"   • AI Call Summary: {summary}")
            print(f"   • AI Call Eval: {eval_result[:50]}..." if len(eval_result) > 50 else f"   • AI Call Eval: {eval_result}")
            print(f"   • F/U Date: {fu_date}")

            if stage == "1":
                print(f"\n✅ TEST PASSED - Successfully transitioned from Stage 0 → 1")
                return True
            else:
                print(f"\n❌ TEST FAILED - Expected stage 1, got {stage}")
                return False
        else:
            print(f"❌ Could not retrieve row data")
            return False

    finally:
        # Cleanup
        wait_with_message(PAUSE_BEFORE_DELETE, "Pausing before cleanup...")
        print(f"\n🧹 Step 5: Cleaning up...")
        test_manager.delete_test_row(row_id)
        print(f"✅ Test row deleted")


# ========================================
# Entry Point
# ========================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🚀 REAL VAPI SINGLE STAGE TEST - First Call Only")
    print("=" * 80)
    print("📋 This test will:")
    print("   1. Create a test row at Stage 0 (never called)")
    print("   2. Make a REAL VAPI call with 1st Reminder assistant")
    print("   3. Update Smartsheet to Stage 1")
    print("   4. Verify the transition")
    print("   5. Clean up test data")
    print("=" * 80)

    success = test_stage_0_only()

    print("\n" + "=" * 80)
    if success:
        print("✅ FIRST CALL TEST COMPLETED SUCCESSFULLY")
    else:
        print("❌ FIRST CALL TEST FAILED")
    print("=" * 80)
