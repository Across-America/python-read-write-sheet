"""
Diagnose why automation fails but manual runs work
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

from workflows.stm1 import get_stm1_sheet
from scripts.auto_stm1_calling import get_customers_with_empty_called_times
from datetime import datetime
from zoneinfo import ZoneInfo
import time

def diagnose_issue():
    """Diagnose automation issues"""
    print("=" * 80)
    print("🔍 DIAGNOSING AUTOMATION ISSUE")
    print("=" * 80)
    print()
    
    # Check 1: Timezone
    print("1️⃣ CHECKING TIMEZONE")
    print("-" * 80)
    pacific_tz = ZoneInfo("America/Los_Angeles")
    utc_tz = ZoneInfo("UTC")
    now_pacific = datetime.now(pacific_tz)
    now_utc = datetime.now(utc_tz)
    
    print(f"   Pacific Time: {now_pacific.strftime('%I:%M %p %Z')}")
    print(f"   UTC Time: {now_utc.strftime('%I:%M %p %Z')}")
    print(f"   Current hour (PST): {now_pacific.hour}")
    print(f"   Current hour (UTC): {now_utc.hour}")
    print()
    
    # Check 2: Service initialization
    print("2️⃣ TESTING SERVICE INITIALIZATION")
    print("-" * 80)
    try:
        start_time = time.time()
        print("   Initializing Smartsheet service...")
        smartsheet_service = get_stm1_sheet()
        init_time = time.time() - start_time
        print(f"   ✅ Service initialized in {init_time:.2f} seconds")
    except Exception as e:
        print(f"   ❌ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return
    print()
    
    # Check 3: Loading customers
    print("3️⃣ TESTING CUSTOMER DATA LOADING")
    print("-" * 80)
    try:
        start_time = time.time()
        print("   Loading all customers...")
        all_customers = smartsheet_service.get_all_customers_with_stages()
        load_time = time.time() - start_time
        print(f"   ✅ Loaded {len(all_customers)} customers in {load_time:.2f} seconds")
        print(f"   ⚠️  This is slow! ({load_time:.1f}s for {len(all_customers)} records)")
    except Exception as e:
        print(f"   ❌ Failed to load customers: {e}")
        import traceback
        traceback.print_exc()
        return
    print()
    
    # Check 4: Filtering customers
    print("4️⃣ TESTING CUSTOMER FILTERING")
    print("-" * 80)
    try:
        start_time = time.time()
        print("   Filtering customers with empty called_times...")
        customers_to_call = get_customers_with_empty_called_times(smartsheet_service)
        filter_time = time.time() - start_time
        print(f"   ✅ Found {len(customers_to_call)} customers in {filter_time:.2f} seconds")
        print(f"   ⚠️  Total time: {init_time + load_time + filter_time:.2f} seconds")
    except Exception as e:
        print(f"   ❌ Failed to filter customers: {e}")
        import traceback
        traceback.print_exc()
        return
    print()
    
    # Check 5: Potential issues
    print("5️⃣ POTENTIAL ISSUES")
    print("-" * 80)
    issues = []
    
    if init_time + load_time + filter_time > 60:
        issues.append(f"❌ Data loading is VERY SLOW ({init_time + load_time + filter_time:.1f}s)")
        issues.append("   → GitHub Actions may timeout or appear stuck")
    
    if len(customers_to_call) == 0:
        issues.append("❌ No customers found to call")
        issues.append("   → Script will wait 5 minutes and check again (infinite loop)")
    
    if now_pacific.hour < 9:
        issues.append(f"⚠️  Current time is {now_pacific.hour}:{now_pacific.minute:02d} - before 9 AM")
        issues.append("   → Script will wait until 9 AM (could be hours)")
    
    if not issues:
        print("   ✅ No obvious issues found")
    else:
        for issue in issues:
            print(f"   {issue}")
    print()
    
    # Recommendations
    print("=" * 80)
    print("💡 RECOMMENDATIONS")
    print("=" * 80)
    print()
    print("1. Add more logging to script:")
    print("   - Log after each major step")
    print("   - Log customer count after filtering")
    print("   - Log when starting each call")
    print()
    print("2. Optimize data loading:")
    print("   - Cache customer data")
    print("   - Load in batches")
    print("   - Add timeout for API calls")
    print()
    print("3. Fix infinite wait issue:")
    print("   - If no customers, don't wait 5 minutes")
    print("   - Exit gracefully if no work to do")
    print("   - Add progress indicators")
    print()
    print("4. Add error handling:")
    print("   - Catch and log all exceptions")
    print("   - Exit on critical errors")
    print("   - Don't silently fail")
    print()

if __name__ == "__main__":
    diagnose_issue()

