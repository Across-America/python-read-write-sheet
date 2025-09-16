# Test script for phone number search function
import os
from dotenv import load_dotenv
from read_cancellation_dev import search_phone_number

# Load environment variables
load_dotenv()

print("🔍 Testing Phone Number Search Function")
print("="*50)

# Test with some real data from the sheet
# Based on the data we saw earlier, let's try some examples

test_cases = [
    {"client_id": "24765", "description": "SHAO MING record"},
    {"client_id": "13094", "description": "TABEL ANWAR RIB record"},
    {"client_id": "5381", "description": "RICHARD VARGAS record"},
    {"client_id": "99999", "description": "Non-existent record (should fail)"}
]

print("Testing with Client ID only (Policy Number will be empty/any):")
print("-" * 50)

for test in test_cases:
    print(f"\n🧪 Test: {test['description']}")
    print(f"Client ID: {test['client_id']}")
    
    # For testing, we'll search with empty policy number first to see what's available
    # In real usage, you should provide both Client ID and Policy Number
    try:
        # This will likely fail since we need both parameters
        # But it will show us the error handling
        phone = search_phone_number(test['client_id'], "")
        
    except Exception as e:
        print(f"Expected behavior - need both parameters: {e}")

print("\n" + "="*50)
print("💡 HOW TO USE:")
print("="*50)
print("1. Run the main script to see all data:")
print("   py read_cancellation_dev.py")
print()
print("2. Find a Client ID and Policy Number from the data")
print()
print("3. Use the search function:")
print("   from read_cancellation_dev import search_phone_number")
print("   phone = search_phone_number('your_client_id', 'your_policy_number')")
print()
print("4. Or run interactive mode:")
print("   py read_cancellation_dev.py")
print("   (and follow the prompts)")

print("\n📞 Quick Search Test:")
print("Let's try to find a phone number for Client ID '24765'")
print("(You would need to provide the correct Policy Number)")
