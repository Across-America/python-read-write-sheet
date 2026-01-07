"""
Script to process a specific sheet by year and month
Usage: python scripts/process_sheet_by_date.py [--year YEAR] [--month MONTH] [--test]
"""

import sys
import os
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
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


def is_weekend(date):
    """Check if a date falls on weekend"""
    return date.weekday() >= 5  # 5=Saturday, 6=Sunday


def find_year_folder(year):
    """Find the folder for a specific year"""
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
        print(f"Error finding year folder: {e}")
        import traceback
        traceback.print_exc()
        return None


def find_sheet_by_month(folder_id, month):
    """
    Find a sheet by month number in a folder
    
    Args:
        folder_id: ID of the folder
        month: Month number (1-12)
    
    Returns:
        dict with 'id' and 'name' if found, None otherwise
    """
    try:
        smart = smartsheet.Smartsheet(access_token=SMARTSHEET_ACCESS_TOKEN)
        smart.errors_as_exceptions(True)
        
        folder = smart.Folders.get_folder(folder_id)
        
        # Month names
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        
        month_name = month_names[month - 1]
        
        # Try different naming patterns
        patterns = [
            f"{month}. {month_name} PLR",  # "1. January PLR"
            f"{month:02d}. {month_name} PLR",  # "01. January PLR"
            f"{month_name} PLR",  # "January PLR"
        ]
        
        if hasattr(folder, 'sheets') and folder.sheets:
            for sheet in folder.sheets:
                sheet_name_lower = sheet.name.lower()
                for pattern in patterns:
                    if pattern.lower() in sheet_name_lower:
                        return {
                            'id': sheet.id,
                            'name': sheet.name
                        }
        
        # If not found, list all sheets for debugging
        print(f"⚠️  Sheet not found with patterns: {patterns}")
        print(f"Available sheets in folder:")
        if hasattr(folder, 'sheets') and folder.sheets:
            for sheet in folder.sheets:
                print(f"  - {sheet.name} (ID: {sheet.id})")
        
        return None
    
    except Exception as e:
        print(f"Error finding sheet: {e}")
        import traceback
        traceback.print_exc()
        return None


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
    """Main function to process sheet by year and month"""
    parser = argparse.ArgumentParser(
        description='Process a specific sheet by year and month',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process current month's sheet
  python scripts/process_sheet_by_date.py
  
  # Process January 2026 sheet
  python scripts/process_sheet_by_date.py --year 2026 --month 1
  
  # Process February 2026 sheet in test mode
  python scripts/process_sheet_by_date.py --year 2026 --month 2 --test
  
  # Process December 2025 sheet
  python scripts/process_sheet_by_date.py --year 2025 --month 12
        """
    )
    
    parser.add_argument('--year', type=int, help='Year (e.g., 2026)', default=None)
    parser.add_argument('--month', type=int, help='Month number (1-12)', default=None)
    parser.add_argument('--test', action='store_true', help='Test mode (no actual calls or updates)')
    
    args = parser.parse_args()
    
    # Check if manually triggered via GitHub Actions
    is_manual_trigger = os.getenv('GITHUB_EVENT_NAME') == 'workflow_dispatch'
    
    # Get current date if not specified
    now = datetime.now()
    year = args.year if args.year else now.year
    month = args.month if args.month else now.month
    
    # Validate month
    if month < 1 or month > 12:
        print(f"❌ Invalid month: {month}. Month must be between 1 and 12.")
        return
    
    # Time check for automated runs (skip for manual triggers)
    if not is_manual_trigger:
        pacific_tz = ZoneInfo("America/Los_Angeles")
        now_pacific = datetime.now(pacific_tz)
        
        # Renewal workflow runs at 11:00 AM and 4:00 PM Pacific time
        # Use a time window to handle DST and GitHub Actions delays:
        # - Morning: 10:00 AM - 12:59 PM (covers 10 AM, 11 AM, 12 PM)
        # - Afternoon: 3:00 PM - 5:59 PM (covers 3 PM, 4 PM, 5 PM)
        morning_window = (10 <= now_pacific.hour <= 12)
        afternoon_window = (15 <= now_pacific.hour <= 17)
        
        if not (morning_window or afternoon_window):
            print("=" * 80)
            print(f"⏭️  Skipping: Current Pacific time is {now_pacific.strftime('%I:%M %p')}")
            print(f"   Expected time window: 10:00 AM - 12:59 PM or 3:00 PM - 5:59 PM")
            print("=" * 80)
            return
        
        # Check if today is weekend (skip weekends, no calls on weekends)
        today_date = now_pacific.date()
        if is_weekend(today_date):
            print("=" * 80)
            print(f"⏭️  Skipping: Today is {today_date.strftime('%A')} (weekend) - no calls on weekends")
            print("=" * 80)
            return
    
    print("=" * 80)
    print(f"Processing Sheet by Date")
    print(f"Year: {year}, Month: {month}")
    if is_manual_trigger:
        print("🖱️  Manual trigger detected - skipping time check")
    
    # Explicitly show mode
    if args.test:
        print("🧪 TEST MODE - No actual calls or updates will be made")
    else:
        print("📞 PRODUCTION MODE - Will make actual phone calls")
        # Verify VAPI API key is set
        vapi_key = os.getenv('VAPI_API_KEY')
        if not vapi_key:
            print("❌ ERROR: VAPI_API_KEY environment variable is not set!")
            print("   Cannot make calls without VAPI API key")
            return False
        else:
            print(f"✅ VAPI API key is configured (length: {len(vapi_key)} characters)")
    print("=" * 80)
    print()
    
    # Find year folder
    print(f"🔍 Finding folder for year {year}...")
    folder_id = find_year_folder(year)
    
    if not folder_id:
        print(f"❌ Could not find folder for year {year}")
        print(f"   Path: ASI -> Personal Line -> Task Prototype -> Renewal / Non-Renewal -> {year}")
        return
    
    print(f"✅ Found year folder (ID: {folder_id})")
    print()
    
    # Find sheet by month
    print(f"🔍 Finding sheet for month {month}...")
    sheet_info = find_sheet_by_month(folder_id, month)
    
    if not sheet_info:
        print(f"❌ Could not find sheet for month {month} in year {year} folder")
        return
    
    print(f"✅ Found sheet: {sheet_info['name']} (ID: {sheet_info['id']})")
    print()
    
    # Process the sheet
    success = process_sheet(sheet_info['id'], sheet_info['name'], test_mode=args.test)
    
    if success:
        print()
        print("=" * 80)
        print("✅ Processing complete")
        print("=" * 80)
    else:
        print()
        print("=" * 80)
        print("❌ Processing failed")
        print("=" * 80)


if __name__ == "__main__":
    main()

