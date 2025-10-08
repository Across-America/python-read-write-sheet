#!/usr/bin/env python3
"""
Test Multi-Stage Batch Calling System
Quick test to show customers ready for each stage
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from services.smartsheet_service import SmartsheetService
from config import CANCELLATION_SHEET_ID
from workflows.batch_calling_v2 import (
    get_customers_ready_for_calls,
    should_skip_row,
    get_call_stage,
    parse_date,
    count_business_days
)


def test_multi_stage_system():
    """Test the multi-stage calling system"""
    print("=" * 80)
    print("🧪 TESTING MULTI-STAGE BATCH CALLING SYSTEM")
    print("=" * 80)
    print()
    
    # Initialize service
    service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
    
    # Test 1: Get all customers with stages
    print("📋 Test 1: Loading all customers with stage information...")
    print("-" * 80)
    
    all_customers = service.get_all_customers_with_stages()
    print(f"\n✅ Loaded {len(all_customers)} total customers")
    
    if not all_customers:
        print("❌ No customers found")
        return
    
    # Show sample customer data
    print(f"\n📝 Sample customer data (first row):")
    sample = all_customers[0]
    for key, value in sample.items():
        if value:  # Only show non-empty fields
            print(f"   {key}: {value}")
    
    # Test 2: Validate and filter
    print(f"\n{'=' * 80}")
    print("📋 Test 2: Validating customers...")
    print("-" * 80)
    
    valid_count = 0
    skipped_count = 0
    stage_counts = {0: 0, 1: 0, 2: 0, 3: 0}
    
    for customer in all_customers:
        should_skip, reason = should_skip_row(customer)
        
        if should_skip:
            skipped_count += 1
            if skipped_count <= 3:  # Show first 3 skipped reasons
                print(f"   ⏭️  Row {customer.get('row_number')}: {reason}")
        else:
            valid_count += 1
            stage = get_call_stage(customer)
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
    
    print(f"\n📊 Validation Summary:")
    print(f"   ✅ Valid: {valid_count}")
    print(f"   ⏭️  Skipped: {skipped_count}")
    print(f"\n   Stage Distribution:")
    print(f"      Stage 0 (Not yet called): {stage_counts.get(0, 0)}")
    print(f"      Stage 1 (After 1st call): {stage_counts.get(1, 0)}")
    print(f"      Stage 2 (After 2nd call): {stage_counts.get(2, 0)}")
    print(f"      Stage 3+ (Complete): {stage_counts.get(3, 0)}")
    
    # Test 3: Get customers ready for today
    print(f"\n{'=' * 80}")
    print("📋 Test 3: Getting customers ready for calls TODAY...")
    print("-" * 80)
    
    today = datetime.now().date()
    print(f"📅 Today: {today} ({today.strftime('%A')})")
    print()
    
    customers_by_stage = get_customers_ready_for_calls(service)
    
    # Show details for each stage
    for stage in [0, 1, 2]:
        customers = customers_by_stage[stage]
        
        if customers:
            stage_name = ["1st", "2nd", "3rd"][stage]
            print(f"\n🔔 Stage {stage} ({stage_name} Call) - {len(customers)} customers ready:")
            print("-" * 60)
            
            for i, customer in enumerate(customers[:5], 1):  # Show first 5
                print(f"   {i}. {customer.get('company', 'N/A')}")
                print(f"      📞 Phone: {customer.get('phone_number', 'N/A')}")
                print(f"      💰 Amount Due: ${customer.get('amount_due', 'N/A')}")
                print(f"      📅 Cancellation: {customer.get('cancellation_date', 'N/A')}")
                print(f"      📍 Follow-up Date: {customer.get('followup_date', 'N/A')}")
                print()
            
            if len(customers) > 5:
                print(f"   ... and {len(customers) - 5} more")
    
    # Test 4: Business day calculation
    print(f"\n{'=' * 80}")
    print("📋 Test 4: Testing business day calculations...")
    print("-" * 80)
    
    test_start = parse_date("2025-10-06")  # Monday
    test_end = parse_date("2025-10-17")    # Friday
    
    if test_start and test_end:
        business_days = count_business_days(test_start, test_end)
        print(f"   From {test_start} to {test_end}")
        print(f"   Business days: {business_days}")
        print(f"   Calendar days: {(test_end - test_start).days}")
    
    print(f"\n{'=' * 80}")
    print("✅ All tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        test_multi_stage_system()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
