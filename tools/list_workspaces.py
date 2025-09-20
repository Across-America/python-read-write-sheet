# List all Smartsheet workspaces
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

try:
    print('Getting all workspaces...')
    
    # Get all workspaces
    workspaces = smart.Workspaces.list_workspaces()
    
    print(f'\nYou have a total of {len(workspaces.data)} workspaces:')
    print('=' * 60)
    
    for i, workspace in enumerate(workspaces.data, 1):
        print(f'{i}. Workspace Name: {workspace.name}')
        print(f'   Workspace ID: {workspace.id}')
        print(f'   Access Level: {workspace.access_level}')
        print('-' * 40)
    
    print('\nPlease check the list above to find the ASI workspace name and ID')
    print('Then tell me the specific workspace name, and I can help you view the files inside!')

except Exception as e:
    print(f'Error: {e}')
    print('Please ensure your API token is set correctly')
