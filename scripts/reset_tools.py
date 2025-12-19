"""Reset and reconfigure STM1 assistant tools"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import requests
import json
from config import VAPI_API_KEY, STM1_ASSISTANT_ID

base_url = "https://api.vapi.ai"
headers = {
    "Authorization": f"Bearer {VAPI_API_KEY}",
    "Content-Type": "application/json"
}

print("=" * 80)
print("🔄 RESETTING STM1 ASSISTANT TOOLS")
print("=" * 80)

# Get current config
response = requests.get(
    f"{base_url}/assistant/{STM1_ASSISTANT_ID}",
    headers=headers
)
assistant = response.json()
model = assistant.get('model', {})

# Step 1: Clear all tools
print("\n1️⃣ Clearing all existing tools...")
model['tools'] = []

clear_payload = {"model": model}
clear_response = requests.patch(
    f"{base_url}/assistant/{STM1_ASSISTANT_ID}",
    headers=headers,
    json=clear_payload
)

if clear_response.status_code not in [200, 201]:
    print(f"❌ Failed to clear tools: {clear_response.status_code}")
    print(clear_response.text)
    sys.exit(1)

print("✅ All tools cleared")

# Step 2: Wait a moment
import time
print("\n⏳ Waiting 2 seconds...")
time.sleep(2)

# Step 3: Add tools one by one
print("\n2️⃣ Adding tools one by one...")

# Add transferCall first
print("   Adding transferCall tool...")
model['tools'] = [{"type": "transferCall"}]

add_response = requests.patch(
    f"{base_url}/assistant/{STM1_ASSISTANT_ID}",
    headers=headers,
    json={"model": model}
)

if add_response.status_code not in [200, 201]:
    print(f"❌ Failed to add transferCall: {add_response.status_code}")
    print(add_response.text)
    sys.exit(1)

print("✅ transferCall added")
time.sleep(1)

# Add endCall
print("   Adding endCall tool...")
model['tools'].append({"type": "endCall"})

add_response2 = requests.patch(
    f"{base_url}/assistant/{STM1_ASSISTANT_ID}",
    headers=headers,
    json={"model": model}
)

if add_response2.status_code not in [200, 201]:
    print(f"❌ Failed to add endCall: {add_response2.status_code}")
    print(add_response2.text)
    sys.exit(1)

print("✅ endCall added")

# Verify
print("\n3️⃣ Verifying final configuration...")
verify_response = requests.get(
    f"{base_url}/assistant/{STM1_ASSISTANT_ID}",
    headers=headers
)

if verify_response.status_code == 200:
    final_assistant = verify_response.json()
    final_model = final_assistant.get('model', {})
    final_tools = final_model.get('tools', [])
    
    print(f"✅ Final tools: {len(final_tools)}")
    for i, tool in enumerate(final_tools, 1):
        print(f"   Tool {i}: {tool.get('type', 'unknown')}")
    
    # Check for duplicates
    types = [t.get('type') for t in final_tools]
    if len(types) != len(set(types)):
        print(f"\n⚠️  WARNING: Duplicates detected!")
        from collections import Counter
        counts = Counter(types)
        for tool_type, count in counts.items():
            if count > 1:
                print(f"   ❌ {tool_type}: {count} duplicates")
    else:
        print(f"\n✅ No duplicates - configuration is clean")

print("\n" + "=" * 80)
print("✅ RESET COMPLETE")
print("=" * 80)
print("You can now test the transfer functionality.")
print("Note: You still need to set the transfer phone number ID in VAPI Dashboard")

