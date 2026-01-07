"""
Check if N1 Project (Renewal Workflow) made any calls today
"""
import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services import SmartsheetService
from config import RENEWAL_WORKSPACE_NAME
import smartsheet


def find_current_month_sheet():
    """Find the current month's sheet"""
    try:
        smart = smartsheet.Smartsheet(access_token=os.getenv('SMARTSHEET_ACCESS_TOKEN'))
        smart.errors_as_exceptions(True)
        
        # Find workspace
        workspaces = smart.Workspaces.list_workspaces(pagination_type='token').data
        workspace_id = None
        for ws in workspaces:
            if ws.name.lower() == RENEWAL_WORKSPACE_NAME.lower():
                workspace_id = ws.id
                break
        
        if not workspace_id:
            print(f"❌ Workspace '{RENEWAL_WORKSPACE_NAME}' not found")
            return None
        
        # Get current year and month
        pacific_tz = ZoneInfo("America/Los_Angeles")
        now = datetime.now(pacific_tz)
        year = now.year
        month = now.month
        
        # Navigate to year folder
        workspace = smart.Workspaces.get_workspace(workspace_id, load_all=True)
        folder_path = ["Personal Line", "Task Prototype", "Renewal / Non-Renewal", str(year)]
        
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
                    if folder_name == str(year):
                        year_folder_id = folder.id
                        # Find sheet by month
                        folder_details = smart.Folders.get_folder(year_folder_id)
                        month_names = [
                            "January", "February", "March", "April", "May", "June",
                            "July", "August", "September", "October", "November", "December"
                        ]
                        month_name = month_names[month - 1]
                        patterns = [
                            f"{month}. {month_name} PLR",
                            f"{month:02d}. {month_name} PLR",
                            f"{month_name} PLR",
                        ]
                        
                        if hasattr(folder_details, 'sheets') and folder_details.sheets:
                            for sheet in folder_details.sheets:
                                sheet_name_lower = sheet.name.lower()
                                for pattern in patterns:
                                    if pattern.lower() in sheet_name_lower:
                                        return sheet.id, sheet.name
                        break
                    folder_details = smart.Folders.get_folder(folder.id)
                    current = folder_details
                    found = True
                    break
            
            if not found:
                print(f"❌ Folder '{folder_name}' not found")
                return None
        
        return None
    
    except Exception as e:
        print(f"❌ Error finding sheet: {e}")
        import traceback
        traceback.print_exc()
        return None


def check_today_calls():
    """Check if there were any calls made today"""
    pacific_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific_tz).date()
    today_str = today.strftime('%Y-%m-%d')
    
    print("=" * 80)
    print(f"Checking N1 Project (Renewal) Calls for Today: {today_str}")
    print("=" * 80)
    print()
    
    # Find current month's sheet
    print("🔍 Finding current month's sheet...")
    sheet_info = find_current_month_sheet()
    
    if not sheet_info:
        print("❌ Could not find current month's sheet")
        return
    
    sheet_id, sheet_name = sheet_info
    print(f"✅ Found sheet: {sheet_name} (ID: {sheet_id})")
    print()
    
    # Load customers from sheet
    print("📋 Loading customers from sheet...")
    try:
        smartsheet_service = SmartsheetService(sheet_id=sheet_id)
        all_customers = smartsheet_service.get_all_customers_with_stages()
        print(f"✅ Loaded {len(all_customers)} customers")
        print()
    except Exception as e:
        print(f"❌ Error loading customers: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Check for today's calls
    print("🔍 Checking for calls made today...")
    print()
    
    calls_today = []
    for customer in all_customers:
        # Check Last Call Made Date
        last_call_date_str = customer.get('last_call_made_date', '') or ''
        if last_call_date_str:
            try:
                # Try to parse the date
                from workflows.renewals import parse_date
                last_call_date = parse_date(last_call_date_str)
                if last_call_date and last_call_date == today:
                    calls_today.append({
                        'company': customer.get('company', 'N/A'),
                        'phone': customer.get('phone', 'N/A'),
                        'last_call_date': last_call_date_str,
                        'source': 'Last Call Made Date'
                    })
            except:
                pass
        
        # Also check Call Notes for today's date
        call_notes = customer.get('call_notes', '') or ''
        if call_notes and today_str in call_notes:
            # Check if this customer is already in the list
            company = customer.get('company', 'N/A')
            if not any(c['company'] == company for c in calls_today):
                calls_today.append({
                    'company': company,
                    'phone': customer.get('phone', 'N/A'),
                    'call_notes_preview': call_notes[:100] + '...' if len(call_notes) > 100 else call_notes,
                    'source': 'Call Notes'
                })
    
    # Print results
    print("=" * 80)
    print(f"📊 Results for {today_str}")
    print("=" * 80)
    
    if calls_today:
        print(f"✅ Found {len(calls_today)} customer(s) with calls made today:")
        print()
        for i, call in enumerate(calls_today, 1):
            print(f"{i}. {call['company']} - {call['phone']}")
            print(f"   Source: {call['source']}")
            if 'last_call_date' in call:
                print(f"   Last Call Date: {call['last_call_date']}")
            print()
    else:
        print("❌ No calls found for today")
        print()
        print("Possible reasons:")
        print("  - Workflow hasn't run yet today")
        print("  - No customers were ready for calls")
        print("  - Workflow ran but no calls were made")
        print("  - Check GitHub Actions for workflow execution status")
    
    print("=" * 80)


if __name__ == "__main__":
    check_today_calls()

