"""
Verify that script can find customers - write to file to avoid encoding issues
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from workflows.stm1 import get_stm1_sheet
from scripts.auto_stm1_calling import get_customers_with_empty_called_times

# Write to file instead of stdout
output_file = project_root / "customer_check_result.txt"

try:
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("CUSTOMER CHECK RESULT\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("Loading service...\n")
        service = get_stm1_sheet()
        
        f.write("Finding customers with empty called_times...\n")
        customers = get_customers_with_empty_called_times(service)
        
        f.write(f"\nRESULT: Found {len(customers)} customers\n\n")
        
        if customers:
            f.write(f"First 20 customers:\n")
            for i, c in enumerate(customers[:20], 1):
                row = c.get('row_number', 'N/A')
                name = c.get('insured_name_', '') or c.get('insured_name', '') or c.get('company', '')
                phone = c.get('phone_number', '') or c.get('contact_phone', '')
                called_times = c.get('called_times', '') or c.get('called_time', '') or '0'
                f.write(f"  {i}. Row {row}: {name[:40]} | Phone: {phone} | Called_times: {called_times}\n")
            
            f.write(f"\nLast 5 customers:\n")
            for i, c in enumerate(customers[-5:], len(customers)-4):
                row = c.get('row_number', 'N/A')
                name = c.get('insured_name_', '') or c.get('insured_name', '') or c.get('company', '')
                phone = c.get('phone_number', '') or c.get('contact_phone', '')
                f.write(f"  {i}. Row {row}: {name[:40]} | Phone: {phone}\n")
        else:
            f.write("\n[WARNING] No customers found!\n")
            f.write("This might be why the script stopped.\n")
    
    print(f"Result written to: {output_file}")
    print(f"Found {len(customers)} customers")
    
except Exception as e:
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"ERROR: {e}\n")
        import traceback
        f.write(traceback.format_exc())
    print(f"Error written to: {output_file}")

