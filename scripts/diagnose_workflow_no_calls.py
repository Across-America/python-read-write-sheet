"""
Diagnose why workflow runs but doesn't make calls
"""
import sys
import os
from pathlib import Path

# Fix Windows encoding issue
if sys.platform == 'win32':
    import io
    if not isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if not isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from zoneinfo import ZoneInfo
from workflows.stm1 import get_stm1_sheet, get_stm1_customers_ready_for_calls
from scripts.auto_stm1_calling import get_customers_with_empty_called_times
from config import STM1_CALLING_START_HOUR, STM1_CALLING_END_HOUR

def diagnose():
    """Diagnose why workflow doesn't make calls"""
    print("=" * 80)
    print("DIAGNOSING WHY WORKFLOW DOESN'T MAKE CALLS")
    print("=" * 80)
    
    pacific_tz = ZoneInfo("America/Los_Angeles")
    now = datetime.now(pacific_tz)
    today = now.date()
    
    print(f"\nCurrent time: {now.strftime('%I:%M %p %Z')}")
    print(f"Today: {today}")
    print()
    
    # Check 1: Time
    print("1. TIME CHECK")
    print("-" * 80)
    current_hour = now.hour
    if current_hour < STM1_CALLING_START_HOUR:
        print(f"   [ISSUE] Too early - before {STM1_CALLING_START_HOUR}:00 AM")
        print(f"   Script will wait until {STM1_CALLING_START_HOUR}:00 AM")
    elif current_hour >= STM1_CALLING_END_HOUR:
        print(f"   [ISSUE] Too late - after {STM1_CALLING_END_HOUR}:00 PM")
    else:
        print(f"   [OK] Within calling hours")
    
    # Check 2: Customers with empty called_times
    print("\n2. CUSTOMERS WITH EMPTY CALLED_TIMES")
    print("-" * 80)
    try:
        service = get_stm1_sheet()
        customers_empty = get_customers_with_empty_called_times(service)
        print(f"   Found: {len(customers_empty)} customers")
        
        if len(customers_empty) == 0:
            print(f"   [ISSUE] NO CUSTOMERS AVAILABLE!")
            print(f"   This is why workflow exits - all customers have called_times > 0")
            print(f"   Script exits after 3 consecutive empty results (MAX_NO_CUSTOMERS = 3)")
        else:
            print(f"   [OK] Found {len(customers_empty)} customers ready to call")
            print(f"   First row: {customers_empty[0].get('row_number')}")
            print(f"   Last row: {customers_empty[-1].get('row_number')}")
    except Exception as e:
        print(f"   [ERROR] {e}")
    
    # Check 3: Customers ready for daily calls
    print("\n3. CUSTOMERS READY FOR DAILY CALLS")
    print("-" * 80)
    try:
        ready_customers = get_stm1_customers_ready_for_calls(service)
        print(f"   Found: {len(ready_customers)} customers")
        
        if len(ready_customers) == 0:
            print(f"   [ISSUE] NO CUSTOMERS READY!")
            print(f"   Possible reasons:")
            print(f"     - All customers were called today (check call_notes for today's date)")
            print(f"     - All customers have called_times > 0")
            print(f"     - All customers are marked as done or recorded")
        else:
            print(f"   [OK] Found {len(ready_customers)} customers ready")
    except Exception as e:
        print(f"   [ERROR] {e}")
    
    # Check 4: Called today analysis
    print("\n4. CALLED TODAY ANALYSIS")
    print("-" * 80)
    try:
        all_customers = service.get_all_customers_with_stages()
        today_str = today.strftime('%Y-%m-%d')
        called_today_count = 0
        
        for customer in all_customers:
            call_notes = customer.get('call_notes', '') or customer.get('stm1_call_notes', '')
            if call_notes and today_str in call_notes:
                called_today_count += 1
        
        print(f"   Customers with call_notes from today: {called_today_count}")
        
        if called_today_count > 0:
            print(f"   [INFO] {called_today_count} customers were called today")
            print(f"   This may explain why no more calls are being made")
    except Exception as e:
        print(f"   [ERROR] {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("DIAGNOSIS SUMMARY")
    print("=" * 80)
    
    if len(customers_empty) == 0:
        print("\n[ROOT CAUSE] No customers with empty called_times")
        print("  - All customers have been called (called_times > 0)")
        print("  - Script exits after 3 consecutive empty results")
        print("  - Solution: Wait for new customers or reset called_times")
    elif len(ready_customers) == 0:
        print("\n[ROOT CAUSE] No customers ready for daily calls")
        print("  - All customers were called today")
        print("  - Script checks if customer was called today before calling")
        print("  - Solution: Wait until tomorrow or check call_notes dates")
    else:
        print("\n[POSSIBLE CAUSES]")
        print("  - Workflow may have encountered an error (check GitHub Actions logs)")
        print("  - Environment variables may be missing")
        print("  - Script may be waiting for 9 AM")
    
    print("=" * 80)

if __name__ == "__main__":
    diagnose()

