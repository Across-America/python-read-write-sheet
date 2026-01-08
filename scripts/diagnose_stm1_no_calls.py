"""
诊断STM1 GitHub Actions启动但没有拨打电话的问题
"""
import sys
import os
from pathlib import Path

# Fix Windows encoding issue
if sys.platform == 'win32':
    import io
    if not isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if not isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from zoneinfo import ZoneInfo
from workflows.stm1 import get_stm1_sheet, get_stm1_customers_ready_for_calls
from scripts.auto_stm1_calling import get_customers_with_empty_called_times
from services import VAPIService
from config import (
    STM1_ASSISTANT_ID,
    STM1_PHONE_NUMBER_ID,
    STM1_CALLING_START_HOUR,
    STM1_CALLING_END_HOUR
)

def diagnose():
    """诊断为什么没有拨打电话"""
    print("=" * 80)
    print("诊断STM1 GitHub Actions启动但没有拨打电话的问题")
    print("=" * 80)
    print()
    
    pacific_tz = ZoneInfo("America/Los_Angeles")
    now = datetime.now(pacific_tz)
    today = now.date()
    
    print(f"当前时间: {now.strftime('%Y-%m-%d %I:%M %p %Z')}")
    print(f"今天日期: {today}")
    print()
    
    # 检查1: 时间检查
    print("=" * 80)
    print("1. 时间检查")
    print("=" * 80)
    current_hour = now.hour
    current_minute = now.minute
    
    print(f"   当前时间: {current_hour}:{current_minute:02d}")
    print(f"   调用时间: {STM1_CALLING_START_HOUR}:00 AM - {STM1_CALLING_END_HOUR}:00 PM Pacific Time")
    
    within_hours = (STM1_CALLING_START_HOUR <= current_hour < STM1_CALLING_END_HOUR and 
                    not (current_hour == STM1_CALLING_END_HOUR - 1 and current_minute >= 55))
    
    if within_hours:
        print(f"   ✅ 在调用时间内")
    else:
        if current_hour < STM1_CALLING_START_HOUR:
            print(f"   ❌ 问题: 还未到调用时间 (需要等到 {STM1_CALLING_START_HOUR}:00 AM)")
            print(f"   → 脚本会等待，但GitHub Actions可能超时")
        elif current_hour >= STM1_CALLING_END_HOUR:
            print(f"   ❌ 问题: 已过调用时间 (调用时间已结束)")
        else:
            print(f"   ❌ 问题: 太接近结束时间 (4:55 PM之后)")
    
    # 检查2: 客户列表 - called_times为空或0
    print("\n" + "=" * 80)
    print("2. 检查待调用客户 (called_times=0或空)")
    print("=" * 80)
    try:
        service = get_stm1_sheet()
        customers_empty = get_customers_with_empty_called_times(service)
        print(f"   找到: {len(customers_empty)} 个客户")
        
        if len(customers_empty) == 0:
            print(f"   ❌ 问题: 没有待调用客户!")
            print(f"   → 脚本会在3次检查后退出 (MAX_NO_CUSTOMERS = 3)")
            print(f"   → 每次检查间隔5分钟，总共15分钟后退出")
        else:
            print(f"   ✅ 找到 {len(customers_empty)} 个待调用客户")
            if customers_empty:
                print(f"   前5个客户:")
                for i, customer in enumerate(customers_empty[:5], 1):
                    row_num = customer.get('row_number', 'N/A')
                    company = customer.get('insured_name_', '') or customer.get('insured_name', '') or customer.get('company', 'Unknown')
                    phone = customer.get('phone_number', '') or customer.get('contact_phone', '')
                    print(f"      {i}. Row {row_num}: {company} - {phone}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 检查3: 客户列表 - ready for calls (使用is_stm1_ready_for_calling逻辑)
    print("\n" + "=" * 80)
    print("3. 检查今天可调用客户 (ready for calls)")
    print("=" * 80)
    try:
        ready_customers = get_stm1_customers_ready_for_calls(service)
        print(f"   找到: {len(ready_customers)} 个今天可调用客户")
        
        if len(ready_customers) == 0:
            print(f"   ⚠️  注意: 没有今天可调用的客户")
            print(f"   → 可能原因:")
            print(f"      - 所有客户今天都已经调用过")
            print(f"      - 所有客户都有called_times > 0")
            print(f"      - 所有客户都被其他条件过滤掉了")
        else:
            print(f"   ✅ 找到 {len(ready_customers)} 个今天可调用客户")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 检查4: VAPI服务配置
    print("\n" + "=" * 80)
    print("4. 检查VAPI配置")
    print("=" * 80)
    if STM1_ASSISTANT_ID:
        print(f"   ✅ STM1_ASSISTANT_ID: {STM1_ASSISTANT_ID[:20]}...")
    else:
        print(f"   ❌ STM1_ASSISTANT_ID: 未配置")
    
    if STM1_PHONE_NUMBER_ID:
        print(f"   ✅ STM1_PHONE_NUMBER_ID: {STM1_PHONE_NUMBER_ID[:20]}...")
    else:
        print(f"   ❌ STM1_PHONE_NUMBER_ID: 未配置")
    
    # 检查5: 测试VAPI连接
    print("\n" + "=" * 80)
    print("5. 测试VAPI连接")
    print("=" * 80)
    try:
        vapi_service = VAPIService(phone_number_id=STM1_PHONE_NUMBER_ID)
        recent_calls = vapi_service.get_recent_calls(limit=5)
        print(f"   ✅ VAPI连接正常")
        print(f"   最近5次调用: {len(recent_calls)} 条记录")
    except Exception as e:
        print(f"   ❌ VAPI连接失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 总结
    print("\n" + "=" * 80)
    print("诊断总结")
    print("=" * 80)
    
    issues = []
    if not within_hours:
        issues.append("时间不在调用窗口内")
    if len(customers_empty) == 0:
        issues.append("没有待调用客户 (called_times=0或空)")
    if len(ready_customers) == 0:
        issues.append("没有今天可调用的客户")
    
    if issues:
        print("发现的问题:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        print()
        print("可能的原因:")
        if "时间不在调用窗口内" in issues:
            print("   - GitHub Actions在UTC 16:00或17:00运行，但脚本会检查Pacific时间")
            print("   - 如果Pacific时间不在9 AM - 5 PM，脚本会等待或退出")
        if "没有待调用客户" in issues:
            print("   - 所有客户的called_times都已>0")
            print("   - 脚本会在3次检查后退出 (每次间隔5分钟)")
        if "没有今天可调用的客户" in issues:
            print("   - 所有客户今天都已经调用过")
            print("   - 或者所有客户都被过滤条件排除了")
    else:
        print("✅ 所有检查都通过，理论上应该可以拨打电话")
        print("   如果仍然没有拨打电话，可能的原因:")
        print("   1. GitHub Actions日志中有错误信息")
        print("   2. VAPI API调用失败但没有正确报告错误")
        print("   3. 脚本在等待过程中被GitHub Actions超时终止")
    
    print("=" * 80)

if __name__ == "__main__":
    diagnose()
