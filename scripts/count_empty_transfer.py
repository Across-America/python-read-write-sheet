"""Count rows with empty transfer status in first 100 rows"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from workflows.stm1 import get_stm1_sheet

smartsheet_service = get_stm1_sheet()

# Get first 100 rows
all_customers = smartsheet_service.get_all_customers_with_stages()
first_100 = all_customers[:100]

# Check transfer column (try multiple possible names)
transfer_cols = ['transferred_to_aacs_or_not', 'transfer', 'was_transferred', 'transfer_status']

empty_count = 0
filled_count = 0
for customer in first_100:
    has_transfer_value = False
    for col in transfer_cols:
        value = customer.get(col, '').strip()
        if value and value.lower() not in ['', 'no', 'yes']:
            # Some other value
            has_transfer_value = True
            break
        elif value and value.lower() in ['yes', 'no']:
            has_transfer_value = True
            break
    
    if has_transfer_value:
        filled_count += 1
    else:
        empty_count += 1

print(f"📊 First 100 rows transfer status:")
print(f"   ✅ Has transfer value: {filled_count}")
print(f"   ⚠️  Empty transfer: {empty_count}")
print(f"   📊 Total: {len(first_100)}")

