"""Debug script to check phone numbers for rows 52 and 95"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from workflows.stm1 import get_stm1_sheet, get_stm1_customers_ready_for_calls
from utils import format_phone_number

service = get_stm1_sheet()
customers = get_stm1_customers_ready_for_calls(service)

print(f"Total customers: {len(customers)}")
print()

if len(customers) > 51:
    customer_52 = customers[51]
    phone_52 = customer_52.get('phone_number', '') or customer_52.get('contact_phone', '')
    formatted_52 = format_phone_number(phone_52)
    print(f"Row 52 (index 51):")
    print(f"  Company: {customer_52.get('insured_name_', 'N/A')}")
    print(f"  Original phone: {phone_52}")
    print(f"  Formatted phone: {formatted_52}")
    print(f"  Row number: {customer_52.get('row_number', 'N/A')}")
    print()

if len(customers) > 94:
    customer_95 = customers[94]
    phone_95 = customer_95.get('phone_number', '') or customer_95.get('contact_phone', '')
    formatted_95 = format_phone_number(phone_95)
    print(f"Row 95 (index 94):")
    print(f"  Company: {customer_95.get('insured_name_', 'N/A')}")
    print(f"  Original phone: {phone_95}")
    print(f"  Formatted phone: {formatted_95}")
    print(f"  Row number: {customer_95.get('row_number', 'N/A')}")
    print()

# Check all phones for issues
print("Checking all phones for formatting issues...")
issues = []
for i, customer in enumerate(customers[:100]):
    phone = customer.get('phone_number', '') or customer.get('contact_phone', '')
    if phone:
        formatted = format_phone_number(phone)
        # Check if formatted phone is valid E.164
        if not formatted.startswith('+'):
            issues.append((i+1, customer.get('insured_name_', 'Unknown'), phone, formatted))
        elif len(formatted) < 8:  # Too short
            issues.append((i+1, customer.get('insured_name_', 'Unknown'), phone, formatted))

if issues:
    print(f"\nFound {len(issues)} phone number issues:")
    for row, name, orig, fmt in issues[:10]:  # Show first 10
        print(f"  Row {row}: {name} - Original: {orig}, Formatted: {fmt}")
else:
    print("No formatting issues found in first 100 customers")

