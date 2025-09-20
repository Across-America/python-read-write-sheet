#!/usr/bin/env python3
"""
Main entry point for the VAPI calling system
This script provides a unified interface to all calling functionality
"""

import sys
import os
from core import auto_call_and_update, batch_call_customers, get_all_customers_to_call

def main():
    """
    Main function with interactive menu
    """
    print("🤖 VAPI CALLING SYSTEM")
    print("=" * 50)
    print("Choose an option:")
    print("1. Make single call (Client ID + Policy Number)")
    print("2. Make single call (Phone Number)")
    print("3. Batch call all customers")
    print("4. Test phone number lookup")
    print("5. Quit")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == "1":
                print("\n📞 Single Call by Client ID + Policy Number:")
                client_id = input("Client ID: ").strip()
                policy_number = input("Policy Number: ").strip()
                
                if client_id and policy_number:
                    print(f"\n🚀 Starting call process...")
                    success = auto_call_and_update(client_id, policy_number)
                    if success:
                        print("✅ Call completed successfully!")
                    else:
                        print("❌ Call failed!")
                else:
                    print("❌ Please provide both Client ID and Policy Number")
                    
            elif choice == "2":
                print("\n📞 Single Call by Phone Number:")
                phone_number = input("Phone Number: ").strip()
                
                if phone_number:
                    print(f"\n🚀 Starting call process...")
                    success = auto_call_and_update(None, None, phone_number)
                    if success:
                        print("✅ Call completed successfully!")
                    else:
                        print("❌ Call failed!")
                else:
                    print("❌ Please provide a phone number")
                    
            elif choice == "3":
                print("\n📞 Batch Call All Customers:")
                print("⚠️  This will call ALL customers in the sheet!")
                confirm = input("Are you sure? (yes/no): ").strip().lower()
                
                if confirm in ['yes', 'y']:
                    customers = get_all_customers_to_call()
                    if customers:
                        print(f"Found {len(customers)} customers to call")
                        results = batch_call_customers(customers)
                        print(f"\n📊 Batch call completed!")
                        print(f"✅ Successful: {results['successful']}")
                        print(f"❌ Failed: {results['failed']}")
                    else:
                        print("❌ No customers found to call")
                else:
                    print("❌ Batch calling cancelled")
                    
            elif choice == "4":
                print("\n🔍 Test Phone Number Lookup:")
                client_id = input("Client ID: ").strip()
                policy_number = input("Policy Number: ").strip()
                
                if client_id and policy_number:
                    from tools import find_phone_by_client_policy
                    import smartsheet
                    import os
                    from dotenv import load_dotenv
                    
                    load_dotenv()
                    token = os.getenv('SMARTSHEET_ACCESS_TOKEN', 'xr7pjb35y9FyLBJ1KoPXyTQ91W4kD7UQH9kFO')
                    smart = smartsheet.Smartsheet(access_token=token)
                    smart.errors_as_exceptions(True)
                    
                    sheet = smart.Sheets.get_sheet(5146141873098628)
                    result = find_phone_by_client_policy(sheet, client_id, policy_number)
                    
                    if result["found"]:
                        print(f"✅ Found customer!")
                        print(f"📞 Phone: {result['phone_number']}")
                        print(f"👤 Insured: {result.get('insured', 'N/A')}")
                        print(f"🏢 Office: {result.get('office', 'N/A')}")
                    else:
                        print(f"❌ {result['error']}")
                else:
                    print("❌ Please provide both Client ID and Policy Number")
                    
            elif choice == "5":
                print("👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid choice. Please enter 1-5")
                
            print("\n" + "-" * 50)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            continue

if __name__ == "__main__":
    main()
