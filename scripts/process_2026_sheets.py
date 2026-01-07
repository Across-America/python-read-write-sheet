"""
Script to process all sheets in the 2026 folder
This will run the renewal workflow for each sheet in the 2026 folder
"""

import sys
import os
# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import smartsheet
from config import SMARTSHEET_ACCESS_TOKEN, RENEWAL_WORKSPACE_NAME
from workflows.renewals import run_renewal_batch_calling
from services import SmartsheetService


def find_2026_folder():
    """Find the 2026 folder ID"""
    try:
        smart = smartsheet.Smartsheet(access_token=SMARTSHEET_ACCESS_TOKEN)
        smart.errors_as_exceptions(True)
        
        # Find workspace
        workspaces = smart.Workspaces.list_workspaces(pagination_type='token').data
        workspace_id = None
        for ws in workspaces:
            if ws.name.lower() == RENEWAL_WORKSPACE_NAME.lower():
                workspace_id = ws.id
                break
        
        if not workspace_id:
            print(f"Workspace '{RENEWAL_WORKSPACE_NAME}' not found")
            return None
        
        # Navigate to 2026 folder
        workspace = smart.Workspaces.get_workspace(workspace_id, load_all=True)
        folder_path = ["Personal Line", "Task Prototype", "Renewal / Non-Renewal", "2026"]
        
        current = workspace
        for folder_name in folder_path:
            if hasattr(current, 'folders'):
                folders = current.folders
            else:
                folder_details = smart.Folders.get_folder(current.id)
                folders = folder_details.folders if hasattr(folder_details, 'folders') else []
            
            found = False
            for folder in folders:
                if folder.name.lower() == folder_name.lower():
                    if folder_name == "2026":
                        return folder.id
                    folder_details = smart.Folders.get_folder(folder.id)
                    current = folder_details
                    found = True
                    break
            
            if not found:
                print(f"Folder '{folder_name}' not found")
                return None
        
        return None
    
    except Exception as e:
        print(f"Error finding 2026 folder: {e}")
        import traceback
        traceback.print_exc()
        return None


def list_sheets_in_2026_folder(folder_id):
    """List all sheets in the 2026 folder"""
    try:
        smart = smartsheet.Smartsheet(access_token=SMARTSHEET_ACCESS_TOKEN)
        smart.errors_as_exceptions(True)
        
        folder = smart.Folders.get_folder(folder_id)
        
        sheets = []
        if hasattr(folder, 'sheets') and folder.sheets:
            for sheet in folder.sheets:
                sheets.append({
                    'id': sheet.id,
                    'name': sheet.name
                })
        
        return sheets
    
    except Exception as e:
        print(f"Error listing sheets: {e}")
        return []


def process_sheet(sheet_id, sheet_name, test_mode=False):
    """Process a single sheet using the renewal workflow"""
    print()
    print("=" * 80)
    print(f"Processing sheet: {sheet_name} (ID: {sheet_id})")
    print("=" * 80)
    
    try:
        # Run the renewal workflow with the specific sheet ID
        run_renewal_batch_calling(test_mode=test_mode, auto_confirm=True, sheet_id=sheet_id, sheet_name=sheet_name)
        
        print(f"✅ Successfully processed sheet: {sheet_name}")
        return True
    
    except Exception as e:
        print(f"❌ Error processing sheet {sheet_name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function to process all sheets in 2026 folder"""
    print("=" * 80)
    print("Batch Processing: All Sheets in 2026 Folder")
    print("Path: ASI -> Personal Line -> Task Prototype -> Renewal / Non-Renewal -> 2026")
    print("=" * 80)
    print()
    
    # Check for test mode
    test_mode = "--test" in sys.argv or "-t" in sys.argv
    
    if test_mode:
        print("🧪 TEST MODE - No actual calls or updates will be made")
        print()
    
    # Find 2026 folder
    print("🔍 Finding 2026 folder...")
    folder_id = find_2026_folder()
    
    if not folder_id:
        print("❌ Could not find the 2026 folder")
        return
    
    print(f"✅ Found 2026 folder (ID: {folder_id})")
    print()
    
    # List all sheets
    print("🔍 Listing all sheets in 2026 folder...")
    sheets = list_sheets_in_2026_folder(folder_id)
    
    if not sheets:
        print("⚠️  No sheets found in the 2026 folder")
        return
    
    print(f"📊 Found {len(sheets)} sheet(s):")
    for i, sheet in enumerate(sheets, 1):
        print(f"   {i}. {sheet['name']} (ID: {sheet['id']})")
    print()
    
    # Confirm before processing
    if not test_mode:
        response = input(f"Process all {len(sheets)} sheet(s)? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Cancelled.")
            return
    
    # Process each sheet
    print()
    print("=" * 80)
    print("Starting batch processing...")
    print("=" * 80)
    
    results = []
    for i, sheet in enumerate(sheets, 1):
        print()
        print(f"[{i}/{len(sheets)}] Processing: {sheet['name']}")
        success = process_sheet(sheet['id'], sheet['name'], test_mode=test_mode)
        results.append({
            'sheet_name': sheet['name'],
            'sheet_id': sheet['id'],
            'success': success
        })
    
    # Print summary
    print()
    print("=" * 80)
    print("Batch Processing Summary")
    print("=" * 80)
    print()
    
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    print(f"Total sheets: {len(results)}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print()
    
    if successful > 0:
        print("Successfully processed sheets:")
        for r in results:
            if r['success']:
                print(f"   ✅ {r['sheet_name']}")
    
    if failed > 0:
        print()
        print("Failed sheets:")
        for r in results:
            if not r['success']:
                print(f"   ❌ {r['sheet_name']}")
    
    print()
    print("=" * 80)
    print("Batch processing complete")
    print("=" * 80)


if __name__ == "__main__":
    main()

