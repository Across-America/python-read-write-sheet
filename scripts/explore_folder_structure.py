"""
Script to explore the folder structure in ASI workspace
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


def list_folder_contents(smart, folder_id, indent=0):
    """Recursively list all folders and sheets"""
    try:
        folder = smart.Folders.get_folder(folder_id)
        prefix = "  " * indent
        
        # List subfolders
        if hasattr(folder, 'folders') and folder.folders:
            for subfolder in folder.folders:
                print(f"{prefix}[FOLDER] {subfolder.name} (ID: {subfolder.id})")
                list_folder_contents(smart, subfolder.id, indent + 1)
        
        # List sheets
        if hasattr(folder, 'sheets') and folder.sheets:
            for sheet in folder.sheets:
                print(f"{prefix}[SHEET] {sheet.name} (ID: {sheet.id})")
    
    except Exception as e:
        print(f"{'  ' * indent}Error: {e}")


def main():
    """Main function to explore folder structure"""
    print("=" * 80)
    print("Exploring folder structure in ASI workspace")
    print("=" * 80)
    print()
    
    try:
        smart = smartsheet.Smartsheet(access_token=SMARTSHEET_ACCESS_TOKEN)
        smart.errors_as_exceptions(True)
        
        # Find workspace
        print(f"Looking for workspace: '{RENEWAL_WORKSPACE_NAME}'...")
        workspaces = smart.Workspaces.list_workspaces(pagination_type='token').data
        
        workspace_id = None
        for ws in workspaces:
            if ws.name.lower() == RENEWAL_WORKSPACE_NAME.lower():
                workspace_id = ws.id
                print(f"Found workspace: '{ws.name}' (ID: {workspace_id})")
                break
        
        if not workspace_id:
            print(f"Workspace '{RENEWAL_WORKSPACE_NAME}' not found")
            return
        
        # Get workspace contents
        print()
        print("Workspace structure:")
        print("-" * 80)
        workspace = smart.Workspaces.get_workspace(workspace_id, load_all=True)
        
        # List top-level folders
        if hasattr(workspace, 'folders') and workspace.folders:
            for folder in workspace.folders:
                print(f"[FOLDER] {folder.name} (ID: {folder.id})")
                list_folder_contents(smart, folder.id, indent=1)
                print()
        
        # List top-level sheets
        if hasattr(workspace, 'sheets') and workspace.sheets:
            print("Top-level sheets:")
            for sheet in workspace.sheets:
                print(f"  [SHEET] {sheet.name} (ID: {sheet.id})")
        
        print()
        print("=" * 80)
        print("Exploration complete")
        print("=" * 80)
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

