"""
Diagnose why no N1 customers are eligible for calls today
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
from workflows.renewals import (
    get_renewal_customers_ready_for_calls,
    get_mortgage_bill_customers_ready_for_calls,
    get_renewal_expired_after_customers,
    parse_date,
    is_weekend
)
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
            print(f"Workspace '{RENEWAL_WORKSPACE_NAME}' not found")
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
                print(f"Folder '{folder_name}' not found")
                return None
        
        return None
    
    except Exception as e:
        print(f"Error finding sheet: {e}")
        import traceback
        traceback.print_exc()
        return None


def diagnose_eligibility():
    """Diagnose why customers are not eligible"""
    pacific_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific_tz).date()
    today_datetime = datetime.now(pacific_tz)
    
    print("=" * 80)
    print(f"Diagnosing N1 Project Eligibility for Today: {today.strftime('%Y-%m-%d %A')}")
    print(f"Current Time (Pacific): {today_datetime.strftime('%H:%M %p')}")
    print("=" * 80)
    print()
    
    # Check if weekend
    if is_weekend(today):
        print("⚠️  Today is a weekend - workflow should skip")
        print()
    
    # Find current month's sheet
    print("Finding current month's sheet...")
    sheet_info = find_current_month_sheet()
    
    if not sheet_info:
        print("Could not find current month's sheet")
        return
    
    sheet_id, sheet_name = sheet_info
    print(f"✅ Found sheet: {sheet_name} (ID: {sheet_id})")
    print()
    
    # Initialize service
    try:
        smartsheet_service = SmartsheetService(sheet_id=sheet_id)
    except Exception as e:
        print(f"Error initializing service: {e}")
        return
    
    # Get customers ready for calls
    print("=" * 80)
    print("Checking Renewal Customers Ready for Calls")
    print("=" * 80)
    print()
    
    try:
        customers_by_stage = get_renewal_customers_ready_for_calls(smartsheet_service)
        
        total_ready = sum(len(customers) for customers in customers_by_stage.values())
        
        print()
        print("=" * 80)
        print(f"Renewal Customers Ready: {total_ready}")
        print("=" * 80)
        
        if total_ready > 0:
            for stage, customers in customers_by_stage.items():
                if customers:
                    print(f"\nStage {stage} ({len(customers)} customers):")
                    for i, customer in enumerate(customers[:5], 1):  # Show first 5
                        print(f"  {i}. {customer.get('company', 'N/A')} - {customer.get('phone', 'N/A')}")
                        exp_date = customer.get('expiration_date', '')
                        print(f"     Expiration: {exp_date}")
                    if len(customers) > 5:
                        print(f"  ... and {len(customers) - 5} more")
        else:
            print("\n❌ No renewal customers ready for calls today")
        
        print()
        
        # Check mortgage bill customers
        print("=" * 80)
        print("Checking Mortgage Bill Customers Ready for Calls")
        print("=" * 80)
        print()
        
        mortgage_customers = get_mortgage_bill_customers_ready_for_calls(smartsheet_service)
        mortgage_total = sum(len(customers) for customers in mortgage_customers.values())
        
        print(f"Mortgage Bill Customers Ready: {mortgage_total}")
        
        if mortgage_total > 0:
            for stage, customers in mortgage_customers.items():
                if customers:
                    print(f"\nStage {stage} ({len(customers)} customers):")
                    for i, customer in enumerate(customers[:5], 1):
                        print(f"  {i}. {customer.get('company', 'N/A')} - {customer.get('phone', 'N/A')}")
        else:
            print("\n❌ No mortgage bill customers ready for calls today")
        
        print()
        
        # Check expired customers
        print("=" * 80)
        print("Checking Expired Customers (after expiration date)")
        print("=" * 80)
        print()
        
        expired_customers = get_renewal_expired_after_customers(smartsheet_service)
        
        print(f"Expired Customers: {len(expired_customers)}")
        
        if expired_customers:
            print("\nExpired customers:")
            for i, customer in enumerate(expired_customers[:5], 1):
                print(f"  {i}. {customer.get('company', 'N/A')} - {customer.get('phone', 'N/A')}")
                exp_date = customer.get('expiration_date', '')
                print(f"     Expiration: {exp_date}")
        else:
            print("\n❌ No expired customers found")
        
        print()
        print("=" * 80)
        print("Summary")
        print("=" * 80)
        print(f"Total Ready for Calls Today: {total_ready + mortgage_total + len(expired_customers)}")
        print(f"  - Renewal: {total_ready}")
        print(f"  - Mortgage Bill: {mortgage_total}")
        print(f"  - Expired: {len(expired_customers)}")
        print()
        
        if total_ready == 0 and mortgage_total == 0 and len(expired_customers) == 0:
            print("⚠️  No customers are eligible for calls today.")
            print("\nPossible reasons:")
            print("  1. No customers are in the calling window (14/7/1/0 days before expiry)")
            print("  2. All customers are filtered out (wrong payee, status, etc.)")
            print("  3. Today is not the scheduled calling day (calls start on day 1 of month)")
            print("  4. All customers already have 'Done' checked")
            print("  5. All customers missing required fields (phone, expiration date, etc.)")
        
    except Exception as e:
        print(f"Error checking customers: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    diagnose_eligibility()

