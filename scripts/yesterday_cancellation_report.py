#!/usr/bin/env python3
"""
昨天Cancellation电话情况报告
用于回答同事的询问
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

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

def generate_report():
    """生成昨天Cancellation电话情况报告"""
    print("=" * 80)
    print("📊 昨天Cancellation电话情况报告")
    print("=" * 80)
    
    # 计算昨天（太平洋时间）
    pacific_tz = ZoneInfo("America/Los_Angeles")
    now = datetime.now(pacific_tz)
    today = now.date()
    yesterday = today - timedelta(days=1)
    
    print(f"\n📅 报告日期: {yesterday}")
    print(f"   生成时间: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}\n")
    
    # 1. 检查VAPI实际拨打的电话
    print("=" * 80)
    print("1️⃣  VAPI实际拨打的电话")
    print("=" * 80)
    
    vapi_service = VAPIService()
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
        
        try:
            call_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            call_time_local = call_time.replace(tzinfo=None)
            
            today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday_start = today_start - timedelta(days=1)
            yesterday_end = today_start
            
            if yesterday_start <= call_time_local < yesterday_end:
                yesterday_calls.append({
                    'call': call,
                    'assistant_type': cl1_assistant_ids[assistant_id],
                    'time': call_time_local
                })
        except:
            continue
    
    print(f"\n✅ 实际拨打的电话: {len(yesterday_calls)} 通")
    for idx, item in enumerate(yesterday_calls, 1):
        call = item['call']
        assistant_type = item['assistant_type']
        time = item['time']
        end_reason = call.get('endedReason', 'N/A')
        cost = call.get('cost', 0)
        
        print(f"   {idx}. {assistant_type} - {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"      结束原因: {end_reason}")
        if cost:
            print(f"      费用: ${cost:.4f}")
    
    # 2. 检查工作流是否运行
    print(f"\n{'=' * 80}")
    print("2️⃣  工作流运行状态")
    print("=" * 80)
    
    log_dir = Path(__file__).parent.parent / "logs" / "cron"
    log_file = log_dir / f"cancellations_{yesterday.strftime('%Y-%m-%d')}.log"
    
    if log_file.exists():
        print(f"✅ 找到日志文件: {log_file}")
        print(f"   工作流昨天应该运行了")
    else:
        print(f"❌ 没有找到日志文件: {log_file}")
        print(f"   可能原因:")
        print(f"   - 工作流没有运行（cron job可能没有执行）")
        print(f"   - 工作流在其他服务器上运行")
        print(f"   - 日志文件被删除或移动")
    
    # 3. 检查Smartsheet中F/U Date为昨天的客户
    print(f"\n{'=' * 80}")
    print("3️⃣  Smartsheet中F/U Date为昨天的客户")
    print("=" * 80)
    
    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
    all_customers = smartsheet_service.get_all_customers_with_stages()
    
    # 注意：如果工作流运行了，F/U Date会被更新，所以现在检查可能看不到昨天的F/U Date
    from workflows.cancellations import parse_date
    
    yesterday_fu_date_customers = []
    for customer in all_customers:
        followup_date_str = customer.get('f_u_date', '')
        if not followup_date_str:
            continue
        
        followup_date = parse_date(followup_date_str)
        if followup_date == yesterday:
            yesterday_fu_date_customers.append(customer)
    
    print(f"\n当前Smartsheet中F/U Date为昨天的客户: {len(yesterday_fu_date_customers)} 个")
    print(f"   (注意：如果工作流运行了，这些客户的F/U Date应该已经被更新)")
    
    # 4. 总结和建议
    print(f"\n{'=' * 80}")
    print("4️⃣  总结和建议")
    print("=" * 80)
    
    print(f"\n📊 关键发现:")
    print(f"   - VAPI实际拨打: {len(yesterday_calls)} 通电话")
    print(f"   - 工作流日志: {'存在' if log_file.exists() else '不存在'}")
    print(f"   - 当前F/U Date为昨天的客户: {len(yesterday_fu_date_customers)} 个")
    
    print(f"\n💡 可能的情况:")
    if len(yesterday_calls) > 0 and not log_file.exists():
        print(f"   1. 工作流可能没有自动运行（cron job可能失败）")
        print(f"   2. 电话可能是手动拨打的")
        print(f"   3. 工作流在其他环境运行（生产服务器）")
    elif len(yesterday_calls) == 0:
        print(f"   1. 昨天确实没有拨打任何Cancellation电话")
        print(f"   2. 可能没有符合条件的客户（F/U Date = 昨天）")
        print(f"   3. 工作流可能没有运行")
    else:
        print(f"   1. 工作流正常运行，拨打了 {len(yesterday_calls)} 通电话")
    
    print(f"\n🔍 建议检查:")
    print(f"   1. 检查生产服务器的cron job是否正常运行")
    print(f"   2. 检查生产服务器的日志文件")
    print(f"   3. 检查Smartsheet中客户的F/U Date是否正确设置")
    print(f"   4. 检查是否有客户被跳过（done? checked, 缺少字段等）")
    
    print("=" * 80)

if __name__ == "__main__":
    generate_report()



