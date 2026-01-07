"""
Check the phone numbers of eligible customers
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services import SmartsheetService
from workflows.renewals import (
    get_renewal_customers_ready_for_calls,
    get_mortgage_bill_customers_ready_for_calls,
    should_skip_renewal_row,
    should_skip_mortgage_bill_row
)
from config import RENEWAL_WORKSPACE_NAME
import smartsheet


def find_current_month_sheet():
    """Find the current month's sheet"""
    try:
        smart = smartsheet.Smartsheet(access_token=os.getenv('SMARTSHEET_ACCESS_TOKEN'))
        smart.errors_as_exceptions(True)
        
        workspaces = smart.Workspaces.list_workspaces(pagination_type='token').data
        workspace_id = None
        for ws in workspaces:
            if ws.name.lower() == RENEWAL_WORKSPACE_NAME.lower():
                workspace_id = ws.id
                break
        
        if not workspace_id:
            return None
        
        pacific_tz = ZoneInfo("America/Los_Angeles")
        now = datetime.now(pacific_tz)
        year = now.year
        month = now.month
        
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
                return None
        
        return None
    
    except Exception as e:
        print(f"Error: {e}")
        return None


def check_customers():
    """Check eligible customers and their phone numbers"""
    print("=" * 80)
    print("Checking Eligible Customers Phone Numbers")
    print("=" * 80)
    print()
    
    sheet_info = find_current_month_sheet()
    if not sheet_info:
        print("Could not find sheet")
        return
    
    sheet_id, sheet_name = sheet_info
    print(f"Sheet: {sheet_name} (ID: {sheet_id})")
    print()
    
    smartsheet_service = SmartsheetService(sheet_id=sheet_id)
    
    # Get renewal customers
    print("=" * 80)
    print("Renewal Customers")
    print("=" * 80)
    customers_by_stage = get_renewal_customers_ready_for_calls(smartsheet_service)
    
    total_renewal = sum(len(customers) for customers in customers_by_stage.values())
    print(f"\nTotal Renewal Customers Ready: {total_renewal}")
    
    if total_renewal > 0:
        for stage, customers in customers_by_stage.items():
            if customers:
                print(f"\nStage {stage} ({len(customers)} customers):")
                for i, customer in enumerate(customers, 1):
                    print(f"\n  {i}. Row {customer.get('row_number', 'N/A')}")
                    print(f"     Company: {customer.get('company', 'N/A')}")
                    
                    # Check all possible phone fields
                    phone_fields = {
                        'client_phone_number': customer.get('client_phone_number', ''),
                        'phone_number': customer.get('phone_number', ''),
                        'phone': customer.get('phone', ''),
                    }
                    
                    print(f"     Phone fields:")
                    for field_name, field_value in phone_fields.items():
                        print(f"       - {field_name}: '{field_value}' (type: {type(field_value).__name__})")
                    
                    # Check if should skip
                    should_skip, skip_reason = should_skip_renewal_row(customer)
                    print(f"     Should skip: {should_skip} ({skip_reason})")
                    
                    # Check validation
                    from workflows.renewals import validate_renewal_customer_data
                    is_valid, error_msg, validated = validate_renewal_customer_data(customer)
                    print(f"     Validation: {is_valid} ({error_msg})")
                    if validated:
                        print(f"     Validated phone: {validated.get('phone_number', 'N/A')}")
    
    # Get mortgage bill customers
    print("\n" + "=" * 80)
    print("Mortgage Bill Customers")
    print("=" * 80)
    mortgage_customers = get_mortgage_bill_customers_ready_for_calls(smartsheet_service)
    
    total_mortgage = sum(len(customers) for customers in mortgage_customers.values())
    print(f"\nTotal Mortgage Bill Customers Ready: {total_mortgage}")
    
    if total_mortgage > 0:
        for stage, customers in mortgage_customers.items():
            if customers:
                print(f"\nStage {stage} ({len(customers)} customers):")
                for i, customer in enumerate(customers, 1):
                    print(f"\n  {i}. Row {customer.get('row_number', 'N/A')}")
                    print(f"     Company: {customer.get('company', 'N/A')}")
                    
                    phone_fields = {
                        'client_phone_number': customer.get('client_phone_number', ''),
                        'phone_number': customer.get('phone_number', ''),
                        'phone': customer.get('phone', ''),
                    }
                    
                    print(f"     Phone fields:")
                    for field_name, field_value in phone_fields.items():
                        print(f"       - {field_name}: '{field_value}' (type: {type(field_value).__name__})")
                    
                    should_skip, skip_reason = should_skip_mortgage_bill_row(customer)
                    print(f"     Should skip: {should_skip} ({skip_reason})")


if __name__ == "__main__":
    check_customers()

