"""Debug script to check phone numbers that will be sent to VAPI"""
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

print(f"Total customers to process: {len(customers)}")
print()

# Simulate what VAPIService does
vapi_customers = []
for i, customer in enumerate(customers):
    phone = customer.get('phone_number') or customer.get('contact_phone') or customer.get('client_phone_number', '')
    if not phone:
        print(f"⚠️  Index {i}: Skipping - no phone number")
        continue
    
    formatted_phone = format_phone_number(phone)
    vapi_customers.append({
        "number": formatted_phone,
        "name": customer.get('company', customer.get('insured_name', 'Unknown'))
    })
    
    # Check indices 52 and 95
    if len(vapi_customers) - 1 == 52:
        print(f"\n🔍 VAPI customers[52] (actual index in vapi_customers array):")
        print(f"  Original customer index: {i}")
        print(f"  Company: {customer.get('insured_name_', 'N/A')}")
        print(f"  Original phone: {phone}")
        print(f"  Formatted phone: {formatted_phone}")
        print(f"  Row number: {customer.get('row_number', 'N/A')}")
    
    if len(vapi_customers) - 1 == 95:
        print(f"\n🔍 VAPI customers[95] (actual index in vapi_customers array):")
        print(f"  Original customer index: {i}")
        print(f"  Company: {customer.get('insured_name_', 'N/A')}")
        print(f"  Original phone: {phone}")
        print(f"  Formatted phone: {formatted_phone}")
        print(f"  Row number: {customer.get('row_number', 'N/A')}")

print(f"\nTotal VAPI customers (after filtering): {len(vapi_customers)}")

# Check for any invalid phone numbers
print("\nChecking all formatted phones for validity...")
issues = []
for i, vapi_customer in enumerate(vapi_customers):
    phone = vapi_customer["number"]
    # Check E.164 format: must start with + and have at least 8 characters total
    if not phone.startswith('+'):
        issues.append((i, vapi_customer["name"], phone, "Missing + prefix"))
    elif len(phone) < 8:
        issues.append((i, vapi_customer["name"], phone, f"Too short: {len(phone)} chars"))
    # Check if contains only + and digits after +
    elif not all(c.isdigit() for c in phone[1:]):
        issues.append((i, vapi_customer["name"], phone, "Contains non-digit characters"))

if issues:
    print(f"\n❌ Found {len(issues)} phone number issues:")
    for idx, name, phone, reason in issues[:20]:  # Show first 20
        print(f"  VAPI customers[{idx}]: {name} - {phone} - {reason}")
else:
    print("✅ All phone numbers appear to be valid E.164 format")

