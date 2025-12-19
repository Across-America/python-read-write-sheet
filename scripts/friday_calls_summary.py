"""
周五通话总结 - 检查 CL1 和 N1 的实际通话数量
"""

import sys
import io
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置输出编码为 UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from services.vapi_service import VAPIService
from config import (
    CANCELLATION_1ST_REMINDER_ASSISTANT_ID,
    CANCELLATION_2ND_REMINDER_ASSISTANT_ID,
    CANCELLATION_3RD_REMINDER_ASSISTANT_ID,
    RENEWAL_1ST_REMINDER_ASSISTANT_ID,
    RENEWAL_2ND_REMINDER_ASSISTANT_ID,
    RENEWAL_3RD_REMINDER_ASSISTANT_ID,
)

def get_friday_calls_summary():
    """获取周五的通话总结"""
    print("=" * 80)
    print("Friday Calls Summary - CL1 and N1")
    print("=" * 80)
    
    pacific_tz = ZoneInfo("America/Los_Angeles")
    now = datetime.now(pacific_tz)
    
    # 找到最近的周五
    today = now.date()
    days_back = (today.weekday() - 4) % 7
    if days_back == 0 and today.weekday() == 4:
        last_friday = today
    elif days_back == 0:
        last_friday = today - timedelta(days=7)
    else:
        last_friday = today - timedelta(days=days_back)
    
    print(f"\nLast Friday: {last_friday.strftime('%Y-%m-%d (%A)')}")
    print("=" * 80)
    
    # CL1 Assistant IDs
    cl1_ids = {
        CANCELLATION_1ST_REMINDER_ASSISTANT_ID: "CL1 - 1st Reminder",
        CANCELLATION_2ND_REMINDER_ASSISTANT_ID: "CL1 - 2nd Reminder",
        CANCELLATION_3RD_REMINDER_ASSISTANT_ID: "CL1 - 3rd Reminder"
    }
    
    # N1 Assistant IDs
    n1_ids = {
        RENEWAL_1ST_REMINDER_ASSISTANT_ID: "N1 - 1st Reminder",
        RENEWAL_2ND_REMINDER_ASSISTANT_ID: "N1 - 2nd Reminder",
        RENEWAL_3RD_REMINDER_ASSISTANT_ID: "N1 - 3rd Reminder"
    }
    
    vapi_service = VAPIService()
    
    try:
        recent_calls = vapi_service.get_recent_calls(limit=500)
    except Exception as e:
        print(f"Error fetching calls: {e}")
        return
    
    cl1_calls = []
    n1_calls = []
    
    for call in recent_calls:
        started_at_str = call.get('startedAt') or call.get('createdAt', '')
        if not started_at_str:
            continue
        
        try:
            started_at_utc = datetime.fromisoformat(started_at_str.replace('Z', '+00:00'))
            started_at_pacific = started_at_utc.astimezone(pacific_tz)
            call_date = started_at_pacific.date()
            
            if call_date != last_friday:
                continue
            
            assistant_id = call.get('assistantId', '')
            
            # CL1 通话 (11:00 AM - 12:00 PM)
            if assistant_id in cl1_ids and 11 <= started_at_pacific.hour < 12:
                cl1_calls.append({
                    'time': started_at_pacific,
                    'phone': call.get('customer', {}).get('number', 'N/A'),
                    'status': call.get('endedReason', 'N/A'),
                    'assistant': cl1_ids[assistant_id]
                })
            
            # N1 通话 (4:00 PM - 5:00 PM)
            if assistant_id in n1_ids and 16 <= started_at_pacific.hour < 17:
                n1_calls.append({
                    'time': started_at_pacific,
                    'phone': call.get('customer', {}).get('number', 'N/A'),
                    'status': call.get('endedReason', 'N/A'),
                    'assistant': n1_ids[assistant_id]
                })
        except Exception as e:
            continue
    
    cl1_calls.sort(key=lambda x: x['time'])
    n1_calls.sort(key=lambda x: x['time'])
    
    print(f"\nCL1 (Cancellations) - 11:00 AM")
    print("-" * 80)
    print(f"Total calls: {len(cl1_calls)}")
    if cl1_calls:
        for i, call in enumerate(cl1_calls, 1):
            print(f"  {i}. {call['time'].strftime('%H:%M:%S')} - {call['phone']} - {call['assistant']} - {call['status']}")
    else:
        print("  (No calls found)")
    
    print(f"\nN1 (Renewals) - 4:00 PM")
    print("-" * 80)
    print(f"Total calls: {len(n1_calls)}")
    if n1_calls:
        for i, call in enumerate(n1_calls, 1):
            print(f"  {i}. {call['time'].strftime('%H:%M:%S')} - {call['phone']} - {call['assistant']} - {call['status']}")
    else:
        print("  (No calls found)")
    
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Friday ({last_friday.strftime('%Y-%m-%d')}):")
    print(f"  CL1 calls: {len(cl1_calls)}")
    print(f"  N1 calls: {len(n1_calls)}")
    print(f"  Total: {len(cl1_calls) + len(n1_calls)} calls")
    print("=" * 80)

if __name__ == "__main__":
    get_friday_calls_summary()

