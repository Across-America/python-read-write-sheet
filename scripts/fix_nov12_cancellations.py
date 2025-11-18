#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix November 12 Cancellation Records
This script will:
1. Find customers that should have been called on Nov 12, 2025
2. Search for their VAPI calls
3. Update Smartsheet with the call results
"""

import sys
import os
from pathlib import Path

# Fix Windows encoding issues
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, date
from zoneinfo import ZoneInfo
from services import VAPIService, SmartsheetService
from config import CANCELLATION_SHEET_ID, CANCELLATION_1ST_REMINDER_ASSISTANT_ID
from workflows.cancellations import (
    get_call_stage,
    update_after_call,
    parse_date,
    calculate_next_followup_date
)
import requests
from config import VAPI_API_KEY


def get_recent_calls(assistant_id=None, limit=200, max_pages=5):
    """
    Get recent VAPI calls with pagination support
    
    Args:
        assistant_id: Optional assistant ID to filter by
        limit: Number of calls per page
        max_pages: Maximum number of pages to fetch
    
    Returns:
        list: List of call data dicts
    """
    base_url = "https://api.vapi.ai"
    
    print(f"🔍 Fetching recent calls...")
    if assistant_id:
        print(f"   Assistant ID: {assistant_id}")
    print(f"   Limit per page: {limit}, Max pages: {max_pages}")
    
    all_calls = []
    
    try:
        # Try different possible endpoints
        endpoints_to_try = [
            f"{base_url}/calls",
            f"{base_url}/call",
        ]
        
        for endpoint in endpoints_to_try:
            try:
                # Try pagination
                page = 1
                has_more = True
                
                while has_more and page <= max_pages:
                    # Try different parameter formats
                    params = {}
                    
                    # VAPI API might use different parameter names
                    if limit:
                        params['limit'] = limit
                    
                    # Try pagination parameters (if supported)
                    if page > 1:
                        params['page'] = page
                        params['offset'] = (page - 1) * limit
                    
                    if assistant_id:
                        params['assistantId'] = assistant_id
                    
                    response = requests.get(
                        endpoint,
                        headers={
                            "Authorization": f"Bearer {VAPI_API_KEY}",
                        },
                        params=params if params else None,  # Only send params if not empty
                        timeout=15
                    )
                    
                    if response.status_code == 200:
                        calls_data = response.json()
                        
                        # Handle different response structures
                        if isinstance(calls_data, dict):
                            calls = calls_data.get('calls', calls_data.get('data', calls_data.get('results', [])))
                            # Check if there's pagination info
                            has_more = calls_data.get('hasMore', False) or calls_data.get('next', None) is not None
                        elif isinstance(calls_data, list):
                            calls = calls_data
                            has_more = len(calls) == limit  # Assume more if we got full page
                        else:
                            calls = []
                            has_more = False
                        
                        all_calls.extend(calls)
                        print(f"   Page {page}: Found {len(calls)} calls (Total: {len(all_calls)})")
                        
                        if not has_more or len(calls) == 0:
                            break
                        
                        page += 1
                    elif response.status_code == 404:
                        break  # Endpoint doesn't exist
                    else:
                        print(f"   ⚠️  {endpoint} page {page} returned status {response.status_code}")
                        if page == 1:
                            break  # If first page fails, try next endpoint
                        else:
                            has_more = False  # Stop pagination
                
                if all_calls:
                    print(f"   ✅ Total: {len(all_calls)} calls from {endpoint}")
                    return all_calls
                    
            except Exception as e:
                print(f"   ⚠️  Error with {endpoint}: {e}")
                if all_calls:
                    return all_calls  # Return what we got so far
                continue
        
        if not all_calls:
            print(f"   ⚠️  Could not fetch calls from any endpoint")
        return all_calls
            
    except Exception as e:
        print(f"   ❌ Error fetching calls: {e}")
        return all_calls if all_calls else []


def filter_calls_by_date(calls, target_date):
    """
    Filter calls by date
    
    Args:
        calls: List of call dicts
        target_date: date object
    
    Returns:
        list: Filtered calls
    """
    filtered = []
    for call in calls:
        created_at = call.get('createdAt') or call.get('created_at') or call.get('created')
        if created_at:
            try:
                # Parse ISO format datetime
                if isinstance(created_at, str):
                    call_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    continue
                if call_date.date() == target_date:
                    filtered.append(call)
            except:
                pass
    return filtered


def match_call_to_customer(call, customer, debug=False):
    """
    Match a VAPI call to a customer by phone number
    
    Args:
        call: VAPI call data dict
        customer: Customer dict from Smartsheet
        debug: If True, print debug information
    
    Returns:
        bool: True if match, False otherwise
    """
    # Get phone numbers from both
    call_phone = None
    if isinstance(call.get('customer'), dict):
        call_phone = call.get('customer', {}).get('number')
    if not call_phone:
        call_phone = call.get('phoneNumber') or call.get('to') or call.get('customerNumber')
    
    customer_phone = customer.get('phone_number', '').strip()
    
    if debug:
        print(f"      Debug matching:")
        print(f"         Call phone: {call_phone}")
        print(f"         Customer phone: {customer_phone}")
    
    if not call_phone or not customer_phone:
        return False
    
    # Normalize phone numbers (remove spaces, dashes, etc.)
    def normalize_phone(phone):
        return ''.join(filter(str.isdigit, str(phone)))
    
    call_normalized = normalize_phone(call_phone)
    customer_normalized = normalize_phone(customer_phone)
    
    if debug:
        print(f"         Call normalized: {call_normalized}")
        print(f"         Customer normalized: {customer_normalized}")
    
    # Match if last 10 digits match (US phone numbers)
    if len(call_normalized) >= 10 and len(customer_normalized) >= 10:
        match = call_normalized[-10:] == customer_normalized[-10:]
        if debug:
            print(f"         Match: {match}")
        return match
    
    return False


def get_customers_for_date(smartsheet_service, target_date):
    """
    Get customers that should have been called on target_date
    
    Args:
        smartsheet_service: SmartsheetService instance
        target_date: date object
    
    Returns:
        list: List of customer dicts
    """
    print(f"\n📋 Getting customers for {target_date}...")
    
    # Get all customers
    all_customers = smartsheet_service.get_all_customers_with_stages()
    
    target_customers = []
    
    for customer in all_customers:
        # Check if f_u_date matches target_date
        f_u_date_str = customer.get('f_u_date', '').strip()
        if f_u_date_str:
            f_u_date = parse_date(f_u_date_str)
            if f_u_date == target_date:
                # Check if stage is 0 (should have been first call)
                stage = get_call_stage(customer)
                if stage == 0:
                    target_customers.append(customer)
    
    print(f"   Found {len(target_customers)} customers with f_u_date = {target_date} and stage = 0")
    
    return target_customers


def main():
    """Main function to fix Nov 12 records"""
    print("=" * 80)
    print("🔧 FIX NOVEMBER 12 CANCELLATION RECORDS")
    print("=" * 80)
    
    target_date = date(2025, 11, 12)
    print(f"\n📅 Target Date: {target_date}")
    
    # Initialize services
    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
    vapi_service = VAPIService()
    
    # Step 1: Get customers that should have been called
    target_customers = get_customers_for_date(smartsheet_service, target_date)
    
    if not target_customers:
        print("\n⚠️  No customers found for this date. They may have already been updated.")
        return
    
    print(f"\n📞 Customers to check:")
    for i, customer in enumerate(target_customers, 1):
        print(f"   {i}. {customer.get('company', 'Unknown')} - {customer.get('phone_number', 'N/A')}")
    
    # Step 2: Get VAPI calls for that date
    print(f"\n🔍 Fetching VAPI calls...")
    print("   Note: VAPI API may not support date filtering directly")
    print("   We'll fetch recent calls and filter by date")
    
    # Try multiple strategies to find calls
    print("\nStrategy 1: Get calls with Cancellation 1st Reminder Assistant ID...")
    recent_calls_1 = get_recent_calls(assistant_id=CANCELLATION_1ST_REMINDER_ASSISTANT_ID, limit=500)
    
    print("\nStrategy 2: Get ALL recent calls (no assistant filter)...")
    recent_calls_2 = get_recent_calls(assistant_id=None, limit=500)
    
    # Combine and deduplicate
    all_calls = {}
    for call in recent_calls_1 + recent_calls_2:
        call_id = call.get('id')
        if call_id and call_id not in all_calls:
            all_calls[call_id] = call
    
    recent_calls = list(all_calls.values())
    print(f"\n   Total unique calls found: {len(recent_calls)}")
    
    # Filter by date
    calls = filter_calls_by_date(recent_calls, target_date)
    
    print(f"\n   Calls on {target_date}: {len(calls)}")
    
    if calls:
        print(f"\n   Found calls on {target_date}:")
        for i, call in enumerate(calls, 1):
            call_id = call.get('id', 'N/A')
            created_at = call.get('createdAt', 'N/A')
            customer_info = call.get('customer', {})
            phone = customer_info.get('number', 'N/A') if isinstance(customer_info, dict) else 'N/A'
            name = customer_info.get('name', 'N/A') if isinstance(customer_info, dict) else 'N/A'
            assistant_id = call.get('assistantId', 'N/A')
            print(f"      {i}. Call ID: {call_id}")
            print(f"         Created: {created_at}")
            print(f"         Customer: {name}")
            print(f"         Phone: {phone}")
            print(f"         Assistant ID: {assistant_id}")
            
            # Try to find matching customer in Smartsheet
            all_customers = smartsheet_service.get_all_customers_with_stages()
            for customer in all_customers:
                if match_call_to_customer(call, customer, debug=False):
                    print(f"         ✅ MATCHED: {customer.get('company', 'Unknown')} (Row {customer.get('row_number', 'N/A')})")
                    break
    
    if not calls:
        print(f"\n⚠️  No calls found in VAPI for {target_date}.")
        print("   Options:")
        print("   1. Calls may be older than the recent calls limit (500)")
        print("   2. Calls may have been made with a different assistant ID")
        print("   3. You may need to check VAPI dashboard manually")
        print("\n   Let's try matching by phone number from all recent calls...")
        calls = recent_calls  # Use all recent calls to try matching
    
    print(f"\n📊 Found {len(calls)} calls to check")
    
    # Debug: Show call details
    if calls:
        print(f"\n📋 Sample call data (first call):")
        sample_call = calls[0]
        print(f"   Keys: {list(sample_call.keys())}")
        print(f"   Created At: {sample_call.get('createdAt', 'N/A')}")
        print(f"   Customer: {sample_call.get('customer', 'N/A')}")
        print(f"   Phone: {sample_call.get('phoneNumber', sample_call.get('to', 'N/A'))}")
        if len(calls) > 1:
            print(f"   ... and {len(calls) - 1} more calls")
    
    # Step 3: First, update any matched calls from the list above
    print(f"\n🔄 Step 3a: Updating matched calls from 11/12...")
    print("=" * 80)
    
    matched_calls_to_update = []
    all_customers_for_matching = smartsheet_service.get_all_customers_with_stages()
    
    for call in calls:
        call_id = call.get('id')
        if not call_id:
            continue
            
        # Find matching customer
        for customer in all_customers_for_matching:
            if match_call_to_customer(call, customer, debug=False):
                # Add to update list if call was made on target_date
                # (regardless of customer's f_u_date, since call was actually made)
                matched_calls_to_update.append({
                    'call': call,
                    'customer': customer,
                    'call_id': call_id
                })
                break
    
    print(f"\n   Found {len(matched_calls_to_update)} calls that match customers with f_u_date = {target_date}")
    
    # Step 4: Match calls to target customers and update
    print(f"\n🔄 Step 3b: Matching calls to target customers and updating Smartsheet...")
    print("=" * 80)
    
    updated_count = 0
    not_found_count = 0
    already_updated_count = 0
    
    # Update matched calls first
    for item in matched_calls_to_update:
        call = item['call']
        customer = item['customer']
        call_id = item['call_id']
        
        print(f"\n📋 Processing matched call: {customer.get('company', 'Unknown')}")
        print(f"   Call ID: {call_id}")
        
        # Get full call data if needed
        if not call.get('analysis'):
            call = vapi_service.check_call_status(call_id)
        
        if call and call.get('analysis'):
            try:
                current_stage = get_call_stage(customer)
                success = update_after_call(smartsheet_service, customer, call, current_stage)
                if success:
                    updated_count += 1
                else:
                    not_found_count += 1
            except Exception as e:
                print(f"   ❌ Exception: {e}")
                not_found_count += 1
    
    # Then process target customers
    for customer in target_customers:
        print(f"\n📋 Processing: {customer.get('company', 'Unknown')}")
        print(f"   Phone: {customer.get('phone_number', 'N/A')}")
        print(f"   Current Stage: {get_call_stage(customer)}")
        
        # Check if already updated (stage > 0)
        current_stage = get_call_stage(customer)
        if current_stage > 0:
            print(f"   ⏭️  Already updated (stage = {current_stage}), skipping")
            already_updated_count += 1
            continue
        
        # Find matching call
        matched_call = None
        for call in calls:
            if match_call_to_customer(call, customer, debug=True):
                # Get full call data
                call_id = call.get('id')
                if call_id:
                    print(f"   ✅ Found matching call: {call_id}")
                    matched_call = vapi_service.check_call_status(call_id)
                    if matched_call:
                        break
                else:
                    # If call already has full data, use it
                    if call.get('analysis'):
                        print(f"   ✅ Found matching call with analysis (no ID)")
                        matched_call = call
                        break
        
        if not matched_call:
            print(f"   ⚠️  No matching call found")
            not_found_count += 1
            continue
        
        # Check if call has analysis
        if not matched_call.get('analysis'):
            print(f"   ⚠️  Call found but no analysis available")
            print(f"      Status: {matched_call.get('status', 'N/A')}")
            print(f"      End Reason: {matched_call.get('endedReason', 'N/A')}")
            
            # Try to wait for analysis if call just ended
            if matched_call.get('status') == 'ended':
                print(f"      ⏳ Call ended, waiting for analysis...")
                matched_call = vapi_service.wait_for_call_completion(matched_call.get('id'))
        
        if matched_call and matched_call.get('analysis'):
            # Update Smartsheet
            print(f"   📝 Updating Smartsheet...")
            try:
                success = update_after_call(smartsheet_service, customer, matched_call, 0)
                if success:
                    print(f"   ✅ Successfully updated!")
                    updated_count += 1
                else:
                    print(f"   ❌ Update failed")
            except Exception as e:
                print(f"   ❌ Exception during update: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"   ⚠️  Cannot update - no analysis available")
            not_found_count += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"   ✅ Updated: {updated_count}")
    print(f"   ⏭️  Already updated: {already_updated_count}")
    print(f"   ❌ Not found/No analysis: {not_found_count}")
    print(f"   📊 Total processed: {len(target_customers)}")
    print("=" * 80)


if __name__ == "__main__":
    main()

