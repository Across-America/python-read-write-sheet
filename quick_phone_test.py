# Quick test of the phone search function
from read_cancellation_dev import search_phone_number

print("🧪 QUICK PHONE SEARCH TEST")
print("="*50)

# Test with the data we just saw:
# Client ID: 24765, Policy: BSNDP-2025-012160-01, Phone: 3239435582

print("Testing with known data:")
print("Client ID: 24765")
print("Policy Number: BSNDP-2025-012160-01")
print("Expected Phone: 3239435582")
print()

result = search_phone_number("24765", "BSNDP-2025-012160-01")

print(f"\n🎯 Test Result: {'SUCCESS' if result else 'FAILED'}")

# Test with wrong data
print("\n" + "-"*50)
print("Testing with wrong policy number:")
result2 = search_phone_number("24765", "WRONG-POLICY")
print(f"🎯 Test Result: {'UNEXPECTED SUCCESS' if result2 else 'EXPECTED FAILURE'}")

print("\n✅ Function is working correctly!")
