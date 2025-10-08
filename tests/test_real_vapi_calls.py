#!/usr/bin/env python3
"""
Real VAPI Multi-Stage Call Testing
Based on test_end_to_end.py but using REAL VAPI calls instead of fake data
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
# Test Infrastructure
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
# Real VAPI Call Tests
# ========================================

def test_stage_0_to_1_real_vapi():
    """Test Stage 0 → 1 with REAL VAPI call"""
    print("\n" + "=" * 80)
    print("🧪 TEST 1: Stage 0 → 1 (1st Reminder Call - REAL VAPI)")
    print("=" * 80)

    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
    vapi_service = VAPIService()
    test_manager = TestRowManager(smartsheet_service, CANCELLATION_SHEET_ID)

    # Prepare test data
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
        # Create customer object
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

            # Assertions
            try:
                assert stage == "1", f"Expected stage 1, got {stage}"
                assert summary, "Summary should not be empty"
                assert fu_date, "Follow-up date should be set"
                print(f"\n✅ TEST 1 PASSED - Successfully transitioned from Stage 0 → 1")
                return True
            except AssertionError as e:
                print(f"\n❌ TEST 1 FAILED - {e}")
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


def test_stage_1_to_2_real_vapi():
    """Test Stage 1 → 2 with REAL VAPI call"""
    print("\n" + "=" * 80)
    print("🧪 TEST 2: Stage 1 → 2 (2nd Reminder Call - REAL VAPI)")
    print("=" * 80)

    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
    vapi_service = VAPIService()
    test_manager = TestRowManager(smartsheet_service, CANCELLATION_SHEET_ID)

    # Prepare test data (Stage 1)
    today = datetime.now().date()
    test_id = int(time.time())

    test_data = {
        "Client ID": f"TEST-STAGE1-{test_id}",
        "Policy Number": f"POL-TEST-{test_id}",
        "Phone number": TEST_CUSTOMER_PHONE,  # From config.TEST_CUSTOMER_PHONE
        "Company": f"Test Company Stage1 {test_id}",
        "Cancellation Date": (today + timedelta(days=12)).strftime('%Y-%m-%d'),
        "Amount Due": "500.00",
        "F/U Date": today.strftime('%Y-%m-%d'),
        "AI Call Stage": "1",  # Starting at Stage 1
        "AI Call Summary": f"[Call 1 - {today.strftime('%Y-%m-%d %H:%M:%S')}]\nFirst call completed - customer acknowledged the cancellation notice.\n",
        "AI Call Eval": f"[Call 1 - {today.strftime('%Y-%m-%d %H:%M:%S')}]\nTrue\n",
        "Done?": False
    }

    print(f"\n📝 Step 1: Creating test row at Stage 1...")
    print(f"   Client ID: {test_data['Client ID']}")
    print(f"   Company: {test_data['Company']}")
    print(f"   Current Stage: 1")
    print(f"   F/U Date: {test_data['F/U Date']}")

    created_row = test_manager.create_test_row(test_data)
    row_id = created_row.id
    print(f"✅ Test row created (Row ID: {row_id})")

    wait_with_message(PAUSE_AFTER_CREATE, "Pausing after row creation...")

    try:
        customer = {
            "client_id": test_data["Client ID"],
            "company": test_data["Company"],
            "phone_number": test_data["Phone number"],
            "cancellation_date": test_data["Cancellation Date"],
            "f_u_date": test_data["F/U Date"],
            "amount_due": test_data["Amount Due"],
            "ai_call_summary": test_data["AI Call Summary"],
            "ai_call_eval": test_data["AI Call Eval"],
            "ai_call_stage": "1",
            "row_id": row_id,
            "row_number": created_row.row_number
        }

        # Get assistant ID for Stage 1
        assistant_id = get_assistant_id_for_stage(1)
        print(f"\n📞 Step 2: Making REAL VAPI call (2nd Reminder)...")
        print(f"   🤖 Using Assistant ID: {assistant_id}")
        print(f"   📱 Calling: {customer['phone_number']}")

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
        success = update_after_call(smartsheet_service, customer, call_data, current_stage=1)

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

            # Assertions
            try:
                assert stage == "2", f"Expected stage 2, got {stage}"
                assert summary, "Summary should not be empty"
                assert "Call 1" in summary and "Call 2" in summary, "Should have both call summaries"
                assert fu_date, "Follow-up date should be set"
                print(f"\n✅ TEST 2 PASSED - Successfully transitioned from Stage 1 → 2")
                return True
            except AssertionError as e:
                print(f"\n❌ TEST 2 FAILED - {e}")
                return False
        else:
            print(f"❌ Could not retrieve row data")
            return False

    finally:
        wait_with_message(PAUSE_BEFORE_DELETE, "Pausing before cleanup...")
        print(f"\n🧹 Step 5: Cleaning up...")
        test_manager.delete_test_row(row_id)
        print(f"✅ Test row deleted")


def test_stage_2_to_3_real_vapi():
    """Test Stage 2 → 3 (Final call, Done=True) with REAL VAPI call"""
    print("\n" + "=" * 80)
    print("🧪 TEST 3: Stage 2 → 3 (3rd/Final Reminder - REAL VAPI)")
    print("=" * 80)

    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
    vapi_service = VAPIService()
    test_manager = TestRowManager(smartsheet_service, CANCELLATION_SHEET_ID)

    today = datetime.now().date()
    test_id = int(time.time())

    test_data = {
        "Client ID": f"TEST-STAGE2-{test_id}",
        "Policy Number": f"POL-TEST-{test_id}",
        "Phone number": TEST_CUSTOMER_PHONE,  # From config.TEST_CUSTOMER_PHONE
        "Company": f"Test Company Stage2 {test_id}",
        "Cancellation Date": (today + timedelta(days=5)).strftime('%Y-%m-%d'),
        "Amount Due": "500.00",
        "F/U Date": today.strftime('%Y-%m-%d'),
        "AI Call Stage": "2",  # Starting at Stage 2
        "AI Call Summary": f"[Call 1 - {today.strftime('%Y-%m-%d %H:%M:%S')}]\nFirst call completed.\n---\n[Call 2 - {today.strftime('%Y-%m-%d %H:%M:%S')}]\nSecond reminder call completed.\n",
        "AI Call Eval": f"[Call 1 - {today.strftime('%Y-%m-%d %H:%M:%S')}]\nTrue\n---\n[Call 2 - {today.strftime('%Y-%m-%d %H:%M:%S')}]\nTrue\n",
        "Done?": False
    }

    print(f"\n📝 Step 1: Creating test row at Stage 2...")
    print(f"   Client ID: {test_data['Client ID']}")
    print(f"   Company: {test_data['Company']}")
    print(f"   Current Stage: 2")
    print(f"   F/U Date: {test_data['F/U Date']}")

    created_row = test_manager.create_test_row(test_data)
    row_id = created_row.id
    print(f"✅ Test row created (Row ID: {row_id})")

    wait_with_message(PAUSE_AFTER_CREATE, "Pausing after row creation...")

    try:
        customer = {
            "client_id": test_data["Client ID"],
            "company": test_data["Company"],
            "phone_number": test_data["Phone number"],
            "cancellation_date": test_data["Cancellation Date"],
            "f_u_date": test_data["F/U Date"],
            "amount_due": test_data["Amount Due"],
            "ai_call_summary": test_data["AI Call Summary"],
            "ai_call_eval": test_data["AI Call Eval"],
            "ai_call_stage": "2",
            "row_id": row_id,
            "row_number": created_row.row_number
        }

        # Get assistant ID for Stage 2
        assistant_id = get_assistant_id_for_stage(2)
        print(f"\n📞 Step 2: Making REAL VAPI call (3rd/Final Reminder)...")
        print(f"   🤖 Using Assistant ID: {assistant_id}")
        print(f"   📱 Calling: {customer['phone_number']}")

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
        end_reason = call_data.get('endedReason', '')

        # Check if customer didn't answer
        if end_reason == 'customer-did-not-answer':
            print(f"\n⚠️  Customer did not answer")
            print(f"   📊 Call ID: {call_data.get('id', 'N/A')}")
            print(f"   💰 Cost: ${call_data.get('cost', 'N/A')}")
            print(f"\n⏭️  Skipping Smartsheet update (no conversation data)")
            return False

        print(f"\n✅ Call completed successfully")
        print(f"   📊 Call ID: {call_data.get('id', 'N/A')}")
        print(f"   ⏱️  Duration: {call_data.get('duration', 'N/A')}s")
        print(f"   💰 Cost: ${call_data.get('cost', 'N/A')}")

        wait_with_message(PAUSE_AFTER_CALL, "Pausing after VAPI call...")

        # Update Smartsheet
        print(f"\n📝 Step 3: Updating Smartsheet...")
        success = update_after_call(smartsheet_service, customer, call_data, current_stage=2)

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
            done = row_data.get("Done?", "")

            print(f"   • AI Call Stage: {stage}")
            print(f"   • AI Call Summary: {summary[:100]}..." if len(summary) > 100 else f"   • AI Call Summary: {summary}")
            print(f"   • AI Call Eval: {eval_result[:50]}..." if len(eval_result) > 50 else f"   • AI Call Eval: {eval_result}")
            print(f"   • F/U Date: {fu_date}")
            print(f"   • Done?: {done}")

            # Assertions
            try:
                assert stage == "3", f"Expected stage 3, got {stage}"
                assert done in [True, "true", 1], f"Expected Done=True, got {done}"
                assert summary, "Summary should not be empty"
                assert "Call 1" in summary and "Call 2" in summary and "Call 3" in summary, "Should have all 3 call summaries"
                print(f"\n✅ TEST 3 PASSED - Successfully transitioned from Stage 2 → 3, Done=True")
                return True
            except AssertionError as e:
                print(f"\n❌ TEST 3 FAILED - {e}")
                return False
        else:
            print(f"❌ Could not retrieve row data")
            return False

    finally:
        wait_with_message(PAUSE_BEFORE_DELETE, "Pausing before cleanup...")
        print(f"\n🧹 Step 5: Cleaning up...")
        test_manager.delete_test_row(row_id)
        print(f"✅ Test row deleted")


# ========================================
# Main Test Runner
# ========================================

def run_all_tests():
    """Run all real VAPI call tests"""
    print("\n" + "=" * 80)
    print("🚀 REAL VAPI MULTI-STAGE CALL TESTING")
    print("=" * 80)
    print("⚠️  WARNING: This will make REAL phone calls and incur charges!")
    print(f"📱 Using test phone number: {TEST_CUSTOMER_PHONE}")
    print("=" * 80)

    response = input("\n⚠️  Proceed with real VAPI call testing? (y/N): ").strip().lower()

    if response not in ['y', 'yes']:
        print("❌ Testing cancelled")
        return

    results = {
        "Test 1 (Stage 0→1)": False,
        "Test 2 (Stage 1→2)": False,
        "Test 3 (Stage 2→3)": False
    }

    try:
        results["Test 1 (Stage 0→1)"] = test_stage_0_to_1_real_vapi()
    except Exception as e:
        print(f"❌ Test 1 failed with exception: {e}")

    try:
        results["Test 2 (Stage 1→2)"] = test_stage_1_to_2_real_vapi()
    except Exception as e:
        print(f"❌ Test 2 failed with exception: {e}")

    try:
        results["Test 3 (Stage 2→3)"] = test_stage_2_to_3_real_vapi()
    except Exception as e:
        print(f"❌ Test 3 failed with exception: {e}")

    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    total_passed = sum(results.values())
    total_tests = len(results)

    print(f"\n🏁 Total: {total_passed}/{total_tests} tests passed")
    print("=" * 80)


if __name__ == "__main__":
    run_all_tests()
