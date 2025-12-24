"""
Analyze why GitHub Actions workflow completes but makes no calls
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Fix Windows encoding issue
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from workflows.stm1 import get_stm1_sheet, validate_stm1_customer_data
from scripts.auto_stm1_calling import get_customers_with_empty_called_times
from datetime import datetime
from zoneinfo import ZoneInfo

def analyze():
    """Analyze why no calls are made"""
    print("=" * 80)
    print("🔍 ANALYZING WHY NO CALLS ARE MADE")
    print("=" * 80)
    print()
    
    # Test 1: Check if function works
    print("1️⃣ TESTING get_customers_with_empty_called_times()")
    print("-" * 80)
    try:
        smartsheet_service = get_stm1_sheet()
        customers = get_customers_with_empty_called_times(smartsheet_service)
        print(f"✅ Found {len(customers)} customers")
        
        if len(customers) == 0:
            print("❌ PROBLEM: Function returns 0 customers!")
            print("   This would cause script to exit after 3 attempts")
            return
        
        # Check first few customers
        print(f"\n   First 5 customers:")
        for i, customer in enumerate(customers[:5], 1):
            company = customer.get('insured_name_', '') or customer.get('insured_name', '') or customer.get('company', 'Unknown')
            phone = customer.get('phone_number', '') or customer.get('contact_phone', '')
            called_times = customer.get('called_times', '') or customer.get('called_time', '') or customer.get('called time', '')
            done = customer.get('done?', False)
            recorded = customer.get('recorded_or_not', '') or customer.get('recorded or not', '')
            
            print(f"   {i}. {company[:40]}")
            print(f"      Phone: {phone}")
            print(f"      called_times: '{called_times}'")
            print(f"      done?: {done}")
            print(f"      recorded_or_not: {recorded}")
            
            # Validate
            is_valid, error_msg, _ = validate_stm1_customer_data(customer)
            print(f"      Valid: {is_valid}")
            if not is_valid:
                print(f"      ❌ Validation error: {error_msg}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    
    # Test 2: Check time conditions
    print("2️⃣ CHECKING TIME CONDITIONS")
    print("-" * 80)
    pacific_tz = ZoneInfo("America/Los_Angeles")
    now_pacific = datetime.now(pacific_tz)
    current_hour = now_pacific.hour
    current_minute = now_pacific.minute
    
    print(f"   Current time: {now_pacific.strftime('%I:%M %p %Z')}")
    print(f"   Current hour: {current_hour}")
    print(f"   Calling hours: 9 AM - 4:55 PM")
    
    if current_hour < 9:
        print(f"   ⚠️  Before 9 AM - script would wait")
    elif current_hour >= 17 or (current_hour == 16 and current_minute >= 55):
        print(f"   ⚠️  After 4:55 PM - script would stop")
    else:
        print(f"   ✅ Within calling hours")
    
    print()
    
    # Test 3: Simulate script logic
    print("3️⃣ SIMULATING SCRIPT LOGIC")
    print("-" * 80)
    print("   Simulating what happens in the script...")
    
    if len(customers) == 0:
        print("   ❌ No customers found")
        print("   → Script would wait 5 minutes")
        print("   → After 3 attempts, script would exit")
        print("   → This explains why workflow completes with no calls!")
    else:
        print(f"   ✅ Found {len(customers)} customers")
        print("   → Script should start calling")
        print("   → If no calls, possible reasons:")
        print("      1. Script crashes before first call")
        print("      2. Validation fails for all customers")
        print("      3. VAPI API call fails silently")
        print("      4. Script exits early for unknown reason")
    
    print()
    
    # Test 4: Check validation
    print("4️⃣ CHECKING VALIDATION")
    print("-" * 80)
    valid_count = 0
    invalid_count = 0
    
    for customer in customers[:20]:  # Check first 20
        is_valid, error_msg, _ = validate_stm1_customer_data(customer)
        if is_valid:
            valid_count += 1
        else:
            invalid_count += 1
            if invalid_count <= 3:
                company = customer.get('insured_name_', '') or customer.get('insured_name', '') or customer.get('company', 'Unknown')
                print(f"   ❌ Invalid: {company[:40]} - {error_msg}")
    
    print(f"   Valid: {valid_count}/{20}")
    print(f"   Invalid: {invalid_count}/{20}")
    
    if valid_count == 0:
        print("   ❌ PROBLEM: No valid customers!")
        print("   → Script would skip all customers")
        print("   → No calls would be made")
    
    print()
    print("=" * 80)
    print("💡 RECOMMENDATION")
    print("=" * 80)
    print()
    print("Check GitHub Actions logs to see:")
    print("  1. How many customers were found")
    print("  2. If validation failed")
    print("  3. If any errors occurred")
    print()
    print("Logs: https://github.com/Across-America/python-read-write-sheet/actions/runs/20495021313")

if __name__ == "__main__":
    analyze()

