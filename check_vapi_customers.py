"""Check actual customers sent to VAPI"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from workflows.stm1 import get_stm1_sheet, get_stm1_customers_ready_for_calls
from utils import format_phone_number
from config import STM1_MAX_DAILY_CALLS

service = get_stm1_sheet()
customers = get_stm1_customers_ready_for_calls(service)

# Apply daily limit
if STM1_MAX_DAILY_CALLS and len(customers) > STM1_MAX_DAILY_CALLS:
    customers = customers[:STM1_MAX_DAILY_CALLS]

print(f"Total customers after filtering: {len(customers)}")
print()

# Simulate VAPIService.make_batch_call_with_assistant
vapi_customers = []
for i, customer in enumerate(customers):
    phone = customer.get('phone_number') or customer.get('contact_phone') or customer.get('client_phone_number', '')
    if not phone:
        continue
    
    # Skip phone numbers starting with 52 (Mexico country code)
    phone_cleaned = str(phone).strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace(".", "").replace("/", "")
    if phone_cleaned.startswith('52') or phone_cleaned.startswith('+52'):
        print(f"⚠️  Skipping index {i}: {customer.get('insured_name_', 'Unknown')} - {phone} (starts with 52)")
        continue
    
    formatted_phone = format_phone_number(phone)
    vapi_customers.append({
        "number": formatted_phone,
        "name": customer.get('company', customer.get('insured_name', 'Unknown'))
    })
    
    # Check indices 52 and 94
    if len(vapi_customers) - 1 == 52:
        print(f"\n🔍 VAPI customers[52]:")
        print(f"  Original index: {i}")
        print(f"  Company: {customer.get('insured_name_', 'N/A')}")
        print(f"  Original phone: {phone}")
        print(f"  Formatted phone: {formatted_phone}")
        print(f"  Phone cleaned: {phone_cleaned}")
        print(f"  Row number: {customer.get('row_number', 'N/A')}")
    
    if len(vapi_customers) - 1 == 94:
        print(f"\n🔍 VAPI customers[94]:")
        print(f"  Original index: {i}")
        print(f"  Company: {customer.get('insured_name_', 'N/A')}")
        print(f"  Original phone: {phone}")
        print(f"  Formatted phone: {formatted_phone}")
        print(f"  Phone cleaned: {phone_cleaned}")
        print(f"  Row number: {customer.get('row_number', 'N/A')}")

print(f"\nTotal VAPI customers: {len(vapi_customers)}")
print(f"Expected: 100")

