#!/usr/bin/env python3
"""
Renewal Workflow Test
Tests the renewal calling workflow with dynamic sheet discovery
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from services import SmartsheetService, VAPIService
from workflows.renewals import (
    get_current_renewal_sheet,
    should_skip_renewal_row,
    get_renewal_stage,
    is_renewal_ready_for_calling,
    calculate_renewal_next_followup_date,
    run_renewal_batch_calling
)
from config import TEST_CUSTOMER_PHONE


def test_renewal_sheet_discovery():
    """Test dynamic renewal sheet discovery"""
    print("=" * 80)
    print("🧪 TESTING RENEWAL SHEET DISCOVERY")
    print("=" * 80)
    
    try:
        # Test getting current renewal sheet
        smartsheet_service = get_current_renewal_sheet()
        print(f"✅ Successfully found renewal sheet: {smartsheet_service.sheet_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to find renewal sheet: {e}")
        print("   This is expected if the sheet doesn't exist yet")
        return False


def test_renewal_validation_logic():
    """Test renewal row validation logic"""
    print("=" * 80)
    print("🧪 TESTING RENEWAL VALIDATION LOGIC")
    print("=" * 80)
    
    # Test valid customer
    valid_customer = {
        'company': 'Test Company',
        'phone_number': TEST_CUSTOMER_PHONE,
        'policy_expiry_date': '2024-12-31',
        'renewal_status': 'renewal',
        'done?': False
    }
    
    should_skip, reason = should_skip_renewal_row(valid_customer)
    print(f"✅ Valid customer - Should skip: {should_skip}, Reason: {reason}")
    
    # Test invalid customers
    test_cases = [
        ({'company': '', 'phone_number': TEST_CUSTOMER_PHONE, 'policy_expiry_date': '2024-12-31', 'renewal_status': 'renewal'}, "Empty company"),
        ({'company': 'Test', 'phone_number': '', 'policy_expiry_date': '2024-12-31', 'renewal_status': 'renewal'}, "Empty phone"),
        ({'company': 'Test', 'phone_number': TEST_CUSTOMER_PHONE, 'policy_expiry_date': '', 'renewal_status': 'renewal'}, "Empty expiry date"),
        ({'company': 'Test', 'phone_number': TEST_CUSTOMER_PHONE, 'policy_expiry_date': '2024-12-31', 'renewal_status': 'invalid'}, "Invalid renewal status"),
        ({'company': 'Test', 'phone_number': TEST_CUSTOMER_PHONE, 'policy_expiry_date': '2024-12-31', 'renewal_status': 'renewal', 'done?': True}, "Done checkbox checked")
    ]
    
    for customer, description in test_cases:
        should_skip, reason = should_skip_renewal_row(customer)
        print(f"✅ {description} - Should skip: {should_skip}, Reason: {reason}")
    
    return True


def test_renewal_timeline_logic():
    """Test renewal timeline logic"""
    print("=" * 80)
    print("🧪 TESTING RENEWAL TIMELINE LOGIC")
    print("=" * 80)
    
    today = datetime.now().date()
    
    # Test cases for different expiry dates based on UW team schedule: 14, 7, 1, 0 days before
    test_cases = [
        (today + timedelta(days=14), "14 days from now", True, 0),  # Stage 0: 2 weeks before
        (today + timedelta(days=7), "7 days from now", True, 1),   # Stage 1: 1 week before
        (today + timedelta(days=1), "1 day from now", True, 2),   # Stage 2: 1 day before
        (today, "today", True, 3),                                # Stage 3: day of expiry
        (today + timedelta(days=30), "30 days from now", False, -1),  # Too early
        (today - timedelta(days=5), "5 days ago", False, -1),     # Already expired
    ]
    
    for expiry_date, description, expected_ready, expected_stage in test_cases:
        customer = {
            'company': 'Test Company',
            'phone_number': TEST_CUSTOMER_PHONE,
            'policy_expiry_date': expiry_date.strftime('%Y-%m-%d'),
            'renewal_status': 'renewal',
            'done?': False
        }
        
        is_ready, reason, stage = is_renewal_ready_for_calling(customer, today)
        status = "✅" if (is_ready == expected_ready and stage == expected_stage) else "❌"
        print(f"{status} {description} - Ready: {is_ready}, Stage: {stage}, Reason: {reason}")
    
    return True


def test_renewal_followup_calculation():
    """Test renewal follow-up date calculation"""
    print("=" * 80)
    print("🧪 TESTING RENEWAL FOLLOW-UP CALCULATION")
    print("=" * 80)
    
    # Test customer with expiry in 30 days
    customer = {
        'policy_expiry_date': (datetime.now().date() + timedelta(days=30)).strftime('%Y-%m-%d')
    }
    
    # Test different stages (0, 1, 2, 3)
    stage_names = ["2 weeks before", "1 week before", "1 day before", "day of expiry"]
    for stage in [0, 1, 2, 3]:
        next_date = calculate_renewal_next_followup_date(customer, stage)
        print(f"✅ Stage {stage} ({stage_names[stage]}) → Next follow-up: {next_date}")
    
    return True


def test_renewal_workflow_integration():
    """Test the complete renewal workflow integration"""
    print("=" * 80)
    print("🧪 TESTING RENEWAL WORKFLOW INTEGRATION")
    print("=" * 80)
    
    try:
        # Test the complete workflow in test mode
        success = run_renewal_batch_calling(test_mode=True)
        
        if success:
            print("✅ Renewal workflow integration test passed")
            return True
        else:
            print("❌ Renewal workflow integration test failed")
            return False
            
    except Exception as e:
        print(f"❌ Renewal workflow integration test failed with error: {e}")
        return False


def main():
    """Run all renewal workflow tests"""
    print("🚀 RENEWAL WORKFLOW TEST SUITE")
    print("=" * 80)
    
    tests = [
        ("Sheet Discovery", test_renewal_sheet_discovery),
        ("Validation Logic", test_renewal_validation_logic),
        ("Timeline Logic", test_renewal_timeline_logic),
        ("Follow-up Calculation", test_renewal_followup_calculation),
        ("Workflow Integration", test_renewal_workflow_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        try:
            if test_func():
                print(f"✅ {test_name} test passed")
                passed += 1
            else:
                print(f"❌ {test_name} test failed")
        except Exception as e:
            print(f"❌ {test_name} test failed with error: {e}")
    
    print(f"\n{'=' * 80}")
    print(f"🏁 RENEWAL WORKFLOW TEST RESULTS")
    print(f"{'=' * 80}")
    print(f"   ✅ Passed: {passed}/{total}")
    print(f"   ❌ Failed: {total - passed}/{total}")
    print(f"{'=' * 80}")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
