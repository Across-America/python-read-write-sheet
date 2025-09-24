# Test the auto call and update system
from api.auto_call_and_update import auto_call_and_update

print("🤖 AUTO CALL AND UPDATE TEST")
print("="*50)

# Test with known customer data
client_id = "24765"
policy_number = "BSNDP-2025-012160-01"

print(f"Testing with:")
print(f"Client ID: {client_id}")
print(f"Policy Number: {policy_number}")
print(f"Expected Phone: 3239435582")
print()

print("🚀 Starting auto call process...")
print("This will:")
print("1. Look up phone number from Smartsheet")
print("2. Make VAPI call")
print("3. Monitor call status every 10 seconds")
print("4. Update Call Result when call ends")
print()

# Make the actual call
result = auto_call_and_update(client_id, policy_number)

if result:
    print("✅ Process completed successfully!")
else:
    print("❌ Process failed!")
