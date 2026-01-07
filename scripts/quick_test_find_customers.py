"""
Quick test - can we find customers?
"""
import sys
from pathlib import Path

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from workflows.stm1 import get_stm1_sheet
    from scripts.auto_stm1_calling import get_customers_with_empty_called_times
    
    print("Loading service...")
    service = get_stm1_sheet()
    
    print("Finding customers...")
    customers = get_customers_with_empty_called_times(service)
    
    print(f"\nRESULT: Found {len(customers)} customers")
    
    if customers:
        print(f"\nFirst 5:")
        for i, c in enumerate(customers[:5], 1):
            row = c.get('row_number', 'N/A')
            name = c.get('insured_name_', '') or c.get('insured_name', '') or c.get('company', '')
            phone = c.get('phone_number', '') or c.get('contact_phone', '')
            print(f"  {i}. Row {row}: {name[:40]} | {phone}")
    else:
        print("\n[WARNING] No customers found!")
        print("This might be why the script stopped.")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

