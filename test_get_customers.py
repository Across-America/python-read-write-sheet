#!/usr/bin/env python3
"""
Test script to inspect get_not_called_customers() output
Shows detailed customer data from Smartsheet
"""

import json
import sys
from services.smartsheet_service import SmartsheetService
from config.settings import CANCELLATION_DEV_2_SHEET_ID

def main():
    """Main test function"""
    print("=" * 80)
    print("🧪 TESTING SmartsheetService.get_not_called_customers()")
    print("=" * 80)
    print()
    
    # Initialize SmartsheetService
    print(f"📋 Using Sheet ID: {CANCELLATION_DEV_2_SHEET_ID}")
    service = SmartsheetService(sheet_id=CANCELLATION_DEV_2_SHEET_ID)
    
    # Get customers with "Not call yet" status
    print("\n🔄 Fetching customers...")
    customers = service.get_not_called_customers()
    
    # Display results
    print("\n" + "=" * 80)
    print(f"📊 RESULTS: Found {len(customers)} customer(s)")
    print("=" * 80)
    
    if not customers:
        print("\n⚠️  No customers with 'Not call yet' status found.")
        print("   This could mean:")
        print("   - All customers have been called")
        print("   - The sheet is empty")
        print("   - The 'Call Status' column doesn't contain 'Not call yet'")
        return
    
    # Display each customer in detail
    for i, customer in enumerate(customers, 1):
        print(f"\n{'─' * 80}")
        print(f"👤 Customer #{i}")
        print(f"{'─' * 80}")
        
        # Core fields
        print(f"  🆔 Client ID:      {customer.get('client_id', 'N/A')}")
        print(f"  📋 Policy Number:  {customer.get('policy_number', 'N/A')}")
        print(f"  📞 Phone Number:   {customer.get('phone_number', 'N/A')}")
        print(f"  📍 Call Status:    {customer.get('call_status', 'N/A')}")
        print(f"  🔢 Row Number:     {customer.get('row_number', 'N/A')}")
        print(f"  🔑 Row ID:         {customer.get('row_id', 'N/A')}")
        
        # Additional fields (if present)
        additional_fields = [
            'agent_name', 'office', 'insured', 'lob', 'status',
            'cancellation_reason', 'cancellation_date'
        ]
        
        has_additional = any(customer.get(field) for field in additional_fields)
        if has_additional:
            print(f"\n  📝 Additional Info:")
            for field in additional_fields:
                value = customer.get(field, '')
                if value:
                    label = field.replace('_', ' ').title()
                    print(f"     • {label}: {value}")
    
    # JSON dump for programmatic use
    print(f"\n{'=' * 80}")
    print("📄 RAW JSON OUTPUT")
    print("=" * 80)
    print(json.dumps(customers, indent=2, ensure_ascii=False))
    
    # Summary statistics
    print(f"\n{'=' * 80}")
    print("📈 SUMMARY STATISTICS")
    print("=" * 80)
    print(f"  Total customers:     {len(customers)}")
    
    # Count unique values
    unique_agents = set(c.get('agent_name', '') for c in customers if c.get('agent_name'))
    unique_offices = set(c.get('office', '') for c in customers if c.get('office'))
    unique_lobs = set(c.get('lob', '') for c in customers if c.get('lob'))
    
    if unique_agents:
        print(f"  Unique agents:       {len(unique_agents)}")
    if unique_offices:
        print(f"  Unique offices:      {len(unique_offices)}")
    if unique_lobs:
        print(f"  Unique LOBs:         {len(unique_lobs)}")
    
    print("\n✅ Test completed successfully!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
