"""
⭐ 重要脚本 ⭐
拨打 F/U Date 指定的未过期保单和过期后的保单
根据距离 Cancellation Date 的天数（14、7、1天前）分配对应的 CL1 assistant ID
对于过期后的保单（Expiration Date过了一天之后），使用专门的 assistant ID

功能：
- 查找指定 F/U Date 的未过期保单（Cancellation Date > F/U Date）
- 根据 F/U Date 距离 Cancellation Date 的工作日数分组：
  * 14天前 → Stage 0 (第1次提醒) → CANCELLATION_1ST_REMINDER_ASSISTANT_ID
  * 7天前 → Stage 1 (第2次提醒) → CANCELLATION_2ND_REMINDER_ASSISTANT_ID
  * 1天前 → Stage 2 (第3次提醒) → CANCELLATION_3RD_REMINDER_ASSISTANT_ID
- 查找过期后的保单（Expiration Date过了一天之后）：
  * 使用专门的过期后 assistant ID: aec4721c-360c-45b5-ba39-87320eab6fc9
- Stage 0: 批量拨打（同时拨打所有客户）
- Stage 1 & 2: 顺序拨打（一次一个客户）
- 过期后保单: 批量拨打（同时拨打所有客户）
- 自动更新 Smartsheet（AI Call Summary, Stage, F/U Date）

使用方法:
    python scripts/call_non_expired_cl1.py
    或
    python scripts/call_non_expired_cl1.py --date 2025-12-08
    或
    python scripts/call_non_expired_cl1.py --date 2025-12-08 --yes  # 自动确认，不询问

参数:
    --date, -d: 指定 F/U Date (格式: YYYY-MM-DD)
    --yes, -y: 自动确认，不询问用户

注意:
    - 如果没有指定日期，脚本会提示用户输入
    - 拨打未过期的保单（Cancellation Date > F/U Date）
    - 拨打过期后的保单（Expiration Date过了一天之后）
    - 根据距离 Cancellation Date 的天数自动分配对应的 CL1 assistant ID
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services import SmartsheetService, VAPIService
from config import CANCELLATION_SHEET_ID
from workflows.cancellations import (
    parse_date, 
    get_call_stage, 
    update_after_call,
    count_business_days,
    get_assistant_id_for_stage
)
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

# 过期后保单的 Assistant ID
EXPIRED_AFTER_ASSISTANT_ID = "aec4721c-360c-45b5-ba39-87320eab6fc9"

def get_non_expired_customers_by_stage(smartsheet_service, target_date):
    """
    根据指定的 F/U Date 获取所有未过期的客户
    根据 F/U Date 距离 cancellation_date 的天数（14、7、1天）来决定使用哪个 assistant
    
    Args:
        smartsheet_service: SmartsheetService 实例
        target_date: 目标 F/U Date (date 对象)
    
    Returns:
        dict: 按 stage 分组的客户 {0: [...], 1: [...], 2: [...]}
              每个 stage 对应不同的 assistant (14天→Stage 0, 7天→Stage 1, 1天→Stage 2)
    """
    print("=" * 80)
    print(f"🔍 查找 F/U Date = {target_date} 的未过期客户")
    print("=" * 80)
    print("📋 根据 F/U Date 距离 cancellation_date 的天数分组:")
    print("   • 14 天前 → Stage 0 (第1次提醒)")
    print("   • 7 天前 → Stage 1 (第2次提醒)")
    print("   • 1 天前 → Stage 2 (第3次提醒)")
    print("=" * 80)
    
    # 获取所有客户
    all_customers = smartsheet_service.get_all_customers_with_stages()
    
    # 按 stage 分组：Stage 0 (14天), Stage 1 (7天), Stage 2 (1天)
    customers_by_stage = {0: [], 1: [], 2: []}
    skipped_count = 0
    
    for customer in all_customers:
        row_num = customer.get('row_number', 'N/A')
        
        # 检查 done 状态
        if customer.get('done?') in [True, 'true', 'True', 1]:
            skipped_count += 1
            continue
        
        # 检查 f_u_date (Follow-up Date)
        followup_date_str = customer.get('f_u_date', '')
        if not followup_date_str.strip():
            skipped_count += 1
            continue
        
        # 解析 f_u_date
        followup_date = parse_date(followup_date_str)
        if not followup_date:
            skipped_count += 1
            continue
        
        # 检查 f_u_date 是否等于目标日期
        if followup_date != target_date:
            continue  # 不是目标日期，跳过
        
        # 获取 cancellation_date
        cancellation_date_str = customer.get('cancellation_date', '')
        if not cancellation_date_str.strip():
            skipped_count += 1
            print(f"   ⏭️  跳过行 {row_num}: Cancellation Date 为空")
            continue
        
        cancellation_date = parse_date(cancellation_date_str)
        if not cancellation_date:
            skipped_count += 1
            print(f"   ⏭️  跳过行 {row_num}: Cancellation Date 无效")
            continue
        
        # 只选择未过期的客户（Cancellation Date > F/U Date）
        if cancellation_date <= followup_date:
            skipped_count += 1
            print(f"   ⏭️  跳过行 {row_num}: 已过期 (Cancellation Date {cancellation_date} <= F/U Date {followup_date})")
            continue
        
        # 检查 amount_due
        if not customer.get('amount_due', '').strip():
            skipped_count += 1
            print(f"   ⏭️  跳过行 {row_num}: Amount Due 为空")
            continue
        
        # 计算 F/U Date 距离 cancellation_date 的天数（工作日）
        business_days = count_business_days(followup_date, cancellation_date)
        
        # 根据天数决定使用哪个 assistant
        # 14天前 → Stage 0, 7天前 → Stage 1, 1天前 → Stage 2
        stage = -1
        stage_name = ""
        
        if business_days >= 12:  # 14天左右（允许一些容差）
            stage = 0
            stage_name = "第1次提醒 (14天前)"
        elif business_days >= 5:  # 7天左右（允许一些容差）
            stage = 1
            stage_name = "第2次提醒 (7天前)"
        elif business_days >= 1:  # 1天左右
            stage = 2
            stage_name = "第3次提醒 (1天前)"
        else:
            skipped_count += 1
            print(f"   ⏭️  跳过行 {row_num}: F/U Date 距离 Cancellation Date 太近 ({business_days} 工作日)")
            continue
        
        # 检查当前 stage 是否合理（不能倒退）
        current_stage = get_call_stage(customer)
        if current_stage > stage:
            skipped_count += 1
            print(f"   ⏭️  跳过行 {row_num}: 当前 stage ({current_stage}) 已超过目标 stage ({stage})")
            continue
        
        # 跳过已完成所有电话的客户
        if current_stage >= 3:
            skipped_count += 1
            print(f"   ⏭️  跳过行 {row_num}: 电话序列已完成 (stage {current_stage})")
            continue
        
        # 添加到对应分组
        customers_by_stage[stage].append(customer)
        print(f"   ✅ 行 {row_num}: {stage_name}, 距离取消日期 {business_days} 工作日, 准备拨打")
    
    print(f"\n📊 摘要:")
    print(f"   14天前 (Stage 0, 第1次提醒): {len(customers_by_stage[0])} 个客户")
    print(f"   7天前 (Stage 1, 第2次提醒): {len(customers_by_stage[1])} 个客户")
    print(f"   1天前 (Stage 2, 第3次提醒): {len(customers_by_stage[2])} 个客户")
    print(f"   跳过: {skipped_count} 行")
    print(f"   总计准备拨打: {sum(len(v) for v in customers_by_stage.values())} 个客户")
    
    return customers_by_stage

def get_expired_after_customers(smartsheet_service, target_date):
    """
    根据指定的 F/U Date 获取所有过期后的客户（Expiration Date过了一天之后）
    
    Args:
        smartsheet_service: SmartsheetService 实例
        target_date: 目标 F/U Date (date 对象)
    
    Returns:
        list: 过期后的客户列表
    """
    print("=" * 80)
    print(f"🔍 查找 F/U Date = {target_date} 的过期后客户")
    print("=" * 80)
    print("📋 筛选条件: Expiration Date过了一天之后 (今天 > Expiration Date + 1天)")
    print("=" * 80)
    
    # 获取所有客户
    all_customers = smartsheet_service.get_all_customers_with_stages()
    
    # 使用太平洋时区获取今天的日期
    pacific_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pacific_tz).date()
    
    expired_customers = []
    skipped_count = 0
    
    for customer in all_customers:
        row_num = customer.get('row_number', 'N/A')
        
        # 检查 done 状态
        if customer.get('done?') in [True, 'true', 'True', 1]:
            skipped_count += 1
            continue
        
        # 检查 f_u_date (Follow-up Date)
        followup_date_str = customer.get('f_u_date', '')
        if not followup_date_str.strip():
            skipped_count += 1
            continue
        
        # 解析 f_u_date
        followup_date = parse_date(followup_date_str)
        if not followup_date:
            skipped_count += 1
            continue
        
        # 检查 f_u_date 是否等于目标日期
        if followup_date != target_date:
            continue  # 不是目标日期，跳过
        
        # 获取 expiration_date
        expiration_date_str = customer.get('expiration_date', '') or customer.get('expiration date', '')
        if not expiration_date_str.strip():
            skipped_count += 1
            print(f"   ⏭️  跳过行 {row_num}: Expiration Date 为空")
            continue
        
        expiration_date = parse_date(expiration_date_str)
        if not expiration_date:
            skipped_count += 1
            print(f"   ⏭️  跳过行 {row_num}: Expiration Date 无效")
            continue
        
        # 检查是否过期后（今天 > Expiration Date + 1天）
        expiration_plus_one = expiration_date + timedelta(days=1)  # 加1天
        if today <= expiration_plus_one:
            skipped_count += 1
            print(f"   ⏭️  跳过行 {row_num}: 未过期或刚过期 (今天 {today} <= Expiration Date+1 {expiration_plus_one})")
            continue
        
        # 检查 amount_due
        if not customer.get('amount_due', '').strip():
            skipped_count += 1
            print(f"   ⏭️  跳过行 {row_num}: Amount Due 为空")
            continue
        
        # 添加到过期后客户列表
        expired_customers.append(customer)
        days_expired = (today - expiration_date).days
        print(f"   ✅ 行 {row_num}: 过期后保单 (Expiration Date {expiration_date}, 已过期 {days_expired} 天), 准备拨打")
    
    print(f"\n📊 摘要:")
    print(f"   过期后保单: {len(expired_customers)} 个客户")
    print(f"   跳过: {skipped_count} 行")
    
    return expired_customers

def call_non_expired_customers(target_date_str=None, auto_confirm=False, test_mode=False):
    """
    拨打未过期的保单客户
    
    Args:
        target_date_str: 目标 F/U Date (格式: YYYY-MM-DD)，如果为 None 则提示用户输入
        auto_confirm: 是否自动确认（不询问用户）
        test_mode: 如果为 True，跳过实际拨打和 Smartsheet 更新 (默认: False)
    """
    print("=" * 80)
    print("📞 拨打未过期保单（根据 F/U Date）")
    if test_mode:
        print("🧪 测试模式 - 不会实际拨打电话或更新 Smartsheet")
    print("=" * 80)
    
    # 初始化服务
    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
    vapi_service = VAPIService()
    
    # 获取目标日期
    if target_date_str:
        target_date = parse_date(target_date_str)
        if not target_date:
            print(f"❌ 无效的日期格式: {target_date_str}")
            print("   请使用格式: YYYY-MM-DD (例如: 2025-12-08)")
            return False
    else:
        # 提示用户输入日期
        print("\n请输入要拨打的 F/U Date (格式: YYYY-MM-DD)")
        print("例如: 2025-12-08")
        date_input = input("F/U Date: ").strip()
        
        if not date_input:
            print("❌ 未输入日期，已取消")
            return False
        
        target_date = parse_date(date_input)
        if not target_date:
            print(f"❌ 无效的日期格式: {date_input}")
            print("   请使用格式: YYYY-MM-DD (例如: 2025-12-08)")
            return False
    
    # 获取未过期客户（按 stage 分组）
    customers_by_stage = get_non_expired_customers_by_stage(smartsheet_service, target_date)
    
    # 获取过期后客户
    expired_after_customers = get_expired_after_customers(smartsheet_service, target_date)
    
    total_non_expired = sum(len(v) for v in customers_by_stage.values())
    total_expired_after = len(expired_after_customers)
    total_customers = total_non_expired + total_expired_after
    
    if total_customers == 0:
        print(f"\n✅ 没有 F/U Date = {target_date} 的客户需要拨打")
        return True
    
    # 显示摘要并询问确认
    print(f"\n{'=' * 80}")
    print(f"📊 准备拨打的客户列表 (F/U Date = {target_date}):")
    print(f"{'=' * 80}")
    
    stage_names_map = {0: "第1次提醒 (14天前)", 1: "第2次提醒 (7天前)", 2: "第3次提醒 (1天前)"}
    
    # 显示未过期客户
    for stage in [0, 1, 2]:
        customers = customers_by_stage[stage]
        if customers:
            assistant_id = get_assistant_id_for_stage(stage)
            print(f"\n🔔 {stage_names_map[stage]} (Stage {stage}) - {len(customers)} 个客户:")
            print(f"   🤖 Assistant ID: {assistant_id}")
            
            for i, customer in enumerate(customers[:10], 1):
                company = customer.get('company', 'Unknown')
                phone = customer.get('phone_number', 'N/A')
                fu_date = customer.get('f_u_date', 'N/A')
                cancellation_date = customer.get('cancellation_date', 'N/A')
                print(f"   {i}. {company} - {phone} (F/U: {fu_date}, Cancel: {cancellation_date})")
            
            if len(customers) > 10:
                print(f"   ... 还有 {len(customers) - 10} 个客户")
    
    # 显示过期后客户
    if expired_after_customers:
        print(f"\n🔔 过期后保单 - {len(expired_after_customers)} 个客户:")
        print(f"   🤖 Assistant ID: {EXPIRED_AFTER_ASSISTANT_ID}")
        
        for i, customer in enumerate(expired_after_customers[:10], 1):
            company = customer.get('company', 'Unknown')
            phone = customer.get('phone_number', 'N/A')
            fu_date = customer.get('f_u_date', 'N/A')
            expiration_date = customer.get('expiration_date', '') or customer.get('expiration date', 'N/A')
            print(f"   {i}. {company} - {phone} (F/U: {fu_date}, Expiration: {expiration_date})")
        
        if len(expired_after_customers) > 10:
            print(f"   ... 还有 {len(expired_after_customers) - 10} 个客户")
    
    print(f"\n{'=' * 80}")
    if not test_mode:
        print(f"⚠️  警告: 这将拨打 {total_customers} 通电话！")
        print(f"   • 未过期保单: {total_non_expired} 通")
        print(f"   • 过期后保单: {total_expired_after} 通")
        print(f"💰 每通电话都会产生费用")
    else:
        print(f"🧪 测试模式: 将模拟拨打 {total_customers} 通电话（不会产生费用）")
        print(f"   • 未过期保单: {total_non_expired} 通")
        print(f"   • 过期后保单: {total_expired_after} 通")
    print(f"{'=' * 80}")
    
    if not test_mode and not auto_confirm:
        response = input(f"\n确认要拨打这些电话吗? (y/N): ").strip().lower()
        
        if response not in ['y', 'yes', '是']:
            print("❌ 已取消拨打")
            return False
    else:
        print(f"\n🤖 自动确认: 开始拨打...")
    
    # 处理每个 stage
    total_success = 0
    total_failed = 0
    
    for stage in [0, 1, 2]:
        customers = customers_by_stage[stage]
        
        if not customers:
            continue
        
        stage_name = stage_names_map[stage]
        assistant_id = get_assistant_id_for_stage(stage)
        
        print(f"\n{'=' * 80}")
        print(f"📞 拨打 {stage_name} (Stage {stage}) - {len(customers)} 个客户")
        print(f"🤖 使用 Assistant: {assistant_id}")
        print(f"{'=' * 80}")
        
        # Stage 0 (14天前): 批量拨打 (同时拨打所有客户)
        if stage == 0:
            print(f"📦 批量拨打模式 (同时拨打)")
            if test_mode:
                print(f"\n🧪 测试模式: 模拟拨打 {len(customers)} 通电话...")
                for customer in customers:
                    print(f"   ✅ [SIMULATED] 将拨打: {customer.get('company', 'Unknown')} - {customer.get('phone_number', 'N/A')}")
                    total_success += 1
                continue
            results = vapi_service.make_batch_call_with_assistant(
                customers,
                assistant_id,
                schedule_immediately=True
            )
            
            if results:
                print(f"\n✅ Stage {stage} 批量拨打完成")
                
                # 检查结果数量是否匹配
                if len(results) != len(customers):
                    print(f"   ⚠️  警告: 结果数量 ({len(results)}) 与客户数量 ({len(customers)}) 不匹配")
                
                for i, customer in enumerate(customers):
                    # 获取对应的 call_data
                    if i < len(results):
                        call_data = results[i]
                    else:
                        call_data = results[0] if results else None
                    
                    if call_data:
                        # 检查是否有 analysis，如果没有则尝试刷新
                        if 'analysis' not in call_data or not call_data.get('analysis'):
                            print(f"   ⚠️  客户 {i+1} ({customer.get('company', 'Unknown')}): call_data 中没有 analysis")
                            if 'id' in call_data:
                                call_id = call_data['id']
                                print(f"      尝试刷新 call status for call_id: {call_id}")
                                try:
                                    refreshed_data = vapi_service.check_call_status(call_id)
                                    if refreshed_data and refreshed_data.get('analysis'):
                                        call_data = refreshed_data
                                        print(f"      ✅ 成功从刷新的 call status 获取 analysis")
                                    else:
                                        print(f"      ⚠️  刷新的 call status 也没有 analysis")
                                except Exception as e:
                                    print(f"      ❌ 刷新 call status 失败: {e}")
                        
                        # 尝试更新 Smartsheet
                        try:
                            current_stage = get_call_stage(customer)
                            success = update_after_call(smartsheet_service, customer, call_data, current_stage)
                            if success:
                                total_success += 1
                            else:
                                print(f"   ❌ 更新 Smartsheet 失败: {customer.get('company', 'Unknown')}")
                                total_failed += 1
                        except Exception as e:
                            print(f"   ❌ 更新 Smartsheet 时发生异常: {customer.get('company', 'Unknown')}: {e}")
                            import traceback
                            traceback.print_exc()
                            total_failed += 1
                    else:
                        print(f"   ❌ 客户 {i+1} ({customer.get('company', 'Unknown')}) 没有 call data")
                        total_failed += 1
            else:
                print(f"\n❌ Stage {stage} 批量拨打失败")
                total_failed += len(customers)
        
        # Stage 1 & 2: 顺序拨打 (一次一个客户)
        else:
            print(f"🔄 顺序拨打模式 (一次一个)")
            if test_mode:
                print(f"\n🧪 测试模式: 模拟拨打 {len(customers)} 通电话...")
                for customer in customers:
                    print(f"   ✅ [SIMULATED] 将拨打: {customer.get('company', 'Unknown')} - {customer.get('phone_number', 'N/A')}")
                    total_success += 1
                continue
            
            for i, customer in enumerate(customers, 1):
                company = customer.get('company', 'Unknown')
                print(f"\n   📞 拨打 {i}/{len(customers)}: {company}")
                
                results = vapi_service.make_batch_call_with_assistant(
                    [customer],  # 一次只拨打一个客户
                    assistant_id,
                    schedule_immediately=True
                )
                
                if results and results[0]:
                    call_data = results[0]
                    
                    # 检查是否有 analysis，如果没有则尝试刷新
                    if 'analysis' not in call_data or not call_data.get('analysis'):
                        print(f"   ⚠️  call_data 中没有 analysis，尝试刷新...")
                        if 'id' in call_data:
                            call_id = call_data['id']
                            try:
                                refreshed_data = vapi_service.check_call_status(call_id)
                                if refreshed_data and refreshed_data.get('analysis'):
                                    call_data = refreshed_data
                                    print(f"   ✅ 成功从刷新的 call status 获取 analysis")
                                else:
                                    print(f"   ⚠️  刷新的 call status 也没有 analysis")
                            except Exception as e:
                                print(f"   ❌ 刷新 call status 失败: {e}")
                    
                    current_stage = get_call_stage(customer)
                    success = update_after_call(smartsheet_service, customer, call_data, current_stage)
                    if success:
                        total_success += 1
                    else:
                        total_failed += 1
                else:
                    print(f"      ❌ 拨打 {i} 失败")
                    total_failed += 1
            
            print(f"\n✅ Stage {stage} 顺序拨打完成")
    
    # 处理过期后保单
    if expired_after_customers:
        print(f"\n{'=' * 80}")
        print(f"📞 拨打过期后保单 - {len(expired_after_customers)} 个客户")
        print(f"🤖 使用 Assistant: {EXPIRED_AFTER_ASSISTANT_ID}")
        print(f"{'=' * 80}")
        print(f"📦 批量拨打模式 (同时拨打)")
        
        if test_mode:
            print(f"\n🧪 测试模式: 模拟拨打 {len(expired_after_customers)} 通过期后保单电话...")
            for customer in expired_after_customers:
                print(f"   ✅ [SIMULATED] 将拨打: {customer.get('company', 'Unknown')} - {customer.get('phone_number', 'N/A')}")
                total_success += 1
        else:
            results = vapi_service.make_batch_call_with_assistant(
                expired_after_customers,
                EXPIRED_AFTER_ASSISTANT_ID,
                schedule_immediately=True
            )
            
            if results:
                print(f"\n✅ 过期后保单批量拨打完成")
                
                # 检查结果数量是否匹配
                if len(results) != len(expired_after_customers):
                    print(f"   ⚠️  警告: 结果数量 ({len(results)}) 与客户数量 ({len(expired_after_customers)}) 不匹配")
                
                for i, customer in enumerate(expired_after_customers):
                    # 获取对应的 call_data
                    if i < len(results):
                        call_data = results[i]
                    else:
                        call_data = results[0] if results else None
                    
                    if call_data:
                        # 检查是否有 analysis，如果没有则尝试刷新
                        if 'analysis' not in call_data or not call_data.get('analysis'):
                            print(f"   ⚠️  客户 {i+1} ({customer.get('company', 'Unknown')}): call_data 中没有 analysis")
                            if 'id' in call_data:
                                call_id = call_data['id']
                                print(f"      尝试刷新 call status for call_id: {call_id}")
                                try:
                                    refreshed_data = vapi_service.check_call_status(call_id)
                                    if refreshed_data and refreshed_data.get('analysis'):
                                        call_data = refreshed_data
                                        print(f"      ✅ 成功从刷新的 call status 获取 analysis")
                                    else:
                                        print(f"      ⚠️  刷新的 call status 也没有 analysis")
                                except Exception as e:
                                    print(f"      ❌ 刷新 call status 失败: {e}")
                        
                        # 尝试更新 Smartsheet
                        # 对于过期后保单，我们仍然使用 update_after_call，但传入当前 stage
                        # update_after_call 会自动增加 stage，这对于过期后保单也是合理的
                        try:
                            current_stage = get_call_stage(customer)
                            success = update_after_call(smartsheet_service, customer, call_data, current_stage)
                            if success:
                                total_success += 1
                            else:
                                print(f"   ❌ 更新 Smartsheet 失败: {customer.get('company', 'Unknown')}")
                                total_failed += 1
                        except Exception as e:
                            print(f"   ❌ 更新 Smartsheet 时发生异常: {customer.get('company', 'Unknown')}: {e}")
                            import traceback
                            traceback.print_exc()
                            total_failed += 1
                    else:
                        print(f"   ❌ 客户 {i+1} ({customer.get('company', 'Unknown')}) 没有 call data")
                        total_failed += 1
            else:
                print(f"\n❌ 过期后保单批量拨打失败")
                total_failed += len(expired_after_customers)
    
    # 最终摘要
    print(f"\n{'=' * 80}")
    print(f"🏁 拨打完成")
    print(f"{'=' * 80}")
    print(f"   ✅ 成功: {total_success}")
    print(f"   ❌ 失败: {total_failed}")
    print(f"   📊 总计: {total_customers}")
    print(f"   • 未过期保单: {total_non_expired}")
    print(f"   • 过期后保单: {total_expired_after}")
    print(f"{'=' * 80}")
    
    return True

if __name__ == "__main__":
    import sys
    auto_confirm = "--yes" in sys.argv or "-y" in sys.argv or "--auto-confirm" in sys.argv
    test_mode = "--test" in sys.argv or "-t" in sys.argv
    
    # 检查是否有日期参数
    target_date_str = None
    if "--date" in sys.argv or "-d" in sys.argv:
        arg_name = "--date" if "--date" in sys.argv else "-d"
        arg_index = sys.argv.index(arg_name)
        if arg_index + 1 < len(sys.argv):
            target_date_str = sys.argv[arg_index + 1]
        else:
            print(f"❌ {arg_name} 参数需要指定日期 (格式: YYYY-MM-DD)")
            sys.exit(1)
    
    call_non_expired_customers(target_date_str=target_date_str, auto_confirm=auto_confirm, test_mode=test_mode)

