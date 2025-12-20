"""
Batch update missing call_notes for today's calls
"""
import sys
import os
from pathlib import Path

# Fix Windows encoding issue
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services import VAPIService
from workflows.stm1 import get_stm1_sheet, update_after_stm1_call
from config import STM1_PHONE_NUMBER_ID
from datetime import datetime
from zoneinfo import ZoneInfo
import time

def batch_update_missing_call_notes():
    """Batch update missing call_notes for today's calls"""
    print("=" * 80)
    print("🔧 BATCH UPDATING MISSING CALL_NOTES")
    print("=" * 80)
    
    pacific_tz = ZoneInfo("America/Los_Angeles")
    now_pacific = datetime.now(pacific_tz)
    today_start = now_pacific.replace(hour=0, minute=0, second=0, microsecond=0)
    today_str = now_pacific.strftime('%Y-%m-%d')
    
    try:
        # Get VAPI calls from today
        print("\n1️⃣ Fetching today's VAPI calls...")
        vapi_service = VAPIService(phone_number_id=STM1_PHONE_NUMBER_ID)
        recent_calls = vapi_service.get_recent_calls(limit=200)
        
        today_calls = []
        for call in recent_calls:
            created_at = call.get('createdAt', '')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if created_dt.tzinfo is None:
                            created_dt = pacific_tz.localize(created_dt)
                    else:
                        created_dt = created_at
                    
                    if created_dt.replace(tzinfo=pacific_tz) >= today_start and call.get('status') == 'ended':
                        customer_info = call.get('customer', {})
                        customer_name = customer_info.get('name', 'N/A') if isinstance(customer_info, dict) else 'N/A'
                        today_calls.append({
                            'id': call.get('id', 'N/A'),
                            'customer_name': customer_name,
                            'created_at': created_dt,
                            'ended_reason': call.get('endedReason', 'N/A')
                        })
                except:
                    pass
        
        print(f"   ✅ Found {len(today_calls)} completed calls today")
        
        # Get Smartsheet customers
        print("\n2️⃣ Fetching Smartsheet customers...")
        smartsheet_service = get_stm1_sheet()
        all_customers = smartsheet_service.get_all_customers_with_stages()
        print(f"   ✅ Loaded {len(all_customers)} customers")
        
        # Find calls that need updating
        print("\n3️⃣ Identifying calls that need updating...")
        calls_to_update = []
        
        for call in today_calls:
            customer_name = call['customer_name'].replace('...', '').strip() if call['customer_name'] != 'N/A' else ''
            
            # Find matching customer
            matching_customer = None
            for customer in all_customers:
                insured_name = customer.get('insured_name_', '') or customer.get('insured_name', '') or customer.get('company', '')
                if customer_name and insured_name:
                    if customer_name[:40] in insured_name or insured_name[:40] in customer_name:
                        matching_customer = customer
                        break
            
            if matching_customer:
                call_notes = matching_customer.get('call_notes', '') or matching_customer.get('stm1_call_notes', '')
                # Check if today's date is in call_notes
                if not call_notes or today_str not in call_notes:
                    calls_to_update.append({
                        'call_id': call['id'],
                        'customer': matching_customer,
                        'customer_name': insured_name
                    })
        
        print(f"   ✅ Found {len(calls_to_update)} calls that need updating")
        
        if not calls_to_update:
            print("\n   ✅ All calls are already updated!")
            return True
        
        # Ask for confirmation (skip if auto_confirm flag is set)
        print(f"\n4️⃣ Ready to update {len(calls_to_update)} calls")
        print("   This will update call_notes, called_times, and transfer status")
        
        # Check for auto_confirm flag from command line
        auto_confirm = '--auto-confirm' in sys.argv or '-y' in sys.argv
        
        if not auto_confirm:
            try:
                response = input("\n   Proceed with batch update? (y/N): ").strip().lower()
                if response not in ['y', 'yes']:
                    print("   ❌ Batch update cancelled")
                    return False
            except EOFError:
                print("   ⚠️  Non-interactive mode - use --auto-confirm flag to proceed")
                return False
        else:
            print("   🤖 AUTO-CONFIRM: Proceeding automatically")
        
        # Batch update
        print("\n5️⃣ Starting batch update...")
        print("=" * 80)
        
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        for i, item in enumerate(calls_to_update, 1):
            call_id = item['call_id']
            customer = item['customer']
            customer_name = item['customer_name']
            
            print(f"\n[{i}/{len(calls_to_update)}] Processing: {customer_name[:50]}")
            print(f"   Call ID: {call_id}")
            
            try:
                # Get full call data
                call_data = vapi_service.check_call_status(call_id)
                if not call_data:
                    print(f"   ⚠️  Failed to get call data, skipping")
                    skipped_count += 1
                    continue
                
                # Check if analysis exists
                if not call_data.get('analysis') or not call_data.get('analysis', {}).get('summary'):
                    print(f"   ⚠️  No analysis found, trying to wait for completion...")
                    try:
                        call_data = vapi_service.wait_for_call_completion(call_id, check_interval=5, max_wait_time=30)
                        if not call_data or not call_data.get('analysis'):
                            print(f"   ⚠️  Still no analysis, skipping")
                            skipped_count += 1
                            continue
                    except Exception as e:
                        print(f"   ⚠️  Error waiting for analysis: {e}, skipping")
                        skipped_count += 1
                        continue
                
                # Update Smartsheet
                try:
                    success = update_after_stm1_call(smartsheet_service, customer, call_data)
                    if success:
                        print(f"   ✅ Updated successfully")
                        success_count += 1
                    else:
                        print(f"   ❌ Update returned False")
                        failed_count += 1
                except Exception as e:
                    print(f"   ❌ Update failed: {e}")
                    failed_count += 1
                
                # Small delay to avoid rate limiting
                if i < len(calls_to_update):
                    time.sleep(1)
                    
            except Exception as e:
                print(f"   ❌ Error processing call: {e}")
                failed_count += 1
        
        # Summary
        print("\n" + "=" * 80)
        print("6️⃣ BATCH UPDATE SUMMARY")
        print("=" * 80)
        print(f"   ✅ Successfully updated: {success_count}")
        print(f"   ❌ Failed: {failed_count}")
        print(f"   ⚠️  Skipped: {skipped_count}")
        print(f"   📊 Total processed: {success_count + failed_count + skipped_count}")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    batch_update_missing_call_notes()

