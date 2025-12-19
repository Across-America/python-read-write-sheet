"""
Find STM1 sheet in workspace
Search for sheets matching "statement" or "call" in AACS workspace
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Fix Windows encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from services.smartsheet_service import SmartsheetService
from config import STM1_WORKSPACE_NAME

def find_sheets_in_workspace():
    """Find all sheets in STM1 workspace"""
    print("=" * 80)
    print(f"🔍 SEARCHING FOR SHEETS IN WORKSPACE: {STM1_WORKSPACE_NAME}")
    print("=" * 80)
    
    try:
        # Try common sheet names
        possible_names = [
            "statements call",
            "statement call", 
            "Statements Call",
            "Statement Call",
            "Insured Driver Statement",
            "STM1",
            "stm1"
        ]
        
        print(f"\n📋 Searching for sheets matching STM1 keywords in workspace '{STM1_WORKSPACE_NAME}'...")
        
        found_sheets = []
        for sheet_name in possible_names:
            try:
                print(f"\n   🔍 Trying: '{sheet_name}'...")
                test_service = SmartsheetService(
                    sheet_name=sheet_name,
                    workspace_name=STM1_WORKSPACE_NAME
                )
                print(f"      ✅ Found! Sheet ID: {test_service.sheet_id}")
                print(f"      📄 Sheet Name: {sheet_name}")
                found_sheets.append({
                    'name': sheet_name,
                    'id': test_service.sheet_id
                })
            except Exception as e:
                error_msg = str(e)
                if "not found" in error_msg.lower() or "not found" in error_msg:
                    print(f"      ❌ Not found")
                else:
                    print(f"      ⚠️  Error: {error_msg[:100]}")
        
        if found_sheets:
            print("\n" + "=" * 80)
            print("📊 FOUND SHEETS:")
            print("=" * 80)
            for sheet in found_sheets:
                print(f"   • {sheet['name']} (ID: {sheet['id']})")
            print("=" * 80)
        else:
            print("\n⚠️  No matching sheets found. Please check:")
            print("   1. Workspace name is correct")
            print("   2. Sheet name spelling")
            print("   3. You have access to the workspace")
        
        print("\n" + "=" * 80)
        print("💡 TIP: If you know the exact sheet name, update STM1_SHEET_NAME in config/settings.py")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    find_sheets_in_workspace()

