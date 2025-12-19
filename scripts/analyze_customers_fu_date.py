"""
分析指定 F/U Date 的客户，查看为什么有些没有被打
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services import SmartsheetService
from config import CANCELLATION_SHEET_ID
from workflows.cancellations import (
    parse_date, 
    get_call_stage, 
    count_business_days,
    get_assistant_id_for_stage
)
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

def analyze_customers_by_fu_date(target_date_str):
    """
    分析指定 F/U Date 的所有客户，详细说明为什么有些没有被打
    """
    target_date = parse_date(target_date_str)
    if not target_date:
        print(f"❌ 无效的日期格式: {target_date_str}")
        return
    
    print("=" * 100)
    print(f"📊 分析 F/U Date = {target_date} 的所有客户")
    print("=" * 100)
    
    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
    all_customers = smartsheet_service.get_all_customers_with_stages()
    
    pacific_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific_tz).date()
    
    matching_customers = []
    
    # 找到所有匹配的客户
    for customer in all_customers:
        followup_date_str = customer.get('f_u_date', '')
        if not followup_date_str.strip():
            continue
        
        followup_date = parse_date(followup_date_str)
        if not followup_date:
            continue
        
        if followup_date == target_date:
            matching_customers.append(customer)
    
    print(f"\n找到 {len(matching_customers)} 个 F/U Date = {target_date} 的客户\n")
    
    # 分类分析
    expired_customers = []  # 已过期 (Cancellation Date <= F/U Date)
    non_expired_customers = []  # 未过期 (Cancellation Date > F/U Date)
    no_cancel_date = []  # 没有 Cancellation Date
    
    for customer in matching_customers:
        cancellation_date_str = customer.get('cancellation_date', '')
        if not cancellation_date_str.strip():
            no_cancel_date.append(customer)
        else:
            cancellation_date = parse_date(cancellation_date_str)
            if cancellation_date:
                if cancellation_date <= target_date:
                    expired_customers.append(customer)
                else:
                    non_expired_customers.append(customer)
            else:
                no_cancel_date.append(customer)
    
    print("=" * 100)
    print("📋 客户分类:")
    print(f"   1. 已过期客户 (Cancellation Date <= {target_date}): {len(expired_customers)} 个")
    print(f"   2. 未过期客户 (Cancellation Date > {target_date}): {len(non_expired_customers)} 个")
    print(f"   3. 无 Cancellation Date: {len(no_cancel_date)} 个")
    print("=" * 100)
    
    # 分析已过期客户（应该用 manual_cl1_calling.py）
    print("\n" + "=" * 100)
    print("🔴 已过期客户分析 (应该用 manual_cl1_calling.py 拨打):")
    print("=" * 100)
    
    for i, customer in enumerate(expired_customers, 1):
        row_num = customer.get('row_number', 'N/A')
        company = customer.get('company', 'Unknown') or customer.get('insured', 'Unknown')
        phone = customer.get('phone_number', 'N/A')
        cancellation_date_str = customer.get('cancellation_date', '')
        amount_due = customer.get('amount_due', '')
        done = customer.get('done?', False)
        current_stage = get_call_stage(customer)
        
        cancellation_date = parse_date(cancellation_date_str)
        days_expired = (target_date - cancellation_date).days if cancellation_date else 0
        
        print(f"\n{i}. 行 {row_num}: {company}")
        print(f"   电话: {phone}")
        print(f"   Cancellation Date: {cancellation_date_str} (已过期 {days_expired} 天)")
        print(f"   Amount Due: {amount_due}")
        print(f"   Current Stage: {current_stage}")
        print(f"   Done?: {done}")
        
        # 检查为什么会被跳过
        reasons = []
        if done in [True, 'true', 'True', 1]:
            reasons.append("❌ Done? = True")
        if not amount_due or not amount_due.strip():
            reasons.append("❌ Amount Due 为空")
        if current_stage >= 3:
            reasons.append(f"❌ Current Stage ({current_stage}) >= 3 (已完成所有电话)")
        
        if reasons:
            print(f"   ⚠️  会被跳过，原因: {', '.join(reasons)}")
        else:
            print(f"   ✅ 应该会被拨打 (使用 manual_cl1_calling.py)")
    
    # 分析未过期客户（应该用 call_non_expired_cl1.py）
    print("\n" + "=" * 100)
    print("🟢 未过期客户分析 (应该用 call_non_expired_cl1.py 拨打):")
    print("=" * 100)
    
    for i, customer in enumerate(non_expired_customers, 1):
        row_num = customer.get('row_number', 'N/A')
        company = customer.get('company', 'Unknown') or customer.get('insured', 'Unknown')
        phone = customer.get('phone_number', 'N/A')
        cancellation_date_str = customer.get('cancellation_date', '')
        amount_due = customer.get('amount_due', '')
        done = customer.get('done?', False)
        current_stage = get_call_stage(customer)
        
        cancellation_date = parse_date(cancellation_date_str)
        business_days = count_business_days(target_date, cancellation_date) if cancellation_date else 0
        
        # 计算应该的 stage
        expected_stage = -1
        if business_days >= 12:
            expected_stage = 0
        elif business_days >= 5:
            expected_stage = 1
        elif business_days >= 1:
            expected_stage = 2
        
        print(f"\n{i}. 行 {row_num}: {company}")
        print(f"   电话: {phone}")
        print(f"   Cancellation Date: {cancellation_date_str} (距离 {business_days} 工作日)")
        print(f"   Amount Due: {amount_due}")
        print(f"   Current Stage: {current_stage}")
        print(f"   Expected Stage: {expected_stage} (基于 {business_days} 工作日)")
        print(f"   Done?: {done}")
        
        # 检查为什么会被跳过
        reasons = []
        if done in [True, 'true', 'True', 1]:
            reasons.append("❌ Done? = True")
        if not amount_due or not amount_due.strip():
            reasons.append("❌ Amount Due 为空")
        if expected_stage == -1:
            reasons.append(f"❌ F/U Date 距离 Cancellation Date 太近 ({business_days} 工作日)")
        if current_stage > expected_stage:
            reasons.append(f"❌ Current Stage ({current_stage}) > Expected Stage ({expected_stage})")
        if current_stage >= 3:
            reasons.append(f"❌ Current Stage ({current_stage}) >= 3 (已完成所有电话)")
        
        if reasons:
            print(f"   ⚠️  会被跳过，原因: {', '.join(reasons)}")
        else:
            print(f"   ✅ 应该会被拨打 (Stage {expected_stage})")
    
    # 分析无 Cancellation Date 的客户
    if no_cancel_date:
        print("\n" + "=" * 100)
        print("🟡 无 Cancellation Date 的客户:")
        print("=" * 100)
        
        for i, customer in enumerate(no_cancel_date, 1):
            row_num = customer.get('row_number', 'N/A')
            company = customer.get('company', 'Unknown') or customer.get('insured', 'Unknown')
            phone = customer.get('phone_number', 'N/A')
            print(f"{i}. 行 {row_num}: {company} - {phone}")
            print(f"   ❌ 没有 Cancellation Date，无法判断是否过期")
    
    print("\n" + "=" * 100)
    print("📊 总结:")
    print("=" * 100)
    print(f"   总客户数: {len(matching_customers)}")
    print(f"   已过期且应该拨打: {sum(1 for c in expired_customers if c.get('done?') not in [True, 'true', 'True', 1] and c.get('amount_due', '').strip() and get_call_stage(c) < 3)}")
    print(f"   未过期且应该拨打: {sum(1 for c in non_expired_customers if c.get('done?') not in [True, 'true', 'True', 1] and c.get('amount_due', '').strip())}")
    print("=" * 100)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        target_date_str = sys.argv[1]
    else:
        # 默认使用今天的日期
        pacific_tz = ZoneInfo("America/Los_Angeles")
        today = datetime.now(pacific_tz).date()
        target_date_str = today.strftime('%Y-%m-%d')
    
    analyze_customers_by_fu_date(target_date_str)





