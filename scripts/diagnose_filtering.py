"""
Diagnose why script is not finding customers with empty called_times
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

from workflows.stm1 import get_stm1_sheet, should_skip_stm1_row

def diagnose():
    """Diagnose filtering issues"""
    print("=" * 80)
    print("DIAGNOSING FILTERING LOGIC")
    print("=" * 80)
    
    service = get_stm1_sheet()
    all_customers = service.get_all_customers_with_stages()
    
    print(f"\nTotal customers: {len(all_customers)}")
    
    # Check first 50 customers with empty called_times
    empty_called_times = []
    skipped_reasons = {}
    
    for customer in all_customers:
        called_times_str = customer.get('called_times', '') or customer.get('called_time', '') or customer.get('called time', '') or '0'
        try:
            called_times_count = int(str(called_times_str).strip()) if str(called_times_str).strip() else 0
        except:
            called_times_count = 0
        
        if called_times_count == 0:
            # Check if should skip
            should_skip, reason = should_skip_stm1_row(customer)
            
            if should_skip:
                if reason not in skipped_reasons:
                    skipped_reasons[reason] = []
                skipped_reasons[reason].append(customer.get('row_number', 'N/A'))
            else:
                empty_called_times.append(customer)
    
    print(f"\nCustomers with called_times = 0/empty: {len(empty_called_times) + sum(len(v) for v in skipped_reasons.values())}")
    print(f"  - Should call: {len(empty_called_times)}")
    print(f"  - Should skip: {sum(len(v) for v in skipped_reasons.values())}")
    
    print(f"\nSkip reasons:")
    for reason, rows in skipped_reasons.items():
        print(f"  - {reason}: {len(rows)} customers")
        if len(rows) <= 10:
            print(f"    Rows: {rows}")
        else:
            print(f"    First 10 rows: {rows[:10]} ...")
    
    if empty_called_times:
        print(f"\nFirst 20 customers that SHOULD be called:")
        for i, cust in enumerate(empty_called_times[:20], 1):
            row = cust.get('row_number', 'N/A')
            name = cust.get('insured_name_', '') or cust.get('insured_name', '') or cust.get('company', '')
            phone = cust.get('phone_number', '') or cust.get('contact_phone', '')
            done = cust.get('done?', False)
            recorded = cust.get('recorded_or_not', '') or cust.get('recorded or not', '')
            print(f"  {i}. Row {row}: {name[:40]} | Phone: {phone} | Done: {done} | Recorded: {recorded}")
    
    # Now check what the actual function returns
    print("\n" + "=" * 80)
    print("CHECKING ACTUAL FUNCTION")
    print("=" * 80)
    
    from scripts.auto_stm1_calling import get_customers_with_empty_called_times
    try:
        script_customers = get_customers_with_empty_called_times(service)
        print(f"get_customers_with_empty_called_times() returns: {len(script_customers)} customers")
        
        if len(script_customers) != len(empty_called_times):
            print(f"\n[ISSUE] Mismatch!")
            print(f"  Manual check (should_skip_stm1_row): {len(empty_called_times)}")
            print(f"  Script function: {len(script_customers)}")
            
            if len(script_customers) < len(empty_called_times):
                print(f"\n  Script is missing {len(empty_called_times) - len(script_customers)} customers!")
                
                # Find which ones are missing
                script_rows = {c.get('row_number') for c in script_customers}
                manual_rows = {c.get('row_number') for c in empty_called_times}
                missing_rows = manual_rows - script_rows
                
                if missing_rows:
                    print(f"  Missing {len(missing_rows)} rows from script")
                    print(f"  First 20 missing rows: {sorted(list(missing_rows))[:20]}")
        else:
            print(f"[OK] Function returns correct number")
    except Exception as e:
        print(f"Error calling function: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 80)

if __name__ == "__main__":
    diagnose()

