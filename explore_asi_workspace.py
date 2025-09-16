# Explore ASI workspace
import smartsheet
import os

print("Connecting to Smartsheet...")

# Use token from environment variable
smart = smartsheet.Smartsheet()
smart.errors_as_exceptions(True)

# ASI 工作区 ID
asi_workspace_id = 2580314045343620

def list_folder_contents(folder_id, folder_name):
    """List contents in folder"""
    try:
        print(f'\n📁 Viewing folder: {folder_name}')
        print('=' * 50)
        
        # Get sheets in folder
        try:
            sheets = smart.Folders.list_sheets(folder_id)
            if sheets.data:
                print(f'📊 Sheets ({len(sheets.data)} items):')
                for i, sheet in enumerate(sheets.data, 1):
                    print(f'  {i}. {sheet.name} (ID: {sheet.id})')
            else:
                print('📊 No sheets')
        except Exception as e:
            print(f'Failed to get sheets: {e}')
        
        # Get subfolders in folder
        try:
            subfolders = smart.Folders.list_folders(folder_id)
            if subfolders.data:
                print(f'📁 Subfolders ({len(subfolders.data)} items):')
                for i, subfolder in enumerate(subfolders.data, 1):
                    print(f'  {i}. {subfolder.name} (ID: {subfolder.id})')
            else:
                print('📁 No subfolders')
        except Exception as e:
            print(f'Failed to get subfolders: {e}')
            
    except Exception as e:
        print(f'Error viewing folder {folder_name}: {e}')

try:
    print(f'\n=== ASI Workspace Structure ===')
    print(f'Workspace ID: {asi_workspace_id}')
    print('=' * 60)
    
    # Get root level folders
    folders = smart.Workspaces.list_folders(asi_workspace_id)
    
    if folders.data:
        print(f'🏠 Root level folders ({len(folders.data)} items):')
        print('-' * 40)
        for i, folder in enumerate(folders.data, 1):
            print(f'{i}. {folder.name} (ID: {folder.id})')
        
        print('\n' + '='*60)
        print('Detailed content:')
        
        # View content of each folder
        for folder in folders.data:
            list_folder_contents(folder.id, folder.name)
    else:
        print('📁 No folders found')
    
    # Try to get root level sheets
    try:
        print(f'\n🏠 Root level sheets:')
        print('=' * 50)
        # May need different method to get root level sheets
        print('Trying to get root level sheets...')
    except Exception as e:
        print(f'Error getting root level sheets: {e}')

except Exception as e:
    print(f'Error: {e}')
    print('Please ensure you have access to this workspace')
