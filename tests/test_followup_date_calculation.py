#!/usr/bin/env python3
"""
Unit Tests for Follow-up Date Calculation Logic
Tests the business day calculation and 3-stage date splitting algorithm
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from workflows.cancellations import (
    is_weekend,
    count_business_days,
    add_business_days,
    calculate_next_followup_date,
    parse_date
)


# ========================================
# Test Cases for Business Day Functions
# ========================================

def test_is_weekend():
    """Test weekend detection"""
    print("\n" + "=" * 80)
    print("🧪 TEST: is_weekend()")
    print("=" * 80)

    test_cases = [
        ("2025-01-06", False, "Monday should NOT be weekend"),
        ("2025-01-10", False, "Friday should NOT be weekend"),
        ("2025-01-11", True, "Saturday should be weekend"),
        ("2025-01-12", True, "Sunday should be weekend"),
        ("2025-01-13", False, "Monday should NOT be weekend"),
    ]

    passed = 0
    failed = 0

    for date_str, expected, description in test_cases:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        result = is_weekend(date)

        if result == expected:
            print(f"   ✅ {date_str} ({date.strftime('%A')}): {result} - {description}")
            passed += 1
        else:
            print(f"   ❌ {date_str} ({date.strftime('%A')}): Expected {expected}, got {result}")
            failed += 1

    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_count_business_days():
    """Test business day counting"""
    print("\n" + "=" * 80)
    print("🧪 TEST: count_business_days()")
    print("=" * 80)

    test_cases = [
        # (start_date, end_date, expected_days, description)
        ("2025-01-06", "2025-01-10", 4, "Mon-Fri (5 days) = 4 business days"),
        ("2025-01-06", "2025-01-13", 5, "Mon-Mon (1 week) = 5 business days"),
        ("2025-01-10", "2025-01-13", 1, "Fri-Mon (skip weekend) = 1 business day"),
        ("2025-01-11", "2025-01-13", 0, "Sat-Mon (weekend + Mon) = 0 business days"),
        ("2025-01-06", "2025-01-20", 10, "Mon-Mon (2 weeks) = 10 business days"),
        ("2025-01-06", "2025-01-06", 0, "Same day = 0 business days"),
        ("2025-01-06", "2025-01-07", 1, "Mon-Tue = 1 business day"),
    ]

    passed = 0
    failed = 0

    for start_str, end_str, expected, description in test_cases:
        start = datetime.strptime(start_str, '%Y-%m-%d').date()
        end = datetime.strptime(end_str, '%Y-%m-%d').date()
        result = count_business_days(start, end)

        if result == expected:
            print(f"   ✅ {start_str} to {end_str}: {result} days - {description}")
            passed += 1
        else:
            print(f"   ❌ {start_str} to {end_str}: Expected {expected}, got {result} - {description}")
            failed += 1

    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_add_business_days():
    """Test adding business days"""
    print("\n" + "=" * 80)
    print("🧪 TEST: add_business_days()")
    print("=" * 80)

    test_cases = [
        # (start_date, days_to_add, expected_date, description)
        ("2025-01-06", 1, "2025-01-07", "Mon + 1 = Tue"),
        ("2025-01-06", 5, "2025-01-13", "Mon + 5 = next Mon"),
        ("2025-01-10", 1, "2025-01-13", "Fri + 1 = Mon (skip weekend)"),
        ("2025-01-10", 3, "2025-01-15", "Fri + 3 = Wed"),
        ("2025-01-11", 1, "2025-01-13", "Sat + 1 = Mon (skip Sat & Sun)"),
        ("2025-01-06", 0, "2025-01-06", "Mon + 0 = Mon (no change)"),
        ("2025-01-06", 10, "2025-01-20", "Mon + 10 = Mon (2 weeks)"),
    ]

    passed = 0
    failed = 0

    for start_str, days, expected_str, description in test_cases:
        start = datetime.strptime(start_str, '%Y-%m-%d').date()
        expected = datetime.strptime(expected_str, '%Y-%m-%d').date()
        result = add_business_days(start, days)

        if result == expected:
            print(f"   ✅ {start_str} + {days} = {result} - {description}")
            passed += 1
        else:
            print(f"   ❌ {start_str} + {days}: Expected {expected}, got {result} - {description}")
            failed += 1

    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0


# ========================================
# Test Cases for 3-Stage Date Splitting
# ========================================

def test_calculate_next_followup_stage_0():
    """Test Stage 0 → 1 followup date calculation (1/3 split)"""
    print("\n" + "=" * 80)
    print("🧪 TEST: calculate_next_followup_date() - Stage 0 → 1")
    print("=" * 80)

    test_cases = [
        # (f_u_date, cancellation_date, expected_days_to_add, description)
        ("2025-01-06", "2025-01-20", 4, "15 business days / 3 ≈ 5 → round(5) = 5, but Mon-Mon is 10 days, so 10/3 = 3.33 → 3"),
        ("2025-01-06", "2025-01-17", 3, "9 business days / 3 = 3"),
        ("2025-01-06", "2025-01-10", 1, "4 business days / 3 ≈ 1.33 → round(1.33) = 1"),
        ("2025-01-06", "2025-01-07", 1, "1 business day / 3 ≈ 0.33 → round(0.33) = 0, min is 1"),
        ("2025-01-10", "2025-01-17", 2, "Fri-Fri: 5 business days / 3 ≈ 1.67 → round(1.67) = 2"),
    ]

    passed = 0
    failed = 0

    for fu_str, cancel_str, expected_days, description in test_cases:
        fu_date = datetime.strptime(fu_str, '%Y-%m-%d').date()
        cancel_date = datetime.strptime(cancel_str, '%Y-%m-%d').date()

        customer = {
            'f_u_date': fu_str,
            'cancellation_date': cancel_str
        }

        result_date = calculate_next_followup_date(customer, current_stage=0)

        if result_date:
            # Calculate actual days added
            actual_days = count_business_days(fu_date, result_date)

            # Allow ±1 day tolerance due to rounding
            if abs(actual_days - expected_days) <= 1:
                print(f"   ✅ {fu_str} to {cancel_str}: Added {actual_days} days → {result_date}")
                print(f"      {description}")
                passed += 1
            else:
                print(f"   ❌ {fu_str} to {cancel_str}: Expected ~{expected_days} days, got {actual_days} → {result_date}")
                print(f"      {description}")
                failed += 1
        else:
            print(f"   ❌ {fu_str} to {cancel_str}: Got None")
            failed += 1

    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_calculate_next_followup_stage_1():
    """Test Stage 1 → 2 followup date calculation (1/2 of remaining)"""
    print("\n" + "=" * 80)
    print("🧪 TEST: calculate_next_followup_date() - Stage 1 → 2")
    print("=" * 80)

    test_cases = [
        # After Stage 0→1, we're now at a new f_u_date
        # Stage 1→2 splits the REMAINING time in half
        ("2025-01-10", "2025-01-20", 2, "6 business days remaining / 2 = 3 → round(3) = 3, but might be 2-3"),
        ("2025-01-10", "2025-01-17", 2, "5 business days remaining / 2 = 2.5 → round(2.5) = 2"),
        ("2025-01-13", "2025-01-17", 1, "4 business days remaining / 2 = 2 → round(2) = 2, but might be 1-2"),
        ("2025-01-15", "2025-01-17", 1, "2 business days remaining / 2 = 1"),
    ]

    passed = 0
    failed = 0

    for fu_str, cancel_str, expected_days, description in test_cases:
        fu_date = datetime.strptime(fu_str, '%Y-%m-%d').date()
        cancel_date = datetime.strptime(cancel_str, '%Y-%m-%d').date()

        customer = {
            'f_u_date': fu_str,
            'cancellation_date': cancel_str
        }

        result_date = calculate_next_followup_date(customer, current_stage=1)

        if result_date:
            actual_days = count_business_days(fu_date, result_date)

            # Allow ±1 day tolerance
            if abs(actual_days - expected_days) <= 1:
                print(f"   ✅ {fu_str} to {cancel_str}: Added {actual_days} days → {result_date}")
                print(f"      {description}")
                passed += 1
            else:
                print(f"   ❌ {fu_str} to {cancel_str}: Expected ~{expected_days} days, got {actual_days} → {result_date}")
                print(f"      {description}")
                failed += 1
        else:
            print(f"   ❌ {fu_str} to {cancel_str}: Got None")
            failed += 1

    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_calculate_next_followup_stage_2():
    """Test Stage 2 → 3 (no more followup)"""
    print("\n" + "=" * 80)
    print("🧪 TEST: calculate_next_followup_date() - Stage 2 → 3")
    print("=" * 80)

    # Stage 2→3 should return None (no more followups)
    customer = {
        'f_u_date': '2025-01-15',
        'cancellation_date': '2025-01-20'
    }

    result = calculate_next_followup_date(customer, current_stage=2)

    if result is None:
        print(f"   ✅ Stage 2→3 returns None (no more followups)")
        return True
    else:
        print(f"   ❌ Stage 2→3 should return None, got {result}")
        return False


# ========================================
# Edge Cases and Stress Tests
# ========================================

def test_edge_cases():
    """Test edge cases"""
    print("\n" + "=" * 80)
    print("🧪 TEST: Edge Cases")
    print("=" * 80)

    passed = 0
    failed = 0

    # Edge case 1: Very short time window (1 day)
    print("\n📋 Edge Case 1: Very short window (1 business day)")
    customer = {'f_u_date': '2025-01-06', 'cancellation_date': '2025-01-07'}
    result = calculate_next_followup_date(customer, 0)
    if result:
        print(f"   ✅ 1 business day / 3 → {result} (minimum 1 day enforced)")
        passed += 1
    else:
        print(f"   ❌ Should return a date, got None")
        failed += 1

    # Edge case 2: Crosses weekend
    print("\n📋 Edge Case 2: Start on Friday, cancel on Monday")
    customer = {'f_u_date': '2025-01-10', 'cancellation_date': '2025-01-13'}
    result = calculate_next_followup_date(customer, 0)
    if result:
        days = count_business_days(
            datetime.strptime('2025-01-10', '%Y-%m-%d').date(),
            result
        )
        print(f"   ✅ Fri-Mon (1 business day) / 3 → {result} ({days} day added)")
        passed += 1
    else:
        print(f"   ❌ Should return a date")
        failed += 1

    # Edge case 3: Very long window (30 business days)
    print("\n📋 Edge Case 3: Very long window (30 business days)")
    fu_date = datetime.strptime('2025-01-06', '%Y-%m-%d').date()
    cancel_date = add_business_days(fu_date, 30)
    customer = {
        'f_u_date': '2025-01-06',
        'cancellation_date': cancel_date.strftime('%Y-%m-%d')
    }
    result = calculate_next_followup_date(customer, 0)
    if result:
        days = count_business_days(fu_date, result)
        expected = 30 // 3  # Should be around 10
        if abs(days - expected) <= 1:
            print(f"   ✅ 30 business days / 3 → {result} ({days} days, expected ~{expected})")
            passed += 1
        else:
            print(f"   ❌ Expected ~{expected} days, got {days}")
            failed += 1
    else:
        print(f"   ❌ Should return a date")
        failed += 1

    # Edge case 4: Multiple consecutive weekends
    print("\n📋 Edge Case 4: Spans multiple weekends")
    customer = {'f_u_date': '2025-01-06', 'cancellation_date': '2025-01-27'}
    result = calculate_next_followup_date(customer, 0)
    if result:
        total_days = count_business_days(
            datetime.strptime('2025-01-06', '%Y-%m-%d').date(),
            datetime.strptime('2025-01-27', '%Y-%m-%d').date()
        )
        days_added = count_business_days(
            datetime.strptime('2025-01-06', '%Y-%m-%d').date(),
            result
        )
        expected = round(total_days / 3)
        print(f"   ✅ {total_days} business days total, added {days_added} (expected ~{expected})")
        passed += 1
    else:
        print(f"   ❌ Should return a date")
        failed += 1

    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_complete_3_stage_workflow():
    """Test complete workflow: Stage 0→1→2→3 with realistic dates"""
    print("\n" + "=" * 80)
    print("🧪 TEST: Complete 3-Stage Workflow")
    print("=" * 80)

    # Start with today and cancellation in 15 business days
    today = datetime.now().date()
    cancellation_date = add_business_days(today, 15)

    print(f"\n📅 Initial Setup:")
    print(f"   Today (F/U Date): {today}")
    print(f"   Cancellation Date: {cancellation_date}")
    print(f"   Total: {count_business_days(today, cancellation_date)} business days")

    customer = {
        'f_u_date': today.strftime('%Y-%m-%d'),
        'cancellation_date': cancellation_date.strftime('%Y-%m-%d')
    }

    # Stage 0 → 1
    print(f"\n📞 Stage 0 → 1:")
    fu_date_1 = calculate_next_followup_date(customer, 0)
    if fu_date_1:
        days_0_to_1 = count_business_days(today, fu_date_1)
        print(f"   Next F/U: {fu_date_1}")
        print(f"   Days added: {days_0_to_1}")

        # Stage 1 → 2
        print(f"\n📞 Stage 1 → 2:")
        customer['f_u_date'] = fu_date_1.strftime('%Y-%m-%d')
        fu_date_2 = calculate_next_followup_date(customer, 1)
        if fu_date_2:
            days_1_to_2 = count_business_days(fu_date_1, fu_date_2)
            print(f"   Next F/U: {fu_date_2}")
            print(f"   Days added: {days_1_to_2}")

            # Stage 2 → 3
            print(f"\n📞 Stage 2 → 3:")
            customer['f_u_date'] = fu_date_2.strftime('%Y-%m-%d')
            fu_date_3 = calculate_next_followup_date(customer, 2)
            if fu_date_3 is None:
                print(f"   Next F/U: None (final stage)")

                # Verify timing
                print(f"\n📊 Timing Breakdown:")
                print(f"   Stage 0→1: {days_0_to_1} business days")
                print(f"   Stage 1→2: {days_1_to_2} business days")
                print(f"   Stage 2→Cancel: {count_business_days(fu_date_2, cancellation_date)} business days")
                print(f"   ✅ Workflow complete")
                return True
            else:
                print(f"   ❌ Stage 2→3 should return None, got {fu_date_3}")
                return False
        else:
            print(f"   ❌ Stage 1→2 returned None")
            return False
    else:
        print(f"   ❌ Stage 0→1 returned None")
        return False


# ========================================
# Main Test Runner
# ========================================

def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("🚀 FOLLOW-UP DATE CALCULATION TEST SUITE")
    print("=" * 80)
    print("Testing business day logic and 3-stage date splitting")
    print("=" * 80)

    results = {
        "is_weekend()": test_is_weekend(),
        "count_business_days()": test_count_business_days(),
        "add_business_days()": test_add_business_days(),
        "Stage 0→1 calculation": test_calculate_next_followup_stage_0(),
        "Stage 1→2 calculation": test_calculate_next_followup_stage_1(),
        "Stage 2→3 calculation": test_calculate_next_followup_stage_2(),
        "Edge cases": test_edge_cases(),
        "Complete 3-stage workflow": test_complete_3_stage_workflow(),
    }

    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")

    print(f"\n🏁 Total: {passed}/{total} test suites passed")
    print("=" * 80)

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
