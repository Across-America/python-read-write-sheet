#!/usr/bin/env python3
"""
验证脚本 - 检查传递给 VAPI 的所有变量值
特别是 first message 中使用的变量
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflows.renewals import get_current_renewal_sheet
from services.vapi_service import format_amount_for_speech, format_date_for_speech


def verify_variables():
    """验证传递给 VAPI 的变量值"""
    print("=" * 80)
    print("🔍 验证传递给 VAPI 的变量值")
    print("=" * 80)
    
    # 初始化服务
    print("\n📋 初始化服务...")
    try:
        smartsheet_service = get_current_renewal_sheet()
        print("✅ 服务初始化成功")
    except Exception as e:
        print(f"❌ 服务初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 获取 Row 343 (Rick insurance)
    print("\n📋 加载客户数据...")
    all_customers = smartsheet_service.get_all_customers_with_stages()
    print(f"✅ 加载了 {len(all_customers)} 条客户记录")
    
    # 查找 Row 343
    target_row_number = 343
    test_customer = None
    
    for customer in all_customers:
        if customer.get('row_number') == target_row_number:
            test_customer = customer
            break
    
    if not test_customer:
        print(f"\n⚠️  没有找到 Row {target_row_number}")
        return
    
    print(f"\n✅ 找到 Row {target_row_number}: {test_customer.get('company', 'Unknown')}")
    
    # 模拟 vapi_service 中的变量准备逻辑
    print("\n" + "=" * 80)
    print("📋 模拟变量准备过程:")
    print("=" * 80)
    
    first_customer = test_customer
    
    # Get offered_premium
    offered_premium = first_customer.get('offered_premium', '') or first_customer.get('Offered Premium', '')
    print(f"\n1. Offered Premium:")
    print(f"   原始值: {offered_premium}")
    
    renewal_payment = ''
    if offered_premium:
        renewal_payment = format_amount_for_speech(offered_premium)
        print(f"   格式化后: {renewal_payment}")
    else:
        print(f"   (空)")
    
    # Get expiration date
    expiration_date_str = first_customer.get('expiration_date', '') or first_customer.get('expiration date', '')
    print(f"\n2. Expiration Date:")
    print(f"   原始值: {expiration_date_str}")
    
    expiration_date_formatted = format_date_for_speech(expiration_date_str) if expiration_date_str else ''
    if expiration_date_formatted:
        print(f"   格式化后: {expiration_date_formatted}")
    else:
        print(f"   (空)")
    
    # 准备所有变量
    variable_values = {
        "company": first_customer.get('company', 'Customer'),
        "Company": first_customer.get('company', 'Customer'),
        "First Name": first_customer.get('first_name', '') or first_customer.get('First Name', ''),
        "first_name": first_customer.get('first_name', '') or first_customer.get('First Name', ''),
        "Last Name": first_customer.get('last_name', '') or first_customer.get('Last Name', ''),
        "last_name": first_customer.get('last_name', '') or first_customer.get('Last Name', ''),
        "LOB": first_customer.get('lob', '') or first_customer.get('LOB', ''),
        "lob": first_customer.get('lob', '') or first_customer.get('LOB', ''),
        "Expiration Date": expiration_date_formatted,
        "expiration_date": expiration_date_formatted,
        "renewal_payment": renewal_payment,
        "renewal payment": renewal_payment
    }
    
    print("\n" + "=" * 80)
    print("📋 所有变量值 (将传递给 VAPI):")
    print("=" * 80)
    
    # 显示 first message 中使用的关键变量
    print("\n🎯 First Message 中使用的变量:")
    print("-" * 80)
    first_message_vars = {
        "First Name": variable_values.get('First Name', ''),
        "Last Name": variable_values.get('Last Name', ''),
        "LOB": variable_values.get('LOB', ''),
        "Company": variable_values.get('Company', ''),
        "Expiration Date": variable_values.get('Expiration Date', ''),
        "renewal payment": variable_values.get('renewal payment', '')
    }
    
    for key, value in first_message_vars.items():
        if value:
            print(f"  {{{{{key}}}}}: '{value}'")
        else:
            print(f"  {{{{{key}}}}}: (空) ⚠️")
    
    print("\n" + "-" * 80)
    print("📋 所有变量 (完整列表):")
    print("-" * 80)
    for key, value in sorted(variable_values.items()):
        if value:
            print(f"  {key:25s}: '{value}'")
        else:
            print(f"  {key:25s}: (空)")
    
    # 测试 first message 模板替换
    print("\n" + "=" * 80)
    print("🧪 First Message 模板替换测试:")
    print("=" * 80)
    
    first_message_template = """Hello {{First Name}} {{Last Name}}, this is Harry calling from All Solutions Insurance Agency. I'm reaching out about your {{LOB}} with {{Company}}, which is scheduled to renew on {{Expiration Date}}. This is a friendly reminder to please make your renewal payment so your coverage continues without interruption. If payment isn't received by the renewal date, your policy will not renew and your insurance may lapse. You can make your payment directly on your insurance carrier's website, or if you'd like help, I can connect you with one of our representatives to assist you right now. Would you like to speak with someone to process your payment?"""
    
    # 替换变量
    test_message = first_message_template
    test_message = test_message.replace("{{First Name}}", variable_values.get('First Name', '{{First Name}}'))
    test_message = test_message.replace("{{Last Name}}", variable_values.get('Last Name', '{{Last Name}}'))
    test_message = test_message.replace("{{LOB}}", variable_values.get('LOB', '{{LOB}}'))
    test_message = test_message.replace("{{Company}}", variable_values.get('Company', '{{Company}}'))
    test_message = test_message.replace("{{Expiration Date}}", variable_values.get('Expiration Date', '{{Expiration Date}}'))
    
    print("\n原始模板:")
    print("-" * 80)
    print(first_message_template)
    print("-" * 80)
    
    print("\n替换后的消息:")
    print("-" * 80)
    print(test_message)
    print("-" * 80)
    
    # 检查是否有未替换的变量
    import re
    remaining_vars = re.findall(r'\{\{([^}]+)\}\}', test_message)
    if remaining_vars:
        print(f"\n⚠️  警告: 以下变量未被替换: {remaining_vars}")
    else:
        print("\n✅ 所有变量都已成功替换！")


if __name__ == "__main__":
    verify_variables()

