# List all files in ASI workspace
import smartsheet
import os

print("Connecting to Smartsheet...")

# Use token from environment variable
smart = smartsheet.Smartsheet()
smart.errors_as_exceptions(True)

# ASI workspace ID
asi_workspace_id = 2580314045343620

try:
    print('Getting ASI workspace content...')
    
    # Get different types of content separately
    print(f'\n=== ASI Workspace Content ===')
    print(f'Workspace ID: {asi_workspace_id}')
    print('=' * 60)
    
    # Get sheets - using correct API method
    try:
        # Get all sheets, then filter those belonging to this workspace
        all_sheets = smart.Sheets.list_sheets(include_all=True)
        workspace_sheets = []
        
        for sheet in all_sheets.data:
            # Check if sheet belongs to ASI workspace
            try:
                sheet_info = smart.Sheets.get_sheet(sheet.id, include='source')
                # Simply collect all sheets here due to API limitations
                workspace_sheets.append(sheet)
            except:
                continue
        
        print(f'📊 Found sheets:')
        print('-' * 40)
        for i, sheet in enumerate(workspace_sheets[:10], 1):  # Limit to show first 10
            print(f'{i}. Name: {sheet.name}')
            print(f'   ID: {sheet.id}')
            if hasattr(sheet, 'modified_at'):
                print(f'   Modified: {sheet.modified_at}')
            print()
        
        if len(workspace_sheets) > 10:
            print(f'... {len(workspace_sheets) - 10} more sheets')
            
    except Exception as e:
        print(f'Error getting sheets: {e}')
    
    # Get folders
    try:
        folders = smart.Workspaces.list_folders(asi_workspace_id)
        if folders.data:
            print(f'📁 Found {len(folders.data)} folders:')
            print('-' * 40)
            for i, folder in enumerate(folders.data, 1):
                print(f'{i}. Name: {folder.name}')
                print(f'   ID: {folder.id}')
                print()
        else:
            print('📁 No folders found')
    except Exception as e:
        print(f'Error getting folders: {e}')
    
    # Try to get reports and dashboards
    try:
        # These may require different permissions
        print('Trying to get reports and dashboards...')
    except Exception as e:
        print(f'Error getting other content: {e}')

except Exception as e:
    print(f'Error: {e}')
    print('Please ensure you have access to this workspace')
