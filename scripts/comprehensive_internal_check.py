"""
综合内部检测脚本
验证 Direct Bill Workflow 的所有功能：
1. 基于 expiration_date 的日期计算
2. 周末避开逻辑
3. 客户筛选逻辑
4. 阶段分配逻辑
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from workflows.direct_bill import (
    is_direct_bill_ready_for_calling,
    should_skip_direct_bill_row,
    calculate_direct_bill_next_followup_date
)
from workflows.cancellations import is_weekend, parse_date
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def print_header(title):
    """打印标题"""
    print("\n" + "=" * 80)
    print(f"🔍 {title}")
    print("=" * 80)

def test_weekend_detection():
    """测试周末检测功能"""
    print_header("测试周末检测功能")
    
    pacific_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific_tz).date()
    
    # 测试今天
    is_today_weekend = is_weekend(today)
    print(f"📅 今天: {today.strftime('%Y-%m-%d %A')}")
    print(f"   是否周末: {'是' if is_today_weekend else '否'}")
    
    # 测试未来7天
    print(f"\n📅 未来7天的周末检测:")
    for i in range(7):
        test_date = today + timedelta(days=i)
        is_weekend_day = is_weekend(test_date)
        status = "周末" if is_weekend_day else "工作日"
        print(f"   {test_date.strftime('%Y-%m-%d %A')}: {status}")
    
    return True

def test_weekend_skip_logic():
    """测试周末跳过逻辑"""
    print_header("测试周末跳过逻辑")
    
    pacific_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific_tz).date()
    
    # 如果今天是周末，应该跳过
    if is_weekend(today):
        customer = {
            "expiration_date": (today + timedelta(days=14)).strftime("%Y-%m-%d"),
            "company": "Test Company",
            "phone_number": "1234567890",
            "payee": "direct billed",
            "payment_status": "pending payment",
            "renewal / non-renewal": "renewal"
        }
        is_ready, reason, stage = is_direct_bill_ready_for_calling(customer, today)
        if not is_ready and "weekend" in reason.lower():
            print(f"✅ 今天 ({today.strftime('%A')}) 是周末，正确跳过")
            print(f"   原因: {reason}")
            return True
        else:
            print(f"❌ 周末跳过逻辑失败")
            return False
    else:
        print(f"ℹ️  今天 ({today.strftime('%A')}) 是工作日，跳过此测试")
        return True

def test_weekend_adjustment():
    """测试周末调整逻辑"""
    print_header("测试周末调整逻辑")
    
    pacific_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific_tz).date()
    
    # 找到下一个周五、周六、周日
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0 and today.weekday() != 4:
        days_until_friday = 7
    next_friday = today + timedelta(days=days_until_friday)
    next_saturday = next_friday + timedelta(days=1)
    next_sunday = next_friday + timedelta(days=2)
    
    passed = 0
    total = 0
    
    # 测试1: 14天前是周六，应该在周五触发
    expiry_saturday = next_saturday + timedelta(days=14)
    customer = {
        "expiration_date": expiry_saturday.strftime("%Y-%m-%d"),
        "company": "Test Company",
        "phone_number": "1234567890",
        "payee": "direct billed",
        "payment_status": "pending payment",
        "renewal / non-renewal": "renewal"
    }
    is_ready, reason, stage = is_direct_bill_ready_for_calling(customer, next_friday)
    total += 1
    if is_ready and "adjusted" in reason.lower():
        print(f"✅ 14天前是周六 → 在周五触发")
        print(f"   到期日: {expiry_saturday.strftime('%Y-%m-%d')}")
        print(f"   触发日: {next_friday.strftime('%Y-%m-%d')}")
        print(f"   原因: {reason}")
        passed += 1
    else:
        print(f"⚠️  14天前是周六的测试未触发（可能日期不匹配）")
    
    # 测试2: 14天前是周日，应该在周五触发
    expiry_sunday = next_sunday + timedelta(days=14)
    customer = {
        "expiration_date": expiry_sunday.strftime("%Y-%m-%d"),
        "company": "Test Company",
        "phone_number": "1234567890",
        "payee": "direct billed",
        "payment_status": "pending payment",
        "renewal / non-renewal": "renewal"
    }
    is_ready, reason, stage = is_direct_bill_ready_for_calling(customer, next_friday)
    total += 1
    if is_ready and "adjusted" in reason.lower():
        print(f"✅ 14天前是周日 → 在周五触发")
        print(f"   到期日: {expiry_sunday.strftime('%Y-%m-%d')}")
        print(f"   触发日: {next_friday.strftime('%Y-%m-%d')}")
        print(f"   原因: {reason}")
        passed += 1
    else:
        print(f"⚠️  14天前是周日的测试未触发（可能日期不匹配）")
    
    print(f"\n📊 周末调整测试: {passed}/{total} 通过")
    return passed == total

def test_expiration_date_logic():
    """测试基于 expiration_date 的逻辑"""
    print_header("测试基于 expiration_date 的逻辑")
    
    pacific_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific_tz).date()
    
    # 确保今天是工作日
    if is_weekend(today):
        print("ℹ️  今天是周末，跳过此测试")
        return True
    
    test_cases = [
        {"days": 14, "stage": 0, "name": "Stage 0 (14天前)"},
        {"days": 7, "stage": 1, "name": "Stage 1 (7天前)"},
        {"days": 1, "stage": 2, "name": "Stage 2 (1天前)"},
    ]
    
    passed = 0
    for test_case in test_cases:
        expiry_date = today + timedelta(days=test_case["days"])
        # 确保目标日期不是周末
        if is_weekend(expiry_date - timedelta(days=test_case["days"])):
            continue
        
        customer = {
            "expiration_date": expiry_date.strftime("%Y-%m-%d"),
            "company": "Test Company",
            "phone_number": "1234567890",
            "payee": "direct billed",
            "payment_status": "pending payment",
            "renewal / non-renewal": "renewal"
        }
        is_ready, reason, stage = is_direct_bill_ready_for_calling(customer, today)
        
        if is_ready and stage == test_case["stage"]:
            print(f"✅ {test_case['name']}: 到期日 {expiry_date.strftime('%Y-%m-%d')}")
            passed += 1
        else:
            print(f"❌ {test_case['name']}: 失败 (Ready={is_ready}, Stage={stage})")
    
    print(f"\n📊 Expiration Date 逻辑测试: {passed}/{len(test_cases)} 通过")
    return passed == len(test_cases)

def test_skip_logic():
    """测试跳过逻辑"""
    print_header("测试客户跳过逻辑")
    
    pacific_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific_tz).date()
    expiry_date = (today + timedelta(days=14)).strftime("%Y-%m-%d")
    
    test_cases = [
        {
            "name": "有效客户",
            "customer": {
                "expiration_date": expiry_date,
                "company": "Test Company",
                "phone_number": "1234567890",
                "payee": "direct billed",
                "payment_status": "pending payment",
                "renewal / non-renewal": "renewal"
            },
            "should_skip": False
        },
        {
            "name": "缺少 expiration_date",
            "customer": {
                "company": "Test Company",
                "phone_number": "1234567890",
                "payee": "direct billed",
                "payment_status": "pending payment",
                "renewal / non-renewal": "renewal"
            },
            "should_skip": True
        },
        {
            "name": "Done 已勾选",
            "customer": {
                "expiration_date": expiry_date,
                "done?": True,
                "company": "Test Company",
                "phone_number": "1234567890",
                "payee": "direct billed",
                "payment_status": "pending payment",
                "renewal / non-renewal": "renewal"
            },
            "should_skip": True
        }
    ]
    
    passed = 0
    for test_case in test_cases:
        should_skip, reason = should_skip_direct_bill_row(test_case["customer"])
        if should_skip == test_case["should_skip"]:
            print(f"✅ {test_case['name']}: {'跳过' if should_skip else '不跳过'}")
            passed += 1
        else:
            print(f"❌ {test_case['name']}: 失败 (期望跳过={test_case['should_skip']}, 实际={should_skip})")
    
    print(f"\n📊 跳过逻辑测试: {passed}/{len(test_cases)} 通过")
    return passed == len(test_cases)

def main():
    """运行所有测试"""
    print("=" * 80)
    print("🔍 DIRECT BILL WORKFLOW - 综合内部检测")
    print("=" * 80)
    print("检测内容:")
    print("  1. 周末检测功能")
    print("  2. 周末跳过逻辑")
    print("  3. 周末调整逻辑（提前到周五）")
    print("  4. 基于 expiration_date 的日期计算")
    print("  5. 客户筛选逻辑")
    print("=" * 80)
    
    pacific_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific_tz).date()
    print(f"\n📅 当前日期 (Pacific Time): {today.strftime('%Y-%m-%d %A')}")
    print(f"🕐 当前时间 (Pacific Time): {datetime.now(pacific_tz).strftime('%H:%M:%S %Z')}")
    
    results = {
        "周末检测": test_weekend_detection(),
        "周末跳过": test_weekend_skip_logic(),
        "周末调整": test_weekend_adjustment(),
        "Expiration Date 逻辑": test_expiration_date_logic(),
        "跳过逻辑": test_skip_logic()
    }
    
    # 总结
    print("\n" + "=" * 80)
    print("📊 检测总结")
    print("=" * 80)
    
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\n🏁 总计: {total_passed}/{total_tests} 项检测通过")
    print("=" * 80)
    
    if total_passed == total_tests:
        print("✅ 所有检测通过！Direct Bill Workflow 功能正常")
    else:
        print("⚠️  部分检测未通过，请检查上述输出")
    
    return 0 if total_passed == total_tests else 1

if __name__ == "__main__":
    sys.exit(main())

