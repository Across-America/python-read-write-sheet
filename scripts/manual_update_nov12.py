#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manual Update November 12 Cancellation Records
This script allows you to manually provide call IDs to update Smartsheet records
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
from services import VAPIService, SmartsheetService
from config import CANCELLATION_SHEET_ID
from workflows.cancellations import (
    get_call_stage,
    update_after_call,
    parse_date
)


def main():
    """Main function to manually update Nov 12 records"""
    print("=" * 80)
    print("MANUAL UPDATE NOVEMBER 12 CANCELLATION RECORDS")
    print("=" * 80)
    
    target_date = date(2025, 11, 12)
    print(f"\nTarget Date: {target_date}")
    
    # Initialize services
    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
    vapi_service = VAPIService()
    
    # Step 1: Get customers that should have been called
    print(f"\nGetting customers for {target_date}...")
    all_customers = smartsheet_service.get_all_customers_with_stages()
    
    target_customers = []
    for customer in all_customers:
        f_u_date_str = customer.get('f_u_date', '').strip()
        if f_u_date_str:
            f_u_date = parse_date(f_u_date_str)
            if f_u_date == target_date:
                stage = get_call_stage(customer)
                if stage == 0:
                    target_customers.append(customer)
    
    if not target_customers:
        print("\nNo customers found for this date.")
        return
    
    print(f"\nFound {len(target_customers)} customers:")
    for i, customer in enumerate(target_customers, 1):
        print(f"  {i}. {customer.get('company', 'Unknown')} - {customer.get('phone_number', 'N/A')} - Stage: {get_call_stage(customer)}")
    
    # Step 2: Get call IDs
    print(f"\n" + "=" * 80)
    print("Please provide call IDs from VAPI dashboard")
    print("You can find call IDs at: https://dashboard.vapi.ai")
    print("=" * 80)
    
    call_id_mapping = {}
    
    for customer in target_customers:
        company = customer.get('company', 'Unknown')
        phone = customer.get('phone_number', 'N/A')
        
        print(f"\nCustomer: {company}")
        print(f"Phone: {phone}")
        
        call_id = input(f"Enter call ID for this customer (or press Enter to skip): ").strip()
        
        if call_id:
            call_id_mapping[company] = {
                'customer': customer,
                'call_id': call_id
            }
    
    if not call_id_mapping:
        print("\nNo call IDs provided. Exiting.")
        return
    
    # Step 3: Update Smartsheet
    print(f"\n" + "=" * 80)
    print("Updating Smartsheet...")
    print("=" * 80)
    
    updated_count = 0
    failed_count = 0
    
    for company, mapping in call_id_mapping.items():
        customer = mapping['customer']
        call_id = mapping['call_id']
        
        print(f"\nProcessing: {company}")
        print(f"  Call ID: {call_id}")
        
        # Get call data from VAPI
        call_data = vapi_service.check_call_status(call_id)
        
        if not call_data:
            print(f"  ERROR: Could not fetch call data")
            failed_count += 1
            continue
        
        # Check if call has analysis
        if not call_data.get('analysis'):
            print(f"  WARNING: No analysis found. Status: {call_data.get('status', 'N/A')}")
            print(f"  Waiting for analysis...")
            
            # Try to wait for analysis
            call_data = vapi_service.wait_for_call_completion(call_id)
            
            if not call_data or not call_data.get('analysis'):
                print(f"  ERROR: Still no analysis available")
                failed_count += 1
                continue
        
        # Update Smartsheet
        print(f"  Updating Smartsheet...")
        try:
            success = update_after_call(smartsheet_service, customer, call_data, 0)
            if success:
                print(f"  SUCCESS: Updated!")
                updated_count += 1
            else:
                print(f"  ERROR: Update failed")
                failed_count += 1
        except Exception as e:
            print(f"  ERROR: Exception during update: {e}")
            import traceback
            traceback.print_exc()
            failed_count += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Updated: {updated_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Total: {len(call_id_mapping)}")
    print("=" * 80)


if __name__ == "__main__":
    main()

