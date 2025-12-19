"""
Configure STM1 Assistant Tools
Add transfer_call_to_AllClaim and STM_end_call_tool to the assistant
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

def configure_tools():
    """Configure tools for STM1 assistant"""
    print("=" * 80)
    print("🔧 CONFIGURING STM1 ASSISTANT TOOLS")
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
        print(f"❌ Failed to fetch assistant: {response.status_code}")
        print(response.text)
        return False
    
    assistant = response.json()
    print("✅ Successfully fetched assistant configuration")
    
    # Get transfer phone number from command line args or use default
    print("\n📱 Transfer Phone Number Configuration")
    print("=" * 80)
    
    # Check command line arguments
    transfer_phone_number_id = None
    if len(sys.argv) > 1:
        transfer_phone_number_id = sys.argv[1]
        print(f"Using transfer phone number ID from command line: {transfer_phone_number_id}")
    else:
        # Try to get from input (non-interactive will fail gracefully)
        try:
            print("Please provide the phone number ID for transfers.")
            print("This should be the phone number that calls will be transferred to.")
            print("Usage: python scripts/configure_stm1_tools.py <phone_number_id>")
            print()
            transfer_phone_number_id = input("Enter Transfer Phone Number ID (or press Enter to skip): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("⚠️  Non-interactive environment detected.")
            print("⚠️  No transfer phone number provided. Transfer tool will be created without phone number.")
            print("   You can update it later in VAPI Dashboard or run:")
            print(f"   python scripts/configure_stm1_tools.py <phone_number_id>")
            transfer_phone_number_id = None
    
    if not transfer_phone_number_id:
        print("⚠️  No transfer phone number provided. Transfer tool will be created without phone number.")
        print("   You can update it later in VAPI Dashboard.")
        transfer_phone_number_id = None
    
    # Prepare tools configuration
    # Note: VAPI uses specific tool types: "transferCall" and "endCall"
    # Tools don't have a "name" field - they're identified by type
    tools = []
    
    # 1. Transfer Tool
    # Note: transferMessage might be configured elsewhere or in the prompt
    transfer_tool = {
        "type": "transferCall"  # Correct type name for VAPI
    }
    
    if transfer_phone_number_id:
        transfer_tool["phoneNumberId"] = transfer_phone_number_id
    
    tools.append(transfer_tool)
    
    # 2. End Call Tool
    end_call_tool = {
        "type": "endCall"  # Correct type name for VAPI
    }
    tools.append(end_call_tool)
    
    print(f"\n📋 Tools to be added:")
    print(f"   1. Transfer Tool: {transfer_tool['type']}")
    print(f"   2. End Call Tool: {end_call_tool['type']}")
    
    # Confirm before updating (skip in non-interactive mode)
    print("\n" + "=" * 80)
    try:
        confirm = input("Proceed with adding these tools? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("❌ Cancelled")
            return False
    except (EOFError, KeyboardInterrupt):
        print("⚠️  Non-interactive mode - auto-confirming...")
        # Auto-confirm in non-interactive mode
    
    # Update assistant with tools
    print("\n📤 Updating assistant configuration...")
    
    # VAPI requires tools to be in model.tools, not top-level
    model = assistant.get('model', {})
    if not model:
        model = {}
    
    # Update model with tools
    model['tools'] = tools
    
    update_payload = {
        "model": model
    }
    
    # Update assistant
    update_response = requests.patch(
        f"{base_url}/assistant/{STM1_ASSISTANT_ID}",
        headers=headers,
        json=update_payload
    )
    
    if update_response.status_code in [200, 201]:
        print("✅ Successfully updated assistant with tools!")
        
        # Verify the update
        print("\n🔍 Verifying update...")
        verify_response = requests.get(
            f"{base_url}/assistant/{STM1_ASSISTANT_ID}",
            headers=headers
        )
        
        if verify_response.status_code == 200:
            updated_assistant = verify_response.json()
            updated_model = updated_assistant.get('model', {})
            updated_tools = updated_model.get('tools', [])
            print(f"   ✅ Verified: {len(updated_tools)} tools now configured")
            
            for i, tool in enumerate(updated_tools, 1):
                tool_type = tool.get('type', 'unknown')
                print(f"   Tool {i}: {tool_type}")
                if tool_type == 'transferCall':
                    phone_id = tool.get('phoneNumberId', 'Not set')
                    transfer_msg = tool.get('transferMessage', 'Not set')
                    print(f"      📱 Transfer Phone Number ID: {phone_id}")
                    print(f"      💬 Transfer Message: {transfer_msg[:50]}...")
            
            return True
        else:
            print(f"   ⚠️  Update may have succeeded but verification failed: {verify_response.status_code}")
            return True
    else:
        print(f"❌ Failed to update assistant: {update_response.status_code}")
        print(f"   Response: {update_response.text}")
        print(f"\n💡 You may need to manually configure tools in VAPI Dashboard")
        print(f"   Required tools:")
        print(f"   1. Transfer Tool:")
        print(f"      • Type: transferCall")
        print(f"      • Transfer Phone Number ID: [your transfer number ID]")
        print(f"      • Transfer Message: 'Great, I will now transfer you...'")
        print(f"   2. End Call Tool:")
        print(f"      • Type: endCall")
        return False

if __name__ == "__main__":
    try:
        success = configure_tools()
        if success:
            print("\n" + "=" * 80)
            print("✅ CONFIGURATION COMPLETE")
            print("=" * 80)
            print("You can now test the transfer functionality.")
        else:
            print("\n" + "=" * 80)
            print("❌ CONFIGURATION FAILED")
            print("=" * 80)
            print("Please configure tools manually in VAPI Dashboard.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

