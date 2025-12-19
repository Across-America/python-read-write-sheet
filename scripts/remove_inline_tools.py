"""Remove inline tools, keep only toolIds"""
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
print("🔧 REMOVING INLINE TOOLS (keeping toolIds only)")
print("=" * 80)

# Get current config
response = requests.get(
    f"{base_url}/assistant/{STM1_ASSISTANT_ID}",
    headers=headers
)
assistant = response.json()
model = assistant.get('model', {})

print(f"\n📋 Current configuration:")
print(f"   toolIds: {model.get('toolIds', [])}")
print(f"   tools (inline): {len(model.get('tools', []))} tools")

# Remove inline tools, keep toolIds
model['tools'] = []

update_payload = {"model": model}

print(f"\n🔄 Removing inline tools...")
update_response = requests.patch(
    f"{base_url}/assistant/{STM1_ASSISTANT_ID}",
    headers=headers,
    json=update_payload
)

if update_response.status_code not in [200, 201]:
    print(f"❌ Failed: {update_response.status_code}")
    print(update_response.text)
    sys.exit(1)

print("✅ Inline tools removed")

# Verify
print(f"\n🔍 Verifying...")
verify_response = requests.get(
    f"{base_url}/assistant/{STM1_ASSISTANT_ID}",
    headers=headers
)

if verify_response.status_code == 200:
    final_assistant = verify_response.json()
    final_model = final_assistant.get('model', {})
    final_tool_ids = final_model.get('toolIds', [])
    final_tools = final_model.get('tools', [])
    
    print(f"   ✅ toolIds: {final_tool_ids}")
    print(f"   ✅ tools (inline): {len(final_tools)} tools")
    
    if len(final_tools) == 0:
        print(f"\n✅ Success! Now using only toolIds (Dashboard-configured tools)")
    else:
        print(f"\n⚠️  Warning: Still have {len(final_tools)} inline tools")

print("\n" + "=" * 80)
print("✅ CONFIGURATION FIXED")
print("=" * 80)
print("The assistant now uses only the tools configured in Dashboard (via toolIds)")
print("You can now test the transfer functionality!")

