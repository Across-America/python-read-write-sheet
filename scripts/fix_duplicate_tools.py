"""
Fix duplicate transferCall tools in STM1 assistant
Remove duplicate tools, keep only one of each type
"""

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
print("🔧 FIXING DUPLICATE TOOLS IN STM1 ASSISTANT")
print("=" * 80)
print(f"🤖 Assistant ID: {STM1_ASSISTANT_ID}")
print("=" * 80)

# Get current assistant configuration
print("\n📥 Fetching current assistant configuration...")
response = requests.get(
    f"{base_url}/assistant/{STM1_ASSISTANT_ID}",
    headers=headers
)

if response.status_code != 200:
    print(f"❌ Failed: {response.status_code}")
    print(response.text)
    sys.exit(1)

assistant = response.json()
model = assistant.get('model', {})
current_tools = model.get('tools', [])

print(f"📊 Current tools: {len(current_tools)}")
for i, tool in enumerate(current_tools, 1):
    print(f"   Tool {i}: {tool.get('type', 'unknown')}")

# Remove duplicates - keep only one of each type
print("\n🔍 Checking for duplicates...")
unique_tools = []
seen_types = set()

for tool in current_tools:
    tool_type = tool.get('type', 'unknown')
    if tool_type not in seen_types:
        unique_tools.append(tool)
        seen_types.add(tool_type)
        print(f"   ✅ Keeping: {tool_type}")
    else:
        print(f"   ⚠️  Removing duplicate: {tool_type}")

if len(unique_tools) == len(current_tools):
    print("\n✅ No duplicates found - all tools are unique")
    sys.exit(0)

print(f"\n📋 After deduplication: {len(unique_tools)} tools")
for i, tool in enumerate(unique_tools, 1):
    print(f"   Tool {i}: {tool.get('type', 'unknown')}")

# Update assistant
print("\n📤 Updating assistant configuration...")
model['tools'] = unique_tools

update_payload = {
    "model": model
}

update_response = requests.patch(
    f"{base_url}/assistant/{STM1_ASSISTANT_ID}",
    headers=headers,
    json=update_payload
)

if update_response.status_code in [200, 201]:
    print("✅ Successfully removed duplicate tools!")
    
    # Verify
    verify_response = requests.get(
        f"{base_url}/assistant/{STM1_ASSISTANT_ID}",
        headers=headers
    )
    
    if verify_response.status_code == 200:
        updated_assistant = verify_response.json()
        updated_model = updated_assistant.get('model', {})
        updated_tools = updated_model.get('tools', [])
        print(f"\n✅ Verified: {len(updated_tools)} tools now configured")
        for i, tool in enumerate(updated_tools, 1):
            print(f"   Tool {i}: {tool.get('type', 'unknown')}")
else:
    print(f"❌ Failed: {update_response.status_code}")
    print(update_response.text)

