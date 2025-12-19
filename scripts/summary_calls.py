"""
总结昨天和今天的通话情况
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.vapi_service import VAPIService
from config import (
    # CL1
    CANCELLATION_1ST_REMINDER_ASSISTANT_ID,
    CANCELLATION_2ND_REMINDER_ASSISTANT_ID,
    CANCELLATION_3RD_REMINDER_ASSISTANT_ID,
    # N1
    RENEWAL_1ST_REMINDER_ASSISTANT_ID,
    RENEWAL_2ND_REMINDER_ASSISTANT_ID,
    RENEWAL_3RD_REMINDER_ASSISTANT_ID
)

def summary_calls():
    """总结通话情况"""
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=" * 80)
    print("Call Summary - Yesterday 4 PM (N1) and Today 11 AM (CL1)")
    print("=" * 80)
    
    pacific_tz = ZoneInfo("America/Los_Angeles")
    now = datetime.now(pacific_tz)
    today = now.date()
    yesterday = (now - timedelta(days=1)).date()
    
    vapi_service = VAPIService()
    
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
    
    try:
        recent_calls = vapi_service.get_recent_calls(limit=200)
        
        # 1. 今天 11:00 AM CL1 通话
        print(f"\n1. Today (12-10) 11:00 AM - CL1 Project")
        print("-" * 80)
        
        today_cl1_calls = []
        for call in recent_calls:
            assistant_id = call.get('assistantId', '')
            if assistant_id not in cl1_ids:
                continue
            
            started_at_str = call.get('startedAt') or call.get('createdAt', '')
            if not started_at_str:
                continue
            
            try:
                started_at_utc = datetime.fromisoformat(started_at_str.replace('Z', '+00:00'))
                started_at_pacific = started_at_utc.astimezone(pacific_tz)
                
                if started_at_pacific.date() == today and 11 <= started_at_pacific.hour < 12:
                    today_cl1_calls.append({
                        'call': call,
                        'time': started_at_pacific,
                        'assistant': cl1_ids[assistant_id]
                    })
            except:
                continue
        
        today_cl1_calls.sort(key=lambda x: x['time'])
        
        print(f"   Total: {len(today_cl1_calls)} calls")
        for i, item in enumerate(today_cl1_calls, 1):
            call = item['call']
            time = item['time']
            phone = call.get('customer', {}).get('number', 'N/A')
            status = call.get('endedReason', 'N/A')
            print(f"   {i}. {time.strftime('%H:%M:%S')} - {phone} - {status}")
        
        # 2. 昨天 4:00 PM N1 通话
        print(f"\n2. Yesterday (12-09) 4:00 PM - N1 Project")
        print("-" * 80)
        
        yesterday_n1_calls = []
        for call in recent_calls:
            assistant_id = call.get('assistantId', '')
            if assistant_id not in n1_ids:
                continue
            
            started_at_str = call.get('startedAt') or call.get('createdAt', '')
            if not started_at_str:
                continue
            
            try:
                started_at_utc = datetime.fromisoformat(started_at_str.replace('Z', '+00:00'))
                started_at_pacific = started_at_utc.astimezone(pacific_tz)
                
                if started_at_pacific.date() == yesterday and 16 <= started_at_pacific.hour < 17:
                    yesterday_n1_calls.append({
                        'call': call,
                        'time': started_at_pacific,
                        'assistant': n1_ids[assistant_id]
                    })
            except:
                continue
        
        yesterday_n1_calls.sort(key=lambda x: x['time'])
        
        print(f"   Total: {len(yesterday_n1_calls)} calls")
        for i, item in enumerate(yesterday_n1_calls, 1):
            call = item['call']
            time = item['time']
            phone = call.get('customer', {}).get('number', 'N/A')
            status = call.get('endedReason', 'N/A')
            print(f"   {i}. {time.strftime('%H:%M:%S')} - {phone} - {status}")
        
        # 总结
        print("\n" + "=" * 80)
        print("Summary")
        print("=" * 80)
        print(f"\nYesterday (12-09) 4:00 PM - N1 Project: {len(yesterday_n1_calls)} calls")
        print(f"Today (12-10) 11:00 AM - CL1 Project: {len(today_cl1_calls)} calls")
        print(f"\nTotal: {len(yesterday_n1_calls) + len(today_cl1_calls)} calls")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    summary_calls()

