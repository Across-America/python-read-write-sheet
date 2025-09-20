# Demonstration of phone number search functionality
import os
from dotenv import load_dotenv
from read_cancellation_dev import search_phone_number

# Load environment variables
load_dotenv()

print("📞 PHONE NUMBER SEARCH DEMONSTRATION")
print("="*60)

# Let's first get some actual data to test with
print("First, let's get some real Policy Numbers from the data...")
print()

# Since we need actual Policy Numbers, let's create a function to show some sample data
def show_sample_data():
    import smartsheet
    
    # Set up connection
    token = os.getenv('SMARTSHEET_ACCESS_TOKEN', 'xr7pjb35y9FyLBJ1KoPXyTQ91W4kD7UQH9kFO')
    smart = smartsheet.Smartsheet(access_token=token)
    smart.errors_as_exceptions(True)
    
    try:
        # Get the sheet
        sheet = smart.Sheets.get_sheet(5146141873098628)  # Cancellations Dev sheet ID
        
        print("📋 Sample records with Policy Numbers:")
        print("-" * 60)
        
        # Find column IDs
        client_id_col = None
        policy_number_col = None
        phone_number_col = None
        insured_col = None
        
        for col in sheet.columns:
            if col.title == "Client ID":
                client_id_col = col.id
            elif col.title == "Policy Number":
                policy_number_col = col.id
            elif col.title == "Phone number":
                phone_number_col = col.id
            elif col.title == "Insured":
                insured_col = col.id
        
        # Show first 10 records that have both Client ID and Policy Number
        count = 0
        for i, row in enumerate(sheet.rows):
            if count >= 5:  # Show only first 5 complete records
                break
                
            client_cell = row.get_column(client_id_col)
            policy_cell = row.get_column(policy_number_col)
            phone_cell = row.get_column(phone_number_col)
            insured_cell = row.get_column(insured_col)
            
            client_id = str(client_cell.display_value) if client_cell.display_value else ""
            policy_number = str(policy_cell.display_value) if policy_cell.display_value else ""
            phone_number = str(phone_cell.display_value) if phone_cell.display_value else ""
            insured = str(insured_cell.display_value) if insured_cell.display_value else ""
            
            # Only show records that have both Client ID and Policy Number
            if client_id and policy_number:
                count += 1
                print(f"{count}. Client ID: {client_id:<8} | Policy: {policy_number:<15} | Insured: {insured:<20} | Phone: {phone_number}")
        
        if count > 0:
            print(f"\n✅ Found {count} complete records to test with!")
            return True
        else:
            print("❌ No complete records found with both Client ID and Policy Number")
            return False
            
    except Exception as e:
        print(f"❌ Error getting sample data: {e}")
        return False

# Show sample data
if show_sample_data():
    print("\n" + "="*60)
    print("🧪 TEST THE SEARCH FUNCTION")
    print("="*60)
    print("Copy any Client ID and Policy Number from above and test:")
    print()
    
    # Interactive test
    while True:
        try:
            print("Enter search criteria (or 'quit' to exit):")
            client_id = input("Client ID: ").strip()
            
            if client_id.lower() == 'quit':
                break
                
            policy_number = input("Policy Number: ").strip()
            
            if not client_id or not policy_number:
                print("❌ Please provide both Client ID and Policy Number")
                continue
            
            print(f"\n🔍 Searching for Client ID: {client_id}, Policy: {policy_number}")
            print("-" * 50)
            
            # Use our search function
            phone = search_phone_number(client_id, policy_number)
            
            print("\n" + "-"*50)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            continue

print("\n💡 USAGE SUMMARY:")
print("="*60)
print("✅ Function created: search_phone_number(client_id, policy_number)")
print("✅ Returns phone number and additional customer info")
print("✅ Handles errors gracefully")
print("✅ Can be imported and used in other scripts")
print("\n📖 Import in other scripts:")
print("   from read_cancellation_dev import search_phone_number")
print("   phone = search_phone_number('12345', 'POL123')")
