#!/usr/bin/env python3
"""
查找一个有完整数据的客户用于测试
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflows.renewals import get_current_renewal_sheet


def find_test_customer():
    """查找一个有完整数据的客户"""
    print("=" * 80)
    print("🔍 查找测试客户")
    print("=" * 80)
    
    smartsheet_service = get_current_renewal_sheet()
    all_customers = smartsheet_service.get_all_customers_with_stages()
    
    print(f"\n✅ 加载了 {len(all_customers)} 条客户记录")
    
    # 查找有完整数据的客户
    candidates = []
    for customer in all_customers:
        has_company = customer.get('company', '').strip()
        has_phone = customer.get('client_phone_number', '') or customer.get('phone_number', '')
        has_premium = customer.get('offered_premium', '') or customer.get('Offered Premium', '')
        has_first_name = customer.get('first_name', '') or customer.get('First Name', '')
        has_last_name = customer.get('last_name', '') or customer.get('Last Name', '')
        has_lob = customer.get('lob', '') or customer.get('LOB', '')
        has_expiration = customer.get('expiration_date', '') or customer.get('expiration date', '')
        
        if has_company and has_phone and has_premium and has_first_name and has_last_name and has_lob and has_expiration:
            candidates.append(customer)
    
    print(f"\n📊 找到 {len(candidates)} 个有完整数据的客户")
    
    if candidates:
        # 显示前5个
        print("\n前5个候选客户:")
        print("=" * 80)
        for i, customer in enumerate(candidates[:5], 1):
            print(f"\n{i}. Row {customer.get('row_number', 'N/A')}:")
            print(f"   公司: {customer.get('company', 'N/A')}")
            print(f"   电话: {customer.get('client_phone_number', 'N/A')}")
            print(f"   First Name: {customer.get('first_name', 'N/A')}")
            print(f"   Last Name: {customer.get('last_name', 'N/A')}")
            print(f"   LOB: {customer.get('lob', 'N/A')}")
            print(f"   Expiration Date: {customer.get('expiration_date', 'N/A')}")
            print(f"   Offered Premium: {customer.get('offered_premium', 'N/A')}")
        
        # 返回第一个
        return candidates[0]
    else:
        print("\n⚠️  没有找到有完整数据的客户")
        return None


if __name__ == "__main__":
    customer = find_test_customer()
    if customer:
        print(f"\n✅ 推荐测试客户: Row {customer.get('row_number', 'N/A')} - {customer.get('company', 'N/A')}")

