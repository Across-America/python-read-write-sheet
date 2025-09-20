#!/usr/bin/env python3
"""
Batch Call System for handling hundreds of calls
This system can handle large volumes of calls with rate limiting and error handling
"""

import time
import os
from dotenv import load_dotenv
import smartsheet
from .auto_call_and_update import auto_call_and_update, get_next_phone_number_id

# Load environment variables
load_dotenv()

# Smartsheet Configuration
token = os.getenv('SMARTSHEET_ACCESS_TOKEN', 'xr7pjb35y9FyLBJ1KoPXyTQ91W4kD7UQH9kFO')
smart = smartsheet.Smartsheet(access_token=token)
smart.errors_as_exceptions(True)
cancellation_dev_sheet_id = 5146141873098628

def get_all_customers_to_call():
    """
    Get all customers from the cancellation sheet that need to be called
    
    Returns:
        list: List of customer records with phone numbers
    """
    try:
        print("🔍 Loading all customers from cancellation sheet...")
        sheet = smart.Sheets.get_sheet(cancellation_dev_sheet_id)
        
        customers = []
        
        # Find column IDs
        client_id_col = None
        policy_number_col = None
        phone_number_col = None
        call_status_col = None
        
        for col in sheet.columns:
            if col.title == "Client ID":
                client_id_col = col.id
            elif col.title == "Policy Number":
                policy_number_col = col.id
            elif col.title == "Phone number":
                phone_number_col = col.id
            elif col.title == "Call Status":
                call_status_col = col.id
        
        if not all([client_id_col, policy_number_col, phone_number_col]):
            print("❌ Required columns not found")
            return []
        
        # Process all rows
        for row in sheet.rows:
            client_cell = row.get_column(client_id_col)
            policy_cell = row.get_column(policy_number_col)
            phone_cell = row.get_column(phone_number_col)
            
            client_id = str(client_cell.display_value).strip() if client_cell.display_value else ""
            policy_number = str(policy_cell.display_value).strip() if policy_cell.display_value else ""
            phone_number = str(phone_cell.display_value).strip() if phone_cell.display_value else ""
            
            # Check if this customer has a valid phone number and hasn't been called yet
            if (client_id and policy_number and phone_number and 
                phone_number != "No phone number" and 
                len(phone_number) >= 10):
                
                # Check call status if available
                call_status = ""
                if call_status_col:
                    call_status_cell = row.get_column(call_status_col)
                    call_status = str(call_status_cell.display_value).strip() if call_status_cell.display_value else ""
                
                # Only call if not already called or if call failed
                if not call_status or call_status.lower() in ["", "failed", "no answer"]:
                    customer = {
                        "client_id": client_id,
                        "policy_number": policy_number,
                        "phone_number": phone_number,
                        "row_number": row.row_number,
                        "call_status": call_status
                    }
                    
                    # Add other useful information
                    for col in sheet.columns:
                        if col.title in ["Agent Name", "Office", "Insured", "LOB", "Status", "Cancellation Reason"]:
                            cell = row.get_column(col.id)
                            value = str(cell.display_value) if cell.display_value else ""
                            customer[col.title.lower().replace(" ", "_")] = value
                    
                    customers.append(customer)
        
        print(f"✅ Found {len(customers)} customers to call")
        return customers
        
    except Exception as e:
        print(f"❌ Error loading customers: {e}")
        return []

def batch_call_customers(customers, delay_between_calls=30, max_calls_per_hour=50):
    """
    Make batch calls to customers with rate limiting
    
    Args:
        customers (list): List of customer records
        delay_between_calls (int): Seconds to wait between calls
        max_calls_per_hour (int): Maximum calls per hour to respect limits
    
    Returns:
        dict: Summary of results
    """
    print(f"🚀 Starting batch call process")
    print(f"📊 Total customers: {len(customers)}")
    print(f"⏱️  Delay between calls: {delay_between_calls} seconds")
    print(f"📈 Max calls per hour: {max_calls_per_hour}")
    print("=" * 60)
    
    results = {
        "total": len(customers),
        "successful": 0,
        "failed": 0,
        "skipped": 0,
        "errors": []
    }
    
    start_time = time.time()
    calls_this_hour = 0
    hour_start_time = start_time
    
    for i, customer in enumerate(customers, 1):
        # Check if we've exceeded hourly limit
        current_time = time.time()
        if current_time - hour_start_time >= 3600:  # 1 hour
            calls_this_hour = 0
            hour_start_time = current_time
        
        if calls_this_hour >= max_calls_per_hour:
            print(f"⏸️  Hourly limit reached ({max_calls_per_hour} calls). Waiting...")
            time.sleep(3600 - (current_time - hour_start_time))
            calls_this_hour = 0
            hour_start_time = time.time()
        
        print(f"\n📞 Call {i}/{len(customers)}")
        print(f"👤 Customer: {customer.get('insured', 'Unknown')}")
        print(f"📋 Policy: {customer['policy_number']}")
        print(f"📱 Phone: {customer['phone_number']}")
        
        try:
            # Make the call
            success = auto_call_and_update(
                customer['client_id'], 
                customer['policy_number'], 
                customer['phone_number']
            )
            
            if success:
                results["successful"] += 1
                print(f"✅ Call {i} completed successfully")
            else:
                results["failed"] += 1
                print(f"❌ Call {i} failed")
            
            calls_this_hour += 1
            
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"Call {i}: {str(e)}")
            print(f"❌ Call {i} error: {e}")
        
        # Wait before next call (except for the last one)
        if i < len(customers):
            print(f"⏳ Waiting {delay_between_calls} seconds before next call...")
            time.sleep(delay_between_calls)
    
    # Print final summary
    print(f"\n🎉 BATCH CALL PROCESS COMPLETED!")
    print("=" * 60)
    print(f"📊 Total calls: {results['total']}")
    print(f"✅ Successful: {results['successful']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"⏭️  Skipped: {results['skipped']}")
    print(f"⏱️  Total time: {int((time.time() - start_time) / 60)} minutes")
    
    if results["errors"]:
        print(f"\n❌ Errors encountered:")
        for error in results["errors"][:10]:  # Show first 10 errors
            print(f"   - {error}")
        if len(results["errors"]) > 10:
            print(f"   ... and {len(results['errors']) - 10} more errors")
    
    return results

def main():
    """
    Main function to run batch calling
    """
    print("🤖 BATCH CALL SYSTEM")
    print("=" * 50)
    
    # Get all customers
    customers = get_all_customers_to_call()
    
    if not customers:
        print("❌ No customers found to call")
        return
    
    # Ask for confirmation
    print(f"\n⚠️  About to call {len(customers)} customers")
    print("This will take approximately:")
    print(f"   - {len(customers) * 30 / 60:.1f} minutes (with 30s delay)")
    print(f"   - {len(customers) * 30 / 3600:.1f} hours total")
    
    confirm = input("\nDo you want to proceed? (yes/no): ").strip().lower()
    
    if confirm in ['yes', 'y']:
        # Start batch calling
        results = batch_call_customers(customers)
        
        # Save results to file
        with open("batch_call_results.txt", "w") as f:
            f.write(f"Batch Call Results - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n")
            f.write(f"Total calls: {results['total']}\n")
            f.write(f"Successful: {results['successful']}\n")
            f.write(f"Failed: {results['failed']}\n")
            f.write(f"Skipped: {results['skipped']}\n")
            f.write("\nErrors:\n")
            for error in results["errors"]:
                f.write(f"- {error}\n")
        
        print(f"\n📄 Results saved to batch_call_results.txt")
    else:
        print("❌ Batch calling cancelled")

if __name__ == "__main__":
    main()
