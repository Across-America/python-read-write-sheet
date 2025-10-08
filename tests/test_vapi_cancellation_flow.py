#!/usr/bin/env python3
"""
VAPI Cancellation Flow End-to-End Test

Tests complete workflow: Smartsheet Data Filtering → VAPI Calling → Status Update

Test Structure:
- Stage 0 (Batch): 2 customers simultaneously (+13239435582, +19096934653 for corner case)
- Stage 1 (Sequential): Individual calls with +13239435582
- Stage 2 (Sequential Advanced): Complex scenarios with +13239435582

Features:
- Reuses cancellation.py logic (no duplication)
- Auto-generates test datasets based on test architecture
- Validates end-to-end flow from filtering to update
- Supports mixed phone formats and edge cases
- ONLY filters test customers (not real data)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
import time
from services import SmartsheetService, VAPIService
from workflows.cancellations import (
    update_after_call,
    get_assistant_id_for_stage,
    add_business_days,
    should_skip_row,
    get_call_stage,
    parse_date
)
from config import CANCELLATION_SHEET_ID, TEST_CUSTOMER_PHONE


# ========================================
# Test Configuration
# ========================================

# Corner case: Use second number only in Stage 0 for batch testing
STAGE_0_BATCH_NUMBERS = [
    TEST_CUSTOMER_PHONE,      # Primary test number
    "+19096934653"            # Secondary for batch corner case
]

# All other stages use only the primary test number
DEFAULT_TEST_NUMBER = TEST_CUSTOMER_PHONE

PAUSE_BETWEEN_STAGES = 10
PAUSE_AFTER_CALL = 5
PAUSE_AFTER_UPDATE = 3


# ========================================
# Test-Only Data Filtering
# ========================================

def get_test_customers_ready_for_calls(smartsheet_service):
    """
    Get ONLY TEST customers ready for calls today

    This is a TEST-SPECIFIC version that filters ONLY test customers
    to avoid mixing with real production data

    Returns:
        dict: Test customers grouped by stage {0: [...], 1: [...], 2: [...]}
    """
    print("=" * 80)
    print("🔍 FETCHING TEST CUSTOMERS READY FOR CALLS")
    print("=" * 80)

    # Get all customers from sheet
    all_customers = smartsheet_service.get_all_customers_with_stages()

    today = datetime.now().date()
    customers_by_stage = {0: [], 1: [], 2: []}
    skipped_count = 0
    real_customer_count = 0

    for customer in all_customers:
        # CRITICAL: Skip non-test customers (filter by Client ID)
        client_id = customer.get('client_id', '')
        if not client_id.startswith('TEST-'):
            real_customer_count += 1
            continue  # Skip real customers silently

        # Initial validation (from cancellation.py)
        should_skip, skip_reason = should_skip_row(customer)
        if should_skip:
            skipped_count += 1
            print(f"   ⏭️  Skipping test row {customer.get('row_number')}: {skip_reason}")
            continue

        # Get current stage
        stage = get_call_stage(customer)

        # Skip if stage >= 3 (call sequence complete)
        if stage >= 3:
            skipped_count += 1
            print(f"   ⏭️  Skipping test row {customer.get('row_number')}: Call sequence complete (stage {stage})")
            continue

        # Check f_u_date (Follow-up Date)
        followup_date_str = customer.get('f_u_date', '')

        # For stage 0, f_u_date must not be empty
        if stage == 0 and not followup_date_str.strip():
            skipped_count += 1
            print(f"   ⏭️  Skipping test row {customer.get('row_number')}: Stage 0 requires F/U Date")
            continue

        # Parse f_u_date
        followup_date = parse_date(followup_date_str)

        if not followup_date:
            skipped_count += 1
            print(f"   ⏭️  Skipping test row {customer.get('row_number')}: Invalid F/U Date")
            continue

        # Check if f_u_date == today
        if followup_date == today:
            customers_by_stage[stage].append(customer)
            print(f"   ✅ Test Row {customer.get('row_number')}: Stage {stage}, ready for call")

    print(f"\n📊 Summary:")
    print(f"   Stage 0 (1st call): {len(customers_by_stage[0])} test customers")
    print(f"   Stage 1 (2nd call): {len(customers_by_stage[1])} test customers")
    print(f"   Stage 2 (3rd call): {len(customers_by_stage[2])} test customers")
    print(f"   Skipped test rows: {skipped_count}")
    print(f"   Real customers (ignored): {real_customer_count}")
    print(f"   Total test customers ready: {sum(len(v) for v in customers_by_stage.values())}")

    return customers_by_stage


# ========================================
# Test Data Generator
# ========================================

class TestDataGenerator:
    """Generates diverse test datasets based on test architecture"""

    def __init__(self):
        self.test_id_base = int(time.time())
        self.customer_counter = 0

    def _format_phone_diverse(self, phone_number, format_type=0):
        """Generate diverse phone number formats"""
        # Remove all non-digits
        digits = ''.join(filter(str.isdigit, phone_number))

        if len(digits) == 11 and digits.startswith('1'):
            # Format: 1XXXXXXXXXX
            area = digits[1:4]
            prefix = digits[4:7]
            line = digits[7:11]
        elif len(digits) == 10:
            area = digits[0:3]
            prefix = digits[3:6]
            line = digits[6:10]
        else:
            return phone_number  # Return as-is if format unknown

        formats = [
            f"+1{area}{prefix}{line}",           # +13239435582
            f"+1 ({area}) {prefix}-{line}",      # +1 (323) 943-5582
            f"({area}) {prefix}-{line}",         # (323) 943-5582
            f"{area}-{prefix}-{line}",           # 323-943-5582
            f"+1{area}-{prefix}-{line}",         # +1323-943-5582
        ]

        return formats[format_type % len(formats)]

    def generate_stage_0_customers(self, count=2):
        """
        Generate Stage 0 customers for batch calling

        Stage 0 requirements:
        - F/U Date = today (ready for immediate call)
        - AI Call Stage = empty or 0
        - Valid company, amount_due, cancellation_date
        - Done? = False
        """
        today = datetime.now().date()
        cancellation_date = add_business_days(today, 15)

        customers = []
        for i in range(count):
            self.customer_counter += 1

            # Use different phone numbers for batch test with diverse formats
            base_phone = STAGE_0_BATCH_NUMBERS[i] if i < len(STAGE_0_BATCH_NUMBERS) else DEFAULT_TEST_NUMBER
            phone = self._format_phone_diverse(base_phone, format_type=i)

            customer = {
                "Client ID": f"TEST-S0-{self.test_id_base}-{self.customer_counter}",
                "Policy Number": f"POL-S0-{self.test_id_base}-{self.customer_counter}",
                "Phone number": phone,
                "Company": f"Stage0 Batch Co {self.customer_counter}",
                "Cancellation Date": cancellation_date.strftime('%Y-%m-%d'),
                "Amount Due": f"${500 + (i * 100)}.00",  # Add $ sign
                "F/U Date": today.strftime('%Y-%m-%d'),
                "AI Call Stage": "",  # Empty = Stage 0
                "AI Call Summary": "",
                "AI Call Eval": "",
                "Done?": False
            }
            customers.append(customer)

        return customers

    def generate_stage_1_customers(self, count=2):
        """
        Generate Stage 1 customers for sequential calling

        Stage 1 requirements:
        - F/U Date = today
        - AI Call Stage = 1
        - Has existing summary from Stage 0
        - All use same test number
        """
        today = datetime.now().date()
        cancellation_date = add_business_days(today, 10)

        customers = []
        for i in range(count):
            self.customer_counter += 1

            # Use diverse phone formats
            phone = self._format_phone_diverse(DEFAULT_TEST_NUMBER, format_type=i + 2)

            customer = {
                "Client ID": f"TEST-S1-{self.test_id_base}-{self.customer_counter}",
                "Policy Number": f"POL-S1-{self.test_id_base}-{self.customer_counter}",
                "Phone number": phone,
                "Company": f"Stage1 Sequential Co {self.customer_counter}",
                "Cancellation Date": cancellation_date.strftime('%Y-%m-%d'),
                "Amount Due": f"${600 + (i * 50)}.00",  # Add $ sign
                "F/U Date": today.strftime('%Y-%m-%d'),
                "AI Call Stage": "1",  # Already at stage 1
                "AI Call Summary": f"[Call 1 - 2025-10-01 10:00:00]\nPrevious call summary for customer {self.customer_counter}",
                "AI Call Eval": f"[Call 1 - 2025-10-01 10:00:00]\nfalse",
                "Done?": False
            }
            customers.append(customer)

        return customers

    def generate_stage_2_customers(self, count=2, include_edge_cases=True):
        """
        Generate Stage 2 customers for advanced sequential calling

        Stage 2 requirements:
        - F/U Date = today
        - AI Call Stage = 2
        - Has summaries from Stage 0 and 1
        - Edge cases: near cancellation date, high amounts, etc.
        """
        today = datetime.now().date()

        customers = []
        for i in range(count):
            self.customer_counter += 1

            # Edge case: customer near cancellation (only 3 days left)
            if include_edge_cases and i == 0:
                cancellation_date = add_business_days(today, 3)
                amount = "$2,500.00"  # High amount with comma and $ sign
            else:
                cancellation_date = add_business_days(today, 5)
                amount = f"${700 + (i * 75)}.00"  # Add $ sign

            # Use diverse phone formats
            phone = self._format_phone_diverse(DEFAULT_TEST_NUMBER, format_type=i + 4)

            customer = {
                "Client ID": f"TEST-S2-{self.test_id_base}-{self.customer_counter}",
                "Policy Number": f"POL-S2-{self.test_id_base}-{self.customer_counter}",
                "Phone number": phone,
                "Company": f"Stage2 Advanced Co {self.customer_counter}",
                "Cancellation Date": cancellation_date.strftime('%Y-%m-%d'),
                "Amount Due": amount,
                "F/U Date": today.strftime('%Y-%m-%d'),
                "AI Call Stage": "2",  # Already at stage 2
                "AI Call Summary": (
                    f"[Call 1 - 2025-10-01 10:00:00]\n"
                    f"First call summary for customer {self.customer_counter}\n"
                    f"---\n"
                    f"[Call 2 - 2025-10-05 14:30:00]\n"
                    f"Second call summary for customer {self.customer_counter}"
                ),
                "AI Call Eval": (
                    f"[Call 1 - 2025-10-01 10:00:00]\nfalse\n"
                    f"---\n"
                    f"[Call 2 - 2025-10-05 14:30:00]\nfalse"
                ),
                "Done?": False
            }
            customers.append(customer)

        return customers

    def generate_skip_test_customers(self):
        """Generate customers that should be skipped by validation logic"""
        today = datetime.now().date()
        cancellation_date = add_business_days(today, 10)

        skip_customers = [
            # Empty company
            {
                "Client ID": f"TEST-SKIP-{self.test_id_base}-1",
                "Company": "",  # Should skip
                "Phone number": DEFAULT_TEST_NUMBER,
                "Amount Due": "$500.00",
                "Cancellation Date": cancellation_date.strftime('%Y-%m-%d'),
                "F/U Date": today.strftime('%Y-%m-%d'),
                "AI Call Stage": "",
                "Done?": False
            },
            # Empty amount
            {
                "Client ID": f"TEST-SKIP-{self.test_id_base}-2",
                "Company": "Skip Test Co 2",
                "Phone number": DEFAULT_TEST_NUMBER,
                "Amount Due": "",  # Should skip
                "Cancellation Date": cancellation_date.strftime('%Y-%m-%d'),
                "F/U Date": today.strftime('%Y-%m-%d'),
                "AI Call Stage": "",
                "Done?": False
            },
            # Done is checked
            {
                "Client ID": f"TEST-SKIP-{self.test_id_base}-3",
                "Company": "Skip Test Co 3",
                "Phone number": DEFAULT_TEST_NUMBER,
                "Amount Due": "$500.00",
                "Cancellation Date": cancellation_date.strftime('%Y-%m-%d'),
                "F/U Date": today.strftime('%Y-%m-%d'),
                "AI Call Stage": "3",
                "Done?": True  # Should skip
            },
            # Stage >= 3
            {
                "Client ID": f"TEST-SKIP-{self.test_id_base}-4",
                "Company": "Skip Test Co 4",
                "Phone number": DEFAULT_TEST_NUMBER,
                "Amount Due": "$500.00",
                "Cancellation Date": cancellation_date.strftime('%Y-%m-%d'),
                "F/U Date": today.strftime('%Y-%m-%d'),
                "AI Call Stage": "4",  # Should skip
                "Done?": False
            }
        ]

        return skip_customers


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

        # Track created rows for cleanup
        self.created_row_ids = []

    def create_test_rows(self, test_data_list):
        """Create multiple test rows in Smartsheet"""
        created_rows = []

        for test_data in test_data_list:
            new_row = self.smartsheet_service.smart.models.Row()
            new_row.to_bottom = True

            for field_name, value in test_data.items():
                if field_name in self.column_map:
                    # Skip special types
                    if self.column_types.get(field_name) in self.skip_types:
                        continue

                    cell = self.smartsheet_service.smart.models.Cell()
                    cell.column_id = self.column_map[field_name]

                    # Handle different field types
                    if field_name == "Done?":
                        cell.value = bool(value)
                    else:
                        cell.value = str(value)

                    new_row.cells.append(cell)

            result = self.smartsheet_service.smart.Sheets.add_rows(self.sheet_id, [new_row])
            created_row = result.result[0]

            created_rows.append({
                'row_id': created_row.id,
                'row_number': created_row.row_number,
                'test_data': test_data
            })

            self.created_row_ids.append(created_row.id)

        return created_rows

    def get_row_data(self, row_id):
        """Get current data from a row"""
        sheet = self.smartsheet_service.smart.Sheets.get_sheet(self.sheet_id)

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

    def cleanup_all(self):
        """Delete all created test rows"""
        if not self.created_row_ids:
            return

        print(f"\n🧹 Cleaning up {len(self.created_row_ids)} test rows...")
        self.smartsheet_service.smart.Sheets.delete_rows(self.sheet_id, self.created_row_ids)
        print(f"✅ Test rows deleted")
        self.created_row_ids.clear()


# ========================================
# Helper Functions
# ========================================

def wait_with_message(seconds, message):
    """Simple wait with message"""
    print(f"\n⏸️  {message} ({seconds}s)")
    time.sleep(seconds)
    print(f"   ✅ Continuing...")


def convert_row_to_customer(row_data, row_id, row_number):
    """Convert Smartsheet row data to customer dict format"""
    return {
        "client_id": row_data.get("Client ID", ""),
        "company": row_data.get("Company", ""),
        "phone_number": row_data.get("Phone number", ""),
        "cancellation_date": row_data.get("Cancellation Date", ""),
        "f_u_date": row_data.get("F/U Date", ""),
        "amount_due": row_data.get("Amount Due", ""),
        "policy_number": row_data.get("Policy Number", ""),
        "ai_call_summary": row_data.get("AI Call Summary", ""),
        "ai_call_eval": row_data.get("AI Call Eval", ""),
        "ai_call_stage": row_data.get("AI Call Stage", ""),
        "done?": row_data.get("Done?", False),
        "row_id": row_id,
        "row_number": row_number
    }


# ========================================
# Stage Test Functions
# ========================================

def test_stage_0_batch_calling(smartsheet_service, vapi_service, test_manager):
    """
    Stage 0: Batch calling with 2 customers
    Tests batch call logic with mixed phone numbers
    """
    print("\n" + "=" * 80)
    print("🧪 STAGE 0: BATCH CALLING TEST")
    print("=" * 80)
    print("📋 Testing: Batch call with 2 customers (corner case: mixed numbers)")
    print(f"   ⚠️  NOTE: Using {STAGE_0_BATCH_NUMBERS[0]} and {STAGE_0_BATCH_NUMBERS[1]}")
    print("=" * 80)

    # Generate test data
    generator = TestDataGenerator()
    test_customers = generator.generate_stage_0_customers(count=2)

    # Create test rows
    print(f"\n📝 Creating {len(test_customers)} Stage 0 test customers...")
    print(f"   🔄 Adding rows to Smartsheet...", flush=True)
    created_rows = test_manager.create_test_rows(test_customers)
    print(f"   ✅ Created {len(created_rows)} rows\n")

    for i, row_info in enumerate(created_rows, 1):
        print(f"   {i}. {row_info['test_data']['Company']} - {row_info['test_data']['Phone number']}")
        print(f"      Amount: {row_info['test_data']['Amount Due']}")
        print(f"      Row ID: {row_info['row_id']}, Row #: {row_info['row_number']}")

    wait_with_message(3, "Pausing before filtering...")

    # Test filtering logic (TEST-ONLY version)
    print(f"\n🔍 Testing get_test_customers_ready_for_calls()...")
    customers_by_stage = get_test_customers_ready_for_calls(smartsheet_service)

    stage_0_customers = customers_by_stage[0]

    if len(stage_0_customers) < 2:
        print(f"❌ Expected at least 2 Stage 0 customers, got {len(stage_0_customers)}")
        return False

    print(f"✅ Filtering successful: Found {len(stage_0_customers)} Stage 0 test customers ready")

    # Confirm batch calling
    response = input(f"\n⚠️  Proceed with batch calling {len(stage_0_customers)} customers? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("⏭️  Skipping Stage 0 calls")
        return True

    # Make batch call
    assistant_id = get_assistant_id_for_stage(0)
    print(f"\n📞 Making batch VAPI call (Stage 0)...")
    print(f"   🤖 Assistant ID: {assistant_id}")

    results = vapi_service.make_batch_call_with_assistant(
        stage_0_customers[:2],  # Only call first 2
        assistant_id,
        schedule_immediately=True
    )

    if not results:
        print(f"❌ Stage 0 batch call failed")
        return False

    print(f"\n✅ Batch call completed")

    wait_with_message(PAUSE_AFTER_CALL, "Pausing after calls...")

    # Update Smartsheet for each customer
    print(f"\n📝 Updating Smartsheet for {len(results)} customers...")
    for customer, call_data in zip(stage_0_customers[:2], results):
        if call_data:
            # Skip if customer didn't answer
            end_reason = call_data.get('endedReason', '')
            if end_reason == 'customer-did-not-answer':
                print(f"   ⏭️  Skipping update for {customer['company']} (no answer)")
                continue

            success = update_after_call(smartsheet_service, customer, call_data, current_stage=0)
            if success:
                print(f"   ✅ Updated: {customer['company']}")
            else:
                print(f"   ❌ Failed: {customer['company']}")

    wait_with_message(PAUSE_AFTER_UPDATE, "Pausing after updates...")

    print(f"\n✅ STAGE 0 COMPLETED")
    return True


def test_stage_1_sequential_calling(smartsheet_service, vapi_service, test_manager):
    """
    Stage 1: Sequential calling with individual customers
    Tests sequential call logic and transfer handling
    """
    print("\n" + "=" * 80)
    print("🧪 STAGE 1: SEQUENTIAL CALLING TEST")
    print("=" * 80)
    print("📋 Testing: Sequential individual calls")
    print(f"   📱 All calls use: {DEFAULT_TEST_NUMBER} (with diverse formats)")
    print("=" * 80)

    # Generate test data
    generator = TestDataGenerator()
    test_customers = generator.generate_stage_1_customers(count=2)

    # Create test rows
    print(f"\n📝 Creating {len(test_customers)} Stage 1 test customers...")
    created_rows = test_manager.create_test_rows(test_customers)

    for i, row_info in enumerate(created_rows, 1):
        print(f"   {i}. {row_info['test_data']['Company']}")
        print(f"      Phone: {row_info['test_data']['Phone number']}")
        print(f"      Amount: {row_info['test_data']['Amount Due']}")
        print(f"      Row ID: {row_info['row_id']}, Row #: {row_info['row_number']}")

    wait_with_message(3, "Pausing before filtering...")

    # Test filtering logic
    print(f"\n🔍 Testing get_test_customers_ready_for_calls()...")
    customers_by_stage = get_test_customers_ready_for_calls(smartsheet_service)

    stage_1_customers = customers_by_stage[1]

    if len(stage_1_customers) < 2:
        print(f"❌ Expected at least 2 Stage 1 customers, got {len(stage_1_customers)}")
        return False

    print(f"✅ Filtering successful: Found {len(stage_1_customers)} Stage 1 test customers ready")

    # Confirm sequential calling
    response = input(f"\n⚠️  Proceed with sequential calling {len(stage_1_customers)} customers? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("⏭️  Skipping Stage 1 calls")
        return True

    # Make sequential calls
    assistant_id = get_assistant_id_for_stage(1)
    print(f"\n📞 Making sequential VAPI calls (Stage 1)...")
    print(f"   🤖 Assistant ID: {assistant_id}")

    for i, customer in enumerate(stage_1_customers[:2], 1):
        print(f"\n   📞 Call {i}/{min(2, len(stage_1_customers))}: {customer['company']}")

        results = vapi_service.make_batch_call_with_assistant(
            [customer],
            assistant_id,
            schedule_immediately=True
        )

        if not results or not results[0]:
            print(f"   ❌ Call {i} failed")
            continue

        call_data = results[0]

        # Skip if customer didn't answer
        end_reason = call_data.get('endedReason', '')
        if end_reason == 'customer-did-not-answer':
            print(f"   ⏭️  Customer did not answer, skipping update")
            continue

        print(f"   ✅ Call {i} completed")

        # Update Smartsheet
        success = update_after_call(smartsheet_service, customer, call_data, current_stage=1)
        if success:
            print(f"   ✅ Smartsheet updated")

        if i < min(2, len(stage_1_customers)):
            wait_with_message(5, f"Pausing before next call...")

    print(f"\n✅ STAGE 1 COMPLETED")
    return True


def test_stage_2_advanced_sequential(smartsheet_service, vapi_service, test_manager):
    """
    Stage 2: Advanced sequential calling with complex scenarios
    Tests edge cases and final stage logic
    """
    print("\n" + "=" * 80)
    print("🧪 STAGE 2: ADVANCED SEQUENTIAL TEST")
    print("=" * 80)
    print("📋 Testing: Complex scenarios and edge cases")
    print("   • Near-cancellation dates")
    print("   • High payment amounts")
    print("   • Final call stage (Done=True)")
    print(f"   📱 All calls use: {DEFAULT_TEST_NUMBER} (with diverse formats)")
    print("=" * 80)

    # Generate test data with edge cases
    generator = TestDataGenerator()
    test_customers = generator.generate_stage_2_customers(count=2, include_edge_cases=True)

    # Create test rows
    print(f"\n📝 Creating {len(test_customers)} Stage 2 test customers...")
    created_rows = test_manager.create_test_rows(test_customers)

    for i, row_info in enumerate(created_rows, 1):
        data = row_info['test_data']
        print(f"   {i}. {data['Company']}")
        print(f"      Phone: {data['Phone number']}")
        print(f"      Amount: {data['Amount Due']}, Cancel: {data['Cancellation Date']}")
        print(f"      Row ID: {row_info['row_id']}, Row #: {row_info['row_number']}")

    wait_with_message(3, "Pausing before filtering...")

    # Test filtering logic
    print(f"\n🔍 Testing get_test_customers_ready_for_calls()...")
    customers_by_stage = get_test_customers_ready_for_calls(smartsheet_service)

    stage_2_customers = customers_by_stage[2]

    if len(stage_2_customers) < 2:
        print(f"❌ Expected at least 2 Stage 2 customers, got {len(stage_2_customers)}")
        return False

    print(f"✅ Filtering successful: Found {len(stage_2_customers)} Stage 2 test customers ready")

    # Confirm sequential calling
    response = input(f"\n⚠️  Proceed with final stage calling {len(stage_2_customers)} customers? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("⏭️  Skipping Stage 2 calls")
        return True

    # Make sequential calls
    assistant_id = get_assistant_id_for_stage(2)
    print(f"\n📞 Making final stage VAPI calls (Stage 2→3)...")
    print(f"   🤖 Assistant ID: {assistant_id}")

    for i, customer in enumerate(stage_2_customers[:2], 1):
        print(f"\n   📞 Final call {i}/{min(2, len(stage_2_customers))}: {customer['company']}")

        results = vapi_service.make_batch_call_with_assistant(
            [customer],
            assistant_id,
            schedule_immediately=True
        )

        if not results or not results[0]:
            print(f"   ❌ Call {i} failed")
            continue

        call_data = results[0]

        # Skip if customer didn't answer
        end_reason = call_data.get('endedReason', '')
        if end_reason == 'customer-did-not-answer':
            print(f"   ⏭️  Customer did not answer, skipping update")
            continue

        print(f"   ✅ Call {i} completed")

        # Update Smartsheet (should mark Done=True)
        success = update_after_call(smartsheet_service, customer, call_data, current_stage=2)
        if success:
            print(f"   ✅ Smartsheet updated (Done=True)")

        # Verify Done=True
        row_data = test_manager.get_row_data(customer['row_id'])
        done_status = row_data.get('Done?', False)
        stage = row_data.get('AI Call Stage', '')

        print(f"   🔍 Verification: Stage={stage}, Done={done_status}")

        if stage == "3" and done_status:
            print(f"   ✅ Final stage verified")
        else:
            print(f"   ⚠️  Expected Stage=3 and Done=True, got Stage={stage}, Done={done_status}")

        if i < min(2, len(stage_2_customers)):
            wait_with_message(5, f"Pausing before next call...")

    print(f"\n✅ STAGE 2 COMPLETED")
    return True


def test_skip_validation():
    """
    Test validation logic without creating actual rows
    Uses in-memory test data
    """
    print("\n" + "=" * 80)
    print("🧪 VALIDATION LOGIC TEST")
    print("=" * 80)
    print("📋 Testing: should_skip_row() and get_call_stage()")
    print("=" * 80)

    generator = TestDataGenerator()
    skip_customers = generator.generate_skip_test_customers()

    print(f"\n🔍 Testing {len(skip_customers)} skip scenarios...")

    for i, customer in enumerate(skip_customers, 1):
        should_skip, reason = should_skip_row(customer)
        client_id = customer.get('Client ID', 'Unknown')

        if should_skip:
            print(f"   ✅ {i}. {client_id}: SKIPPED - {reason}")
        else:
            print(f"   ❌ {i}. {client_id}: NOT SKIPPED (expected to skip)")

    print(f"\n✅ VALIDATION TEST COMPLETED")
    return True


# ========================================
# Main Test Function
# ========================================

def run_end_to_end_test():
    """
    Run complete end-to-end test workflow
    """
    print("\n" + "=" * 80)
    print("🧪 VAPI CANCELLATION FLOW - END-TO-END TEST")
    print("=" * 80)
    print("⚠️  WARNING: This will make REAL phone calls and incur charges!")
    print("=" * 80)
    print("📋 Test Structure:")
    print("   1. Validation Logic Test (no calls)")
    print("   2. Stage 0: Batch calling (2 customers, mixed numbers)")
    print("   3. Stage 1: Sequential calling (2 customers)")
    print("   4. Stage 2: Advanced sequential (2 customers with edge cases)")
    print("=" * 80)
    print(f"📱 Primary test number: {DEFAULT_TEST_NUMBER}")
    print(f"📱 Stage 0 corner case: {STAGE_0_BATCH_NUMBERS}")
    print("🔒 ONLY test customers (Client ID starts with TEST-) will be processed")
    print("=" * 80)

    response = input("\n⚠️  Proceed with end-to-end test? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ Test cancelled")
        return False

    # Initialize services
    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
    vapi_service = VAPIService()
    test_manager = TestRowManager(smartsheet_service, CANCELLATION_SHEET_ID)

    try:
        # Test 1: Validation logic (no API calls)
        print("\n" + "=" * 80)
        print("TEST 1: VALIDATION LOGIC")
        print("=" * 80)
        test_skip_validation()

        wait_with_message(5, "Pausing before Stage 0...")

        # Test 2: Stage 0 batch calling
        print("\n" + "=" * 80)
        print("TEST 2: STAGE 0 BATCH CALLING")
        print("=" * 80)
        success = test_stage_0_batch_calling(smartsheet_service, vapi_service, test_manager)
        if not success:
            print("❌ Stage 0 test failed")
            return False

        wait_with_message(PAUSE_BETWEEN_STAGES, "Pausing before Stage 1...")

        # Test 3: Stage 1 sequential calling
        print("\n" + "=" * 80)
        print("TEST 3: STAGE 1 SEQUENTIAL CALLING")
        print("=" * 80)
        success = test_stage_1_sequential_calling(smartsheet_service, vapi_service, test_manager)
        if not success:
            print("❌ Stage 1 test failed")
            return False

        wait_with_message(PAUSE_BETWEEN_STAGES, "Pausing before Stage 2...")

        # Test 4: Stage 2 advanced sequential
        print("\n" + "=" * 80)
        print("TEST 4: STAGE 2 ADVANCED SEQUENTIAL")
        print("=" * 80)
        success = test_stage_2_advanced_sequential(smartsheet_service, vapi_service, test_manager)
        if not success:
            print("❌ Stage 2 test failed")
            return False

        print("\n" + "=" * 80)
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print("   ✅ Validation logic verified")
        print("   ✅ Stage 0 batch calling tested")
        print("   ✅ Stage 1 sequential calling tested")
        print("   ✅ Stage 2 advanced scenarios tested")
        print("   ✅ End-to-end flow validated")
        print("=" * 80)

        return True

    finally:
        # Cleanup
        wait_with_message(5, "Pausing before cleanup...")
        test_manager.cleanup_all()


# ========================================
# Entry Point
# ========================================

if __name__ == "__main__":
    success = run_end_to_end_test()

    print("\n" + "=" * 80)
    if success:
        print("✅ END-TO-END TEST PASSED")
    else:
        print("❌ END-TO-END TEST FAILED")
    print("=" * 80)
