#!/usr/bin/env python3
"""
全面检查昨天Cancellation电话情况
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.vapi_service import VAPIService
from services import SmartsheetService
from config import CANCELLATION_SHEET_ID
from config import (
    CANCELLATION_1ST_REMINDER_ASSISTANT_ID,
    CANCELLATION_2ND_REMINDER_ASSISTANT_ID,
    CANCELLATION_3RD_REMINDER_ASSISTANT_ID
)
from workflows.cancellations import (
    get_call_stage,
    should_skip_row,
    parse_date
)

def comprehensive_check():
    """全面检查昨天Cancellation电话情况"""
    print("=" * 80)
    print("🔍 全面检查昨天Cancellation电话情况")
    print("=" * 80)
    
    # 计算昨天（太平洋时间）
    pacific_tz = ZoneInfo("America/Los_Angeles")
    now = datetime.now(pacific_tz)
    today = now.date()
    yesterday = today - timedelta(days=1)
    
    print(f"\n📅 检查日期: {yesterday}")
    print(f"   当前时间: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}\n")
    
    # 1. 检查VAPI实际拨打的电话
    print("=" * 80)
    print("1️⃣  VAPI实际拨打的电话")
    print("=" * 80)
    
    vapi_service = VAPIService()
    print("📡 正在从VAPI获取通话记录...")
    recent_calls = vapi_service.get_recent_calls(limit=200)
    
    cl1_assistant_ids = {
        CANCELLATION_1ST_REMINDER_ASSISTANT_ID: "1st Reminder",
        CANCELLATION_2ND_REMINDER_ASSISTANT_ID: "2nd Reminder",
        CANCELLATION_3RD_REMINDER_ASSISTANT_ID: "3rd Reminder"
    }
    
    yesterday_calls = []
    for call in recent_calls:
        assistant_id = call.get('assistantId', '')
        if assistant_id not in cl1_assistant_ids:
            continue
        
        created = call.get('createdAt', '') or call.get('created_at', '')
        started = call.get('startedAt', '') or call.get('started_at', '')
        timestamp_str = started if started else created
        
        if not timestamp_str:
            continue
        
        # 简单检查：如果时间戳字符串包含昨天的日期，就认为是昨天的电话
        # 这样可以避免时区转换的问题
        yesterday_str = yesterday.strftime('%Y-%m-%d')
        if yesterday_str in timestamp_str:
            try:
                call_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                call_time_local = call_time.replace(tzinfo=None)
                
                yesterday_calls.append({
                    'call': call,
                    'assistant_type': cl1_assistant_ids[assistant_id],
                    'time': call_time_local,
                    'assistant_id': assistant_id
                })
            except:
                continue
    
    print(f"\n✅ 实际拨打的电话: {len(yesterday_calls)} 通\n")
    
    if yesterday_calls:
        for idx, item in enumerate(yesterday_calls, 1):
            call = item['call']
            assistant_type = item['assistant_type']
            time = item['time']
            end_reason = call.get('endedReason', 'N/A')
            duration = call.get('duration', 0)
            cost = call.get('cost', 0)
            call_id = call.get('id', 'N/A')
            
            print(f"   {idx}. {assistant_type}")
            print(f"      时间: {time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(f"      结束原因: {end_reason}")
            if duration:
                print(f"      时长: {duration}秒")
            if cost:
                print(f"      费用: ${cost:.4f}")
            print(f"      Call ID: {call_id[:50]}...")
            print()
    else:
        print("   ⚠️  没有找到任何电话")
    
    # 2. 检查Smartsheet中应该拨打的客户
    print("=" * 80)
    print("2️⃣  Smartsheet中应该拨打的客户分析")
    print("=" * 80)
    
    print("📡 正在从Smartsheet获取数据...")
    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
    all_customers = smartsheet_service.get_all_customers_with_stages()
    print(f"✅ 获取到 {len(all_customers)} 条客户记录\n")
    
    # 筛选F/U Date为昨天的客户
    should_call_customers = []
    skipped_customers = []
    
    for customer in all_customers:
        followup_date_str = customer.get('f_u_date', '')
        
        if not followup_date_str:
            continue
        
        followup_date = parse_date(followup_date_str)
        
        if followup_date == yesterday:
            should_skip, skip_reason = should_skip_row(customer)
            stage = get_call_stage(customer)
            
            if should_skip:
                skipped_customers.append({
                    'customer': customer,
                    'reason': skip_reason,
                    'stage': stage
                })
            elif stage >= 3:
                skipped_customers.append({
                    'customer': customer,
                    'reason': f"Call sequence complete (stage {stage})",
                    'stage': stage
                })
            else:
                should_call_customers.append({
                    'customer': customer,
                    'stage': stage
                })
    
    print(f"📊 分析结果:")
    print(f"   ✅ 应该拨打: {len(should_call_customers)} 个客户")
    print(f"   ⏭️  被跳过: {len(skipped_customers)} 个客户")
    print(f"   📞 实际拨打: {len(yesterday_calls)} 通电话\n")
    
    # 显示应该拨打的客户
    if should_call_customers:
        print(f"✅ 应该拨打但可能没有拨打的客户 ({len(should_call_customers)}个):")
        print("-" * 80)
        
        for idx, item in enumerate(should_call_customers, 1):
            customer = item['customer']
            stage = item['stage']
            stage_name = ["1st", "2nd", "3rd"][stage] if stage < 3 else "Complete"
            
            print(f"\n{idx}. Row {customer.get('row_number')}:")
            print(f"   Company: {customer.get('company', 'N/A')}")
            print(f"   Client ID: {customer.get('client_id', 'N/A')}")
            print(f"   Phone: {customer.get('phone_number', 'N/A')}")
            print(f"   Stage: {stage} ({stage_name} Reminder)")
            print(f"   F/U Date: {customer.get('f_u_date', 'N/A')}")
            print(f"   Cancellation Date: {customer.get('cancellation_date', 'N/A')}")
            print(f"   Amount Due: {customer.get('amount_due', 'N/A')}")
            print(f"   AI Call Stage: {customer.get('ai_call_stage', 'N/A')}")
    else:
        print("⚠️  当前Smartsheet中没有F/U Date为昨天的客户")
        print("   (如果工作流运行了，F/U Date应该已经被更新)")
    
    # 显示被跳过的客户统计
    if skipped_customers:
        print(f"\n⏭️  被跳过的客户统计 ({len(skipped_customers)}个):")
        print("-" * 80)
        
        skip_reasons = defaultdict(list)
        for item in skipped_customers:
            reason = item['reason']
            skip_reasons[reason].append(item)
        
        for reason, items in sorted(skip_reasons.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"\n   {reason}: {len(items)}个客户")
            for idx, item in enumerate(items[:3], 1):  # 只显示前3个
                customer = item['customer']
                print(f"      {idx}. Row {customer.get('row_number')}: {customer.get('company', 'N/A')} - {customer.get('phone_number', 'N/A')}")
            if len(items) > 3:
                print(f"      ... 还有 {len(items) - 3} 个")
    
    # 3. 检查工作流日志
    print(f"\n{'=' * 80}")
    print("3️⃣  工作流运行状态")
    print("=" * 80)
    
    log_dir = Path(__file__).parent.parent / "logs" / "cron"
    log_file = log_dir / f"cancellations_{yesterday.strftime('%Y-%m-%d')}.log"
    
    if log_file.exists():
        print(f"✅ 找到日志文件: {log_file}")
        print(f"   文件大小: {log_file.stat().st_size} bytes")
        print(f"   修改时间: {datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 读取最后几行
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"\n   最后10行日志:")
                print("   " + "-" * 76)
                for line in lines[-10:]:
                    print(f"   {line.rstrip()}")
        except:
            print("   ⚠️  无法读取日志文件")
    else:
        print(f"❌ 没有找到日志文件: {log_file}")
        print(f"   可能原因:")
        print(f"   - 工作流没有运行")
        print(f"   - 工作流在其他服务器上运行")
        print(f"   - 日志文件被删除")
    
    # 4. 总结
    print(f"\n{'=' * 80}")
    print("4️⃣  总结")
    print("=" * 80)
    
    print(f"\n📊 关键数据:")
    print(f"   - VAPI实际拨打: {len(yesterday_calls)} 通")
    print(f"   - 应该拨打: {len(should_call_customers)} 个客户")
    print(f"   - 被跳过: {len(skipped_customers)} 个客户")
    print(f"   - 工作流日志: {'存在' if log_file.exists() else '不存在'}")
    
    print(f"\n💡 分析:")
    if len(yesterday_calls) == 0:
        print(f"   ❌ 昨天没有拨打任何Cancellation电话")
        if len(should_call_customers) > 0:
            print(f"   ⚠️  但应该有 {len(should_call_customers)} 个客户需要拨打")
            print(f"   🔍 可能原因: 工作流没有运行，或者所有客户都被跳过了")
    elif len(yesterday_calls) < len(should_call_customers):
        missing = len(should_call_customers) - len(yesterday_calls)
        print(f"   ⚠️  缺少 {missing} 通电话")
        print(f"   🔍 可能原因:")
        print(f"      - 工作流部分运行")
        print(f"      - 某些客户在运行时被跳过")
        print(f"      - 某些电话失败")
    elif len(yesterday_calls) == len(should_call_customers):
        print(f"   ✅ 电话数量匹配")
    else:
        print(f"   ℹ️  实际电话数多于应该拨打的客户数")
        print(f"   🔍 可能原因: 有重复拨打或手动拨打")
    
    if not log_file.exists() and len(yesterday_calls) > 0:
        print(f"\n   ⚠️  有电话但没有日志文件")
        print(f"   🔍 可能原因: 电话是手动拨打的，或者日志在其他位置")
    
    print("=" * 80)

if __name__ == "__main__":
    comprehensive_check()

