# Read Cancellations Dev sheet data
import smartsheet
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Use token from environment variable or set directly
token = os.getenv('SMARTSHEET_ACCESS_TOKEN', 'xr7pjb35y9FyLBJ1KoPXyTQ91W4kD7UQH9kFO')

# Cancellations Dev sheet ID
cancellation_dev_sheet_id = 5146141873098628

# Initialize Smartsheet client only when needed
def get_smartsheet_client():
    """Get Smartsheet client instance"""
    smart = smartsheet.Smartsheet(access_token=token)
    smart.errors_as_exceptions(True)
    return smart

def display_sheet_structure(sheet):
    """Display the structure of the sheet"""
    print(f"\n📊 Sheet Structure:")
    print(f"Name: {sheet.name}")
    print(f"ID: {sheet.id}")
    print(f"Total Rows: {sheet.total_row_count}")
    print(f"Total Columns: {len(sheet.columns)}")
    print(f"Modified: {sheet.modified_at}")
    print(f"Created: {sheet.created_at}")
    
    print(f"\n📋 Columns ({len(sheet.columns)} total):")
    print("-" * 60)
    for i, column in enumerate(sheet.columns, 1):
        print(f"{i:2d}. {column.title:<25} | Type: {str(column.type):<15} | ID: {column.id}")

def find_phone_by_client_policy(sheet, client_id, policy_number):
    """
    Find phone number and other details by Client ID and Policy Number
    
    Args:
        sheet: Smartsheet sheet object
        client_id (str): Client ID to search for
        policy_number (str): Policy Number to search for
    
    Returns:
        dict: Search result with found status and details
    """
    # Find column IDs for the search
    client_id_col = None
    policy_number_col = None
    phone_number_col = None
    
    for col in sheet.columns:
        if col.title == "Client ID":
            client_id_col = col.id
        elif col.title == "Policy Number":
            policy_number_col = col.id
        elif col.title == "Phone number":
            phone_number_col = col.id
    
    # Check if we found all required columns
    missing_cols = []
    if not client_id_col:
        missing_cols.append("Client ID")
    if not policy_number_col:
        missing_cols.append("Policy Number")
    if not phone_number_col:
        missing_cols.append("Phone number")
    
    if missing_cols:
        return {
            "found": False,
            "error": f"Missing required columns: {', '.join(missing_cols)}"
        }
    
    # Search through all rows
    for row in sheet.rows:
        # Get values for comparison
        client_cell = row.get_column(client_id_col)
        policy_cell = row.get_column(policy_number_col)
        
        client_value = str(client_cell.display_value).strip() if client_cell.display_value else ""
        policy_value = str(policy_cell.display_value).strip() if policy_cell.display_value else ""
        
        # Check if both client ID and policy number match
        if client_value == str(client_id).strip() and policy_value == str(policy_number).strip():
            # Found a match! Get the phone number and other relevant info
            phone_cell = row.get_column(phone_number_col)
            phone_value = str(phone_cell.display_value) if phone_cell.display_value else "No phone number"
            
            # Get additional info for context
            result = {
                "found": True,
                "phone_number": phone_value,
                "client_id": client_value,
                "policy_number": policy_value,
                "row_number": row.row_number
            }
            
            # Add other useful information
            for col in sheet.columns:
                if col.title in ["Agent Name", "Office", "Insured", "LOB", "Status", "Cancellation Reason"]:
                    cell = row.get_column(col.id)
                    value = str(cell.display_value) if cell.display_value else ""
                    result[col.title.lower().replace(" ", "_")] = value
            
            return result
    
    # No match found
    return {
        "found": False,
        "error": f"No record found with Client ID '{client_id}' and Policy Number '{policy_number}'"
    }

def search_phone_number(client_id, policy_number):
    """
    Convenient function to search for phone number by client ID and policy number
    
    Args:
        client_id (str): Client ID to search for
        policy_number (str): Policy Number to search for
    
    Returns:
        str: Phone number if found, None if not found
    """
    try:
        # Get the sheet
        smart = get_smartsheet_client()
        sheet = smart.Sheets.get_sheet(cancellation_dev_sheet_id)
        
        # Search for the record
        result = find_phone_by_client_policy(sheet, client_id, policy_number)
        
        if result["found"]:
            print(f"\n🎯 Record Found!")
            print(f"📞 Phone Number: {result['phone_number']}")
            print(f"👤 Client ID: {result['client_id']}")
            print(f"📋 Policy Number: {result['policy_number']}")
            print(f"🏢 Office: {result.get('office', 'N/A')}")
            print(f"👨‍💼 Agent: {result.get('agent_name', 'N/A')}")
            print(f"🏠 Insured: {result.get('insured', 'N/A')}")
            print(f"📊 LOB: {result.get('lob', 'N/A')}")
            print(f"📍 Status: {result.get('status', 'N/A')}")
            print(f"❌ Cancellation Reason: {result.get('cancellation_reason', 'N/A')}")
            print(f"📝 Row Number: {result['row_number']}")
            
            return result['phone_number']
        else:
            print(f"\n❌ {result['error']}")
            return None
            
    except Exception as e:
        error_msg = f"Error searching for phone number: {e}"
        print(f"\n❌ {error_msg}")
        return None

def display_sheet_data(sheet, max_rows=10):
    """Display the data from the sheet"""
    print(f"\n📋 Sheet Data (first {max_rows} rows):")
    print("-" * 80)
    
    # Display headers
    headers = [col.title[:15] for col in sheet.columns[:8]]  # Limit to first 8 columns for display
    header_line = " | ".join(f"{header:<15}" for header in headers)
    print(f"    {header_line}")
    print("-" * 80)
    
    # Display data rows
    for i, row in enumerate(sheet.rows[:max_rows], 1):
        row_data = []
        for col in sheet.columns[:8]:  # Limit to first 8 columns
            cell = row.get_column(col.id)
            value = str(cell.display_value) if cell.display_value else ""
            row_data.append(value[:15])  # Limit cell width
        
        row_line = " | ".join(f"{data:<15}" for data in row_data)
        print(f"{i:2d}. {row_line}")
    
    if len(sheet.rows) > max_rows:
        print(f"\n... and {len(sheet.rows) - max_rows} more rows")

def main():
    """Main execution function - loads and displays sheet data"""
    print("Connecting to Smartsheet...")
    print('Getting Cancellations Dev sheet data...')
    
    try:
        # Get the sheet with all data
        smart = get_smartsheet_client()
        sheet = smart.Sheets.get_sheet(cancellation_dev_sheet_id, include='attachments,discussions')
        
        print(f"\n🎯 Successfully loaded: {sheet.name}")
        
        # Display sheet structure
        display_sheet_structure(sheet)
        
        # Display sheet data
        display_sheet_data(sheet, max_rows=15)
        
        # Additional analysis
        print(f"\n📈 Data Summary:")
        print(f"- Total records: {len(sheet.rows)}")
        print(f"- Last modified: {sheet.modified_at}")
        
        # Check for specific columns that might indicate cancellation data
        cancellation_columns = []
        for col in sheet.columns:
            if any(keyword in col.title.lower() for keyword in ['cancel', 'status', 'reason', 'date', 'policy']):
                cancellation_columns.append(col.title)
        
        if cancellation_columns:
            print(f"\n🔍 Cancellation-related columns found:")
            for col in cancellation_columns:
                print(f"  - {col}")
        
        print(f"\n✅ Data retrieval completed successfully!")
        print(f"📊 You can now analyze the {len(sheet.rows)} records in this cancellation dataset.")
        
        # Example usage of the search function
        print(f"\n" + "="*60)
        print("📞 PHONE NUMBER SEARCH EXAMPLE")
        print("="*60)
        print("Usage: search_phone_number('client_id', 'policy_number')")
        print("Example: search_phone_number('24765', 'ABC123')")
        print()
        print("To use this function in another script:")
        print("1. Import this file: from read_cancellation_dev import search_phone_number")
        print("2. Call: phone = search_phone_number('your_client_id', 'your_policy_number')")

    except Exception as e:
        print(f'Error: {e}')
        print('Please ensure you have access to this sheet')

def interactive_mode():
    """Interactive phone search mode"""
    print(f"\n" + "="*60)
    print("🔍 INTERACTIVE PHONE SEARCH MODE")
    print("="*60)
    
    while True:
        try:
            print("\nEnter search criteria (or 'quit' to exit):")
            client_id = input("Client ID: ").strip()
            
            if client_id.lower() == 'quit':
                print("👋 Goodbye!")
                break
                
            policy_number = input("Policy Number: ").strip()
            
            if not client_id or not policy_number:
                print("❌ Please provide both Client ID and Policy Number")
                continue
            
            # Search for the phone number
            phone = search_phone_number(client_id, policy_number)
            
            if phone:
                print(f"\n✅ Found! Phone number: {phone}")
            
            print("\n" + "-"*40)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            continue

# If this script is run directly, provide main functionality and interactive mode
if __name__ == "__main__":
    # Run the main data loading first
    main()
    
    # Then start interactive mode
    interactive_mode()
