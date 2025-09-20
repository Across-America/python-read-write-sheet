# Explore Personal Line > Cancellations folder
import smartsheet
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

print("Connecting to Smartsheet...")

# Use token from environment variable or set directly
token = os.getenv('SMARTSHEET_ACCESS_TOKEN', 'xr7pjb35y9FyLBJ1KoPXyTQ91W4kD7UQH9kFO')
smart = smartsheet.Smartsheet(access_token=token)
smart.errors_as_exceptions(True)

# Cancellations folder ID (obtained from previous results)
cancellations_folder_id = 6500165851867012

def get_folder_contents(folder_id, folder_name):
    """Get all contents in the folder"""
    try:
        print(f'\n📁 Viewing folder: {folder_name}')
        print(f'Folder ID: {folder_id}')
        print('=' * 60)
        
        # Use correct API method to get folder contents
        folder = smart.Folders.get_folder(folder_id)
        
        sheets_found = []
        subfolders_found = []
        
        # Check sheets in folder
        if hasattr(folder, 'sheets') and folder.sheets:
            sheets_found = folder.sheets
            print(f'📊 Sheets ({len(sheets_found)} items):')
            print('-' * 40)
            for i, sheet in enumerate(sheets_found, 1):
                print(f'{i}. Name: {sheet.name}')
                print(f'   ID: {sheet.id}')
                if hasattr(sheet, 'modified_at') and sheet.modified_at:
                    print(f'   Modified: {sheet.modified_at}')
                if hasattr(sheet, 'created_at') and sheet.created_at:
                    print(f'   Created: {sheet.created_at}')
                print()
        else:
            print('📊 No sheets found')
        
        # Check subfolders
        if hasattr(folder, 'folders') and folder.folders:
            subfolders_found = folder.folders
            print(f'📁 Subfolders ({len(subfolders_found)} items):')
            print('-' * 40)
            for i, subfolder in enumerate(subfolders_found, 1):
                print(f'{i}. Name: {subfolder.name}')
                print(f'   ID: {subfolder.id}')
                print()
        else:
            print('📁 No subfolders found')
        
        # Check reports
        if hasattr(folder, 'reports') and folder.reports:
            print(f'📈 Reports ({len(folder.reports)} items):')
            print('-' * 40)
            for i, report in enumerate(folder.reports, 1):
                print(f'{i}. Name: {report.name}')
                print(f'   ID: {report.id}')
                print()
        
        # Check dashboards
        if hasattr(folder, 'dashboards') and folder.dashboards:
            print(f'📋 Dashboards ({len(folder.dashboards)} items):')
            print('-' * 40)
            for i, dashboard in enumerate(folder.dashboards, 1):
                print(f'{i}. Name: {dashboard.name}')
                print(f'   ID: {dashboard.id}')
                print()
        
        return sheets_found, subfolders_found
        
    except Exception as e:
        print(f'Error getting folder contents: {e}')
        return [], []

try:
    print(f'\n=== Personal Line > Cancellations Folder Content ===')
    
    # Get Cancellations folder content
    sheets, subfolders = get_folder_contents(cancellations_folder_id, "Cancellations")
    
    # If there are subfolders, show their content too
    if subfolders:
        print(f'\n{"="*60}')
        print('Subfolder detailed content:')
        for subfolder in subfolders:
            get_folder_contents(subfolder.id, f"Cancellations > {subfolder.name}")
    
    # Provide operation suggestions
    if sheets:
        print(f'\n{"="*60}')
        print('📋 Available operations:')
        print('1. View specific sheet details')
        print('2. Read sheet data')
        print('3. Update sheet content')
        print('4. Export sheet data')
        print('\nPlease tell me which sheet you want to operate on and what operation you want to perform!')

except Exception as e:
    print(f'Error: {e}')
    print('Please ensure you have access to this folder')
