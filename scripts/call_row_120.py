"""Call specific row 120"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from workflows.stm1 import (
    get_stm1_sheet,
    validate_stm1_customer_data,
    update_after_stm1_call
)
from workflows.stm1_variables import build_stm1_variable_values
from services import VAPIService
from config import STM1_ASSISTANT_ID, STM1_PHONE_NUMBER_ID, STM1_CALLING_START_HOUR, STM1_CALLING_END_HOUR
from datetime import datetime
from zoneinfo import ZoneInfo

TARGET_ROW = 120  # Row 120 (0-indexed: 119)

if __name__ == "__main__":
    print("=" * 80)
    print(f"📞 CALLING ROW {TARGET_ROW}")
    print("=" * 80)
    
    # Check current time
    pacific_tz = ZoneInfo("America/Los_Angeles")
    now_pacific = datetime.now(pacific_tz)
    current_hour = now_pacific.hour
    current_minute = now_pacific.minute
    
    print(f"Current time: {now_pacific.strftime('%I:%M %p %Z')}")
    print(f"Calling hours: {STM1_CALLING_START_HOUR}:00 AM - {STM1_CALLING_END_HOUR}:00 PM Pacific Time")
    print()
    
    # Check if current time is within calling hours
    if current_hour < STM1_CALLING_START_HOUR or current_hour >= STM1_CALLING_END_HOUR:
        print(f"❌ Outside calling hours ({STM1_CALLING_START_HOUR}:00 - {STM1_CALLING_END_HOUR}:00 Pacific Time)")
        print(f"   Current time: {now_pacific.strftime('%I:%M %p %Z')}")
        sys.exit(1)
    
    # Safety check: Don't start calls too close to end time
    if current_hour == STM1_CALLING_END_HOUR - 1 and current_minute >= 55:
        print(f"❌ Too close to end of calling hours")
        print(f"   Current time: {now_pacific.strftime('%I:%M %p %Z')}")
        sys.exit(1)
    
    print(f"✅ Current time is within calling hours")
    print()
    
    try:
        # Initialize services
        print("=" * 80)
        print("🔧 INITIALIZING SERVICES")
        print("=" * 80)
        smartsheet_service = get_stm1_sheet()
        vapi_service = VAPIService(phone_number_id=STM1_PHONE_NUMBER_ID)
        print(f"✅ Services initialized")
        print(f"   🤖 Assistant ID: {STM1_ASSISTANT_ID}")
        print(f"   📱 Phone Number ID: {STM1_PHONE_NUMBER_ID}")
        
        # Get all customers and find row 120
        print("\n" + "=" * 80)
        print(f"🔍 FETCHING ROW {TARGET_ROW}")
        print("=" * 80)
        all_customers = smartsheet_service.get_all_customers_with_stages()
        
        # Row 120 is at index 119 (0-indexed)
        if len(all_customers) < TARGET_ROW:
            print(f"❌ Sheet only has {len(all_customers)} rows, cannot access row {TARGET_ROW}")
            sys.exit(1)
        
        customer = all_customers[TARGET_ROW - 1]  # Convert to 0-indexed
        
        company = customer.get('insured_name_', '') or customer.get('insured_name', '') or customer.get('company', 'Unknown')
        phone = customer.get('phone_number', '') or customer.get('contact_phone', '')
        claim = customer.get('claim_number', 'N/A')
        row_num = customer.get('row_number', 'N/A')
        
        print(f"📋 Row {row_num}: {company}")
        print(f"   Phone: {phone}")
        print(f"   Claim: {claim}")
        print("=" * 80)
        
        # Validate customer
        print("\n🔍 Validating customer data...")
        is_valid, error_msg, validated_data = validate_stm1_customer_data(customer)
        if not is_valid:
            print(f"❌ Validation failed: {error_msg}")
            sys.exit(1)
        
        print("✅ Validation passed")
        
        # Merge validated data
        customer_for_call = {**customer, **validated_data}
        
        # Make call
        print("\n" + "=" * 80)
        print("📞 INITIATING CALL")
        print("=" * 80)
        print(f"   🚀 Initiating call...")
        
        results = vapi_service.make_batch_call_with_assistant(
            [customer_for_call],
            STM1_ASSISTANT_ID,
            schedule_immediately=True,
            custom_variable_builder=build_stm1_variable_values
        )
        
        if results and results[0]:
            call_data = results[0]
            print(f"   ✅ Call completed")
            
            # Check if analysis exists, try to refresh if missing
            if 'analysis' not in call_data or not call_data.get('analysis'):
                print(f"   ⚠️  No analysis in call_data, attempting to refresh...")
                if 'id' in call_data:
                    call_id = call_data['id']
                    try:
                        refreshed_data = vapi_service.wait_for_call_completion(call_id)
                        if refreshed_data and refreshed_data.get('analysis'):
                            call_data = refreshed_data
                            print(f"      ✅ Successfully retrieved analysis from refreshed call status")
                    except Exception as e:
                        print(f"      ❌ Failed to refresh call status: {e}")
            
            # Check transfer status
            ended_reason = call_data.get('endedReason', '')
            print(f"\n📊 Call Results:")
            print(f"   📋 endedReason: {ended_reason}")
            if ended_reason == 'assistant-forwarded-call':
                print(f"   🔄 ✅ TRANSFER SUCCESSFUL!")
            else:
                print(f"   📞 No transfer detected")
            
            # Update Smartsheet
            print(f"\n📝 Updating Smartsheet...")
            try:
                success = update_after_stm1_call(smartsheet_service, customer, call_data)
                if success:
                    print(f"✅ Smartsheet updated successfully")
                    print(f"   • Transfer Status: {'Yes' if ended_reason == 'assistant-forwarded-call' else 'No'} (endedReason: {ended_reason})")
                else:
                    print(f"❌ Smartsheet update failed")
            except Exception as e:
                print(f"❌ Exception during Smartsheet update: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"   ❌ Call failed - no results returned")
            sys.exit(1)
        
        print("\n" + "=" * 80)
        print("✅ COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


