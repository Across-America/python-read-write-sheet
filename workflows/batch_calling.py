"""
Batch Calling Workflows - Business logic for batch calling operations
"""

from services import VAPIService, SmartsheetService
from config import CANCELLATION_DEV_2_SHEET_ID

def test_single_customer_call():
    """
    Test function to call a single customer with detailed analysis
    
    Returns:
        bool: Success status
    """
    print("🧪 TESTING SINGLE CUSTOMER CALL WITH DETAILED ANALYSIS")
    print("=" * 60)
    
    # Initialize services
    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_DEV_2_SHEET_ID)
    vapi_service = VAPIService()
    
    # Get customers with "Not call yet" status
    customers = smartsheet_service.get_not_called_customers()
    
    if not customers:
        print("❌ No customers found with 'Not call yet' status")
        return False
    
    # Take only the first customer for testing
    test_customer = customers[0]
    
    print(f"📞 Testing with customer:")
    print(f"   👤 Name: {test_customer.get('insured', 'Unknown')}")
    print(f"   📱 Phone: {test_customer['phone_number']}")
    print(f"   📋 Policy: {test_customer['policy_number']}")
    print(f"   🏢 Office: {test_customer.get('office', 'N/A')}")
    print(f"   👨‍💼 Agent: {test_customer.get('agent_name', 'N/A')}")
    
    # Make single customer call
    result = vapi_service.make_batch_call([test_customer], schedule_immediately=True)
    
    if result:
        print(f"\n✅ SINGLE CUSTOMER CALL SUCCESSFUL!")
        print(f"📊 Call monitoring and detailed analysis completed")
        
        # Update call status
        smartsheet_service.update_call_status([test_customer], "Called")
        
        # Update call result with detailed analysis
        if 'call_data' in result:
            smartsheet_service.update_call_result(test_customer, result['call_data'])
        
        return True
    else:
        print(f"\n❌ SINGLE CUSTOMER CALL FAILED!")
        return False


def test_batch_call_not_called():
    """
    Test function to call all customers with "Not call yet" status
    
    Returns:
        bool: Success status
    """
    print("🧪 TESTING BATCH CALL FOR 'NOT CALL YET' CUSTOMERS")
    print("=" * 60)
    print("📋 This will call all customers with 'Not call yet' status")
    print("🤖 Using Spencer: Call Transfer V2 Campaign assistant")
    print("🏢 Company caller ID: +1 (951) 247-2003")
    print("=" * 60)
    
    # Initialize services
    smartsheet_service = SmartsheetService()
    vapi_service = VAPIService()
    
    # Get customers with "Not call yet" status
    customers = smartsheet_service.get_not_called_customers()
    
    if not customers:
        print("❌ No customers found with 'Not call yet' status")
        return False
    
    print(f"\n📊 Found {len(customers)} customers to call:")
    print("-" * 50)
    for i, customer in enumerate(customers[:10], 1):
        print(f"{i:2d}. {customer.get('insured', 'Unknown')} - {customer['phone_number']} - {customer['policy_number']}")
    
    if len(customers) > 10:
        print(f"    ... and {len(customers) - 10} more customers")
    
    # Ask for confirmation
    print(f"\n⚠️  WARNING: This will make {len(customers)} phone calls!")
    print(f"💰 This will incur charges for each call")
    print(f"🏢 All calls will show caller ID: +1 (951) 247-2003")
    
    response = input(f"\nProceed with batch calling? (y/N): ").strip().lower()
    
    if response not in ['y', 'yes']:
        print("❌ Batch calling cancelled")
        return False
    
    # Update status to "Calling" before making calls
    print(f"\n📝 Updating status to 'Calling'...")
    smartsheet_service.update_call_status(customers, "Calling")
    
    # Make the batch call
    print(f"\n🚀 Initiating batch call...")
    result = vapi_service.make_batch_call(customers, schedule_immediately=True)
    
    if result:
        print(f"\n✅ BATCH CALL INITIATED SUCCESSFULLY!")
        print(f"📞 Called {len(customers)} customers")
        print(f"🤖 Using Spencer: Call Transfer V2 Campaign")
        print(f"🏢 Caller ID: +1 (951) 247-2003")
        print(f"📊 Check VAPI dashboard for call progress")
        
        # Update status to "Called" after successful initiation
        print(f"\n📝 Updating status to 'Called'...")
        smartsheet_service.update_call_status(customers, "Called")
        
        return True
    else:
        print(f"\n❌ BATCH CALL FAILED!")
        print(f"💡 Check the error messages above for details")
        
        # Revert status back to "Not call yet" if call failed
        print(f"\n📝 Reverting status back to 'Not call yet'...")
        smartsheet_service.update_call_status(customers, "Not call yet")
        
        return False


def show_not_called_customers():
    """
    Show all customers with "Not call yet" status without calling
    """
    print("📋 SHOWING 'NOT CALL YET' CUSTOMERS")
    print("=" * 60)
    
    smartsheet_service = SmartsheetService()
    customers = smartsheet_service.get_not_called_customers()
    
    if customers:
        print(f"\n📊 Found {len(customers)} customers with 'Not call yet' status:")
        print("-" * 60)
        for i, customer in enumerate(customers, 1):
            print(f"{i:2d}. {customer.get('insured', 'Unknown')}")
            print(f"    📱 Phone: {customer['phone_number']}")
            print(f"    📋 Policy: {customer['policy_number']}")
            print(f"    🏢 Office: {customer.get('office', 'N/A')}")
            print(f"    👨‍💼 Agent: {customer.get('agent_name', 'N/A')}")
            print()
    else:
        print("❌ No customers found with 'Not call yet' status")
