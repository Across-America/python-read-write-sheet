"""
详细监控测试进度 - 检查VAPI电话和Smartsheet更新
"""

import sys
from pathlib import Path
from datetime import datetime
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.smartsheet_service import SmartsheetService
from services.vapi_service import VAPIService
from config import RENEWAL_PLR_SHEET_ID

def find_target_customers():
    """找出指定的三个客户：Sarb, Amrin, 和 Rick"""
    smartsheet_service = SmartsheetService(sheet_id=RENEWAL_PLR_SHEET_ID)
    all_customers = smartsheet_service.get_all_customers_with_stages()
    
    target_customers = []
    for customer in all_customers:
        first_name = str(customer.get('first_name', '')).strip().upper()
        last_name = str(customer.get('last_name', '')).strip().upper()
        
        if (first_name == 'SARB' and last_name == 'GILL') or \
           (first_name == 'AMRIN' and last_name == 'SAHI') or \
           (first_name == 'RICK' and last_name == 'YANG'):
            target_customers.append(customer)
    
    return target_customers

def check_smartsheet_updates():
    """检查Smartsheet中的call notes更新"""
    customers = find_target_customers()
    
    print("\n" + "=" * 80)
    print("📋 SMARTSHEET CALL NOTES STATUS")
    print("=" * 80)
    
    for customer in customers:
        first_name = customer.get('first_name', 'N/A')
        last_name = customer.get('last_name', 'N/A')
        phone = customer.get('client_phone_number', 'N/A')
        call_notes = customer.get('call_notes', '')
        
        # 检查是否有call notes
        if call_notes and call_notes.strip():
            # 计算call notes的数量（按---分割）
            call_count = len([c for c in call_notes.split('---') if c.strip()])
            print(f"✅ {first_name} {last_name} ({phone})")
            print(f"   📝 Call notes found: {call_count} entry/entries")
            
            # 显示最新的call note时间
            if 'Call Placed At:' in call_notes:
                lines = call_notes.split('\n')
                for i, line in enumerate(lines):
                    if 'Call Placed At:' in line and i + 1 < len(lines):
                        time_str = lines[i].split('Call Placed At:')[1].strip()
                        print(f"   🕐 Latest call: {time_str}")
                        break
        else:
            print(f"⏳ {first_name} {last_name} ({phone})")
            print(f"   📝 No call notes yet")
        
        print("-" * 80)

def check_vapi_calls():
    """检查VAPI最近的电话"""
    print("\n" + "=" * 80)
    print("📞 VAPI RECENT CALLS STATUS")
    print("=" * 80)
    
    vapi_service = VAPIService()
    recent_calls = vapi_service.get_recent_calls(limit=20)
    
    if not recent_calls:
        print("⚠️  No recent calls found")
        return
    
    # 过滤最近30分钟的电话
    now = datetime.now()
    recent_test_calls = []
    
    for call in recent_calls:
        created = call.get('createdAt', '') or call.get('created_at', '')
        if created:
            try:
                call_time = datetime.fromisoformat(created.replace('Z', '+00:00'))
                time_diff = (now - call_time.replace(tzinfo=None)).total_seconds()
                
                if time_diff < 1800:  # 30分钟内
                    recent_test_calls.append((call, time_diff))
            except:
                pass
    
    if not recent_test_calls:
        print("⚠️  No calls in the last 30 minutes")
        return
    
    # 按时间排序
    recent_test_calls.sort(key=lambda x: x[1])
    
    print(f"\n✅ Found {len(recent_test_calls)} calls in the last 30 minutes\n")
    
    for idx, (call, time_diff) in enumerate(recent_test_calls[:10], 1):  # 只显示最近10个
        call_id = call.get('id', 'N/A')
        status = call.get('status', 'N/A')
        end_reason = call.get('endedReason', 'N/A')
        duration = call.get('duration', 'N/A')
        cost = call.get('cost', 'N/A')
        created = call.get('createdAt', '') or call.get('created_at', 'N/A')
        
        # 格式化时间
        if time_diff < 60:
            time_ago = f"{int(time_diff)}s ago"
        elif time_diff < 3600:
            time_ago = f"{int(time_diff/60)}m ago"
        else:
            time_ago = f"{int(time_diff/3600)}h ago"
        
        # 状态图标
        if status == 'ended':
            if end_reason == 'voicemail':
                icon = "📞"
            elif end_reason == 'assistant-ended-call':
                icon = "✅"
            elif end_reason == 'customer-ended-call':
                icon = "📴"
            else:
                icon = "ℹ️"
        elif status == 'queued' or status == 'ringing':
            icon = "⏳"
        elif status == 'in-progress':
            icon = "📞"
        else:
            icon = "❓"
        
        print(f"{idx}. {icon} {time_ago}")
        print(f"   Status: {status} | End: {end_reason}")
        if duration != 'N/A':
            print(f"   Duration: {duration}s | Cost: ${cost}")
        print(f"   Call ID: {call_id[:50]}...")
        print("-" * 80)

def monitor_progress():
    """监控测试进度"""
    print("=" * 80)
    print("🔍 MONITORING TEST PROGRESS")
    print("=" * 80)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查目标客户
    customers = find_target_customers()
    print(f"\n📋 Target customers: {len(customers)}")
    for customer in customers:
        first_name = customer.get('first_name', 'N/A')
        last_name = customer.get('last_name', 'N/A')
        print(f"   - {first_name} {last_name}")
    
    # 检查Smartsheet更新
    check_smartsheet_updates()
    
    # 检查VAPI电话
    check_vapi_calls()
    
    print("\n" + "=" * 80)
    print("💡 Tip: Run this script again to see updated progress")
    print("=" * 80)

if __name__ == "__main__":
    monitor_progress()

