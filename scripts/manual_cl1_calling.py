"""
CL1 Project - Manual Cancellation Calling Script
手动触发脚本：根据指定的 F/U Date 拨打所有已过期的保单

使用方法:
    python scripts/manual_cl1_calling.py --date 2025-12-05
    或
    python scripts/manual_cl1_calling.py --test --date 2025-12-05  # 测试模式，不实际拨打

注意: 
- 只拨打已过期的保单（Cancellation Date <= F/U Date）
- 使用固定的 Assistant ID: aec4721c-360c-45b5-ba39-87320eab6fc9
- 所有过期保单批量拨打（同时拨打）
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, date
from zoneinfo import ZoneInfo
from services import VAPIService, SmartsheetService
from config import (
    CANCELLATION_SHEET_ID,
    CANCELLATION_1ST_REMINDER_ASSISTANT_ID,
    CANCELLATION_2ND_REMINDER_ASSISTANT_ID,
    CANCELLATION_3RD_REMINDER_ASSISTANT_ID
)
from workflows.cancellations import (
    should_skip_row,
    get_call_stage,
    get_assistant_id_for_stage,
    update_after_call,
    parse_date
)


def get_customers_by_fu_date(smartsheet_service, target_date):
    """
    根据指定的 F/U Date 获取所有已过期的客户（Cancellation Date <= F/U Date）
    所有过期客户使用同一个 assistant ID
    
    Args:
        smartsheet_service: SmartsheetService 实例
        target_date: 目标 F/U Date (date 对象)
    
    Returns:
        list: 已过期的客户列表
    """
    print("=" * 80)
    print(f"🔍 查找 F/U Date = {target_date} 的已过期客户")
    print("=" * 80)
    print("📋 筛选条件: Cancellation Date <= F/U Date (已过期)")
    print("=" * 80)
    
    # 获取所有客户
    all_customers = smartsheet_service.get_all_customers_with_stages()
    
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
            continue  # 不是目标日期，跳过（不打印，避免输出太多）
        
        # 找到匹配的 F/U Date，打印调试信息
        print(f"   🔍 检查行 {row_num}: F/U Date = {followup_date_str}")
        
        # 获取 cancellation_date
        cancellation_date_str = customer.get('cancellation_date', '')
        if not cancellation_date_str.strip():
            skipped_count += 1
            print(f"   ⏭️  跳过行 {customer.get('row_number')}: Cancellation Date 为空")
            continue
        
        cancellation_date = parse_date(cancellation_date_str)
        if not cancellation_date:
            skipped_count += 1
            print(f"   ⏭️  跳过行 {customer.get('row_number')}: Cancellation Date 无效")
            continue
        
        # 只选择已过期的客户（Cancellation Date <= F/U Date）
        # 注意：对于过期客户，我们不需要检查 cancellation_date > f_u_date 的关系
        if cancellation_date > followup_date:
            skipped_count += 1
            print(f"   ⏭️  跳过行 {customer.get('row_number')}: 未过期 (Cancellation Date {cancellation_date} > F/U Date {followup_date})")
            continue
        
        # 检查 amount_due（过期客户也需要有 amount_due）
        if not customer.get('amount_due', '').strip():
            skipped_count += 1
            print(f"   ⏭️  跳过行 {customer.get('row_number')}: Amount Due 为空")
            continue
        
        # 计算过期天数
        days_expired = (followup_date - cancellation_date).days
        
        # 检查当前 stage（跳过已完成所有电话的客户）
        current_stage = get_call_stage(customer)
        if current_stage >= 3:
            skipped_count += 1
            print(f"   ⏭️  跳过行 {customer.get('row_number')}: 电话序列已完成 (stage {current_stage})")
            continue
        
        # 添加到过期客户列表
        expired_customers.append(customer)
        status = "今天过期" if days_expired == 0 else f"已过期 {days_expired} 天"
        print(f"   ✅ 行 {customer.get('row_number')}: 已过期保单, {status}, 准备拨打")
    
    print(f"\n📊 摘要:")
    print(f"   已过期客户: {len(expired_customers)} 个")
    print(f"   跳过: {skipped_count} 行")
    print(f"   总计准备拨打: {len(expired_customers)} 个客户")
    
    return expired_customers


def manual_cl1_calling(target_date_str=None, test_mode=False, auto_confirm=False):
    """
    手动触发 CL1 项目的电话拨打
    
    Args:
        target_date_str: 目标 F/U Date 字符串 (格式: YYYY-MM-DD)，如果为 None 则提示用户输入
        test_mode: 如果为 True，跳过实际拨打和 Smartsheet 更新 (默认: False)
        assistant_ids: dict，包含每个 stage 的 assistant ID，格式: {0: 'id0', 1: 'id1', 2: 'id2'}
                       如果为 None，则提示用户输入
    """
    print("=" * 80)
    print("🚀 CL1 项目 - 手动触发电话拨打系统")
    if test_mode:
        print("🧪 测试模式 - 不会实际拨打电话或更新 Smartsheet")
    print("=" * 80)
    print("📋 CL1 项目: 根据 F/U Date 手动触发电话拨打")
    print("📞 3阶段拨打: 第1次提醒 → 第2次提醒 → 第3次提醒")
    print("=" * 80)
    
    # 获取目标日期
    if target_date_str:
        target_date = parse_date(target_date_str)
        if not target_date:
            print(f"❌ 无效的日期格式: {target_date_str}")
            print("   请使用格式: YYYY-MM-DD (例如: 2025-01-15)")
            return False
    else:
        # 提示用户输入日期
        print("\n请输入要拨打的 F/U Date (格式: YYYY-MM-DD)")
        print("例如: 2025-01-15")
        date_input = input("F/U Date: ").strip()
        
        if not date_input:
            print("❌ 未输入日期，已取消")
            return False
        
        target_date = parse_date(date_input)
        if not target_date:
            print(f"❌ 无效的日期格式: {date_input}")
            print("   请使用格式: YYYY-MM-DD (例如: 2025-01-15)")
            return False
    
    print(f"\n📅 目标 F/U Date: {target_date}")
    
    # 使用指定的 Assistant ID（用于所有过期保单）
    EXPIRED_POLICY_ASSISTANT_ID = "aec4721c-360c-45b5-ba39-87320eab6fc9"
    
    print(f"\n🤖 Assistant ID 配置:")
    print(f"   过期保单 Assistant ID: {EXPIRED_POLICY_ASSISTANT_ID}")
    
    # 初始化服务
    try:
        smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
        vapi_service = VAPIService()
    except Exception as e:
        print(f"❌ 初始化服务失败: {e}")
        return False
    
    # 根据目标日期获取已过期的客户
    expired_customers = get_customers_by_fu_date(smartsheet_service, target_date)
    
    total_customers = len(expired_customers)
    
    if total_customers == 0:
        print(f"\n✅ 没有 F/U Date = {target_date} 的已过期客户需要拨打")
        return True
    
    # 显示摘要并询问确认
    print(f"\n{'=' * 80}")
    print(f"📊 准备拨打的已过期客户列表 (F/U Date = {target_date}):")
    print(f"{'=' * 80}")
    print(f"\n🔔 已过期保单 - {total_customers} 个客户:")
    print(f"   🤖 Assistant ID: {EXPIRED_POLICY_ASSISTANT_ID}")
    
    for i, customer in enumerate(expired_customers[:20], 1):
        company = customer.get('company', 'Unknown')
        phone = customer.get('phone_number', 'N/A')
        fu_date = customer.get('f_u_date', 'N/A')
        cancellation_date = customer.get('cancellation_date', 'N/A')
        days_expired = 0
        if fu_date and cancellation_date:
            fu = parse_date(fu_date)
            cancel = parse_date(cancellation_date)
            if fu and cancel:
                days_expired = (fu - cancel).days
        status = "今天过期" if days_expired == 0 else f"已过期 {days_expired} 天"
        print(f"   {i}. {company} - {phone} (F/U: {fu_date}, Cancel: {cancellation_date}, {status})")
    
    if len(expired_customers) > 20:
        print(f"   ... 还有 {len(expired_customers) - 20} 个客户")
    
    print(f"\n{'=' * 80}")
    if not test_mode:
        print(f"⚠️  警告: 这将拨打 {total_customers} 通电话！")
        print(f"💰 每通电话都会产生费用")
    else:
        print(f"🧪 测试模式: 将模拟 {total_customers} 通电话 (不会产生费用)")
    print(f"{'=' * 80}")
    
    # 询问确认
    if not test_mode and not auto_confirm:
        response = input(f"\n确认要拨打这些电话吗? (y/N): ").strip().lower()
        
        if response not in ['y', 'yes', '是']:
            print("❌ 已取消拨打")
            return False
    elif auto_confirm:
        print(f"\n🤖 自动确认: 开始拨打...")
    
    # 处理已过期的客户（批量拨打）
    total_success = 0
    total_failed = 0
    
    print(f"\n{'=' * 80}")
    print(f"📞 拨打已过期保单 - {total_customers} 个客户")
    print(f"🤖 使用 Assistant: {EXPIRED_POLICY_ASSISTANT_ID}")
    print(f"{'=' * 80}")
    
    if test_mode:
        # 测试模式: 模拟拨打
        print(f"\n🧪 测试模式: 模拟 {total_customers} 通电话...")
        for customer in expired_customers:
            company = customer.get('company', 'Unknown')
            phone = customer.get('phone_number', 'N/A')
            print(f"   ✅ [模拟] 将拨打: {company} - {phone}")
            total_success += 1
    else:
        # 批量拨打所有过期客户（同时拨打）
        print(f"📦 批量拨打模式 (同时拨打所有过期客户)")
        results = vapi_service.make_batch_call_with_assistant(
            expired_customers,
            EXPIRED_POLICY_ASSISTANT_ID,
            schedule_immediately=True
        )
        
        if results:
            print(f"\n✅ 批量拨打完成")
            
            # 检查结果数量是否匹配
            if len(results) != len(expired_customers):
                print(f"   ⚠️  警告: 结果数量 ({len(results)}) 与客户数量 ({len(expired_customers)}) 不匹配")
            
            for i, customer in enumerate(expired_customers):
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
                    
                    # 获取当前 stage（用于更新）
                    current_stage = get_call_stage(customer)
                    
                    # 尝试更新 Smartsheet
                    try:
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
            print(f"\n❌ 批量拨打失败")
            total_failed += len(expired_customers)
    
    # 最终摘要
    print(f"\n{'=' * 80}")
    print(f"🏁 拨打完成")
    print(f"{'=' * 80}")
    print(f"   ✅ 成功: {total_success}")
    print(f"   ❌ 失败: {total_failed}")
    print(f"   📊 总计: {total_success + total_failed}")
    print(f"{'=' * 80}")
    
    return True


if __name__ == "__main__":
    import sys
    
    # 检查命令行参数
    test_mode = "--test" in sys.argv or "-t" in sys.argv
    auto_confirm = "--yes" in sys.argv or "-y" in sys.argv or "--auto-confirm" in sys.argv
    
    # 检查是否有日期参数
    target_date_str = None
    if "--date" in sys.argv:
        date_index = sys.argv.index("--date")
        if date_index + 1 < len(sys.argv):
            target_date_str = sys.argv[date_index + 1]
        else:
            print("❌ --date 参数需要指定日期 (格式: YYYY-MM-DD)")
            sys.exit(1)
    elif "-d" in sys.argv:
        date_index = sys.argv.index("-d")
        if date_index + 1 < len(sys.argv):
            target_date_str = sys.argv[date_index + 1]
        else:
            print("❌ -d 参数需要指定日期 (格式: YYYY-MM-DD)")
            sys.exit(1)
    
    manual_cl1_calling(target_date_str=target_date_str, test_mode=test_mode, auto_confirm=auto_confirm)

