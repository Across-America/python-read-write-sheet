"""Quick STM1 check"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from workflows.stm1 import get_stm1_sheet
from scripts.auto_stm1_calling import get_customers_with_empty_called_times
from services import VAPIService
from config import STM1_PHONE_NUMBER_ID
from datetime import datetime
from zoneinfo import ZoneInfo

print("=" * 80)
print("STM1 QUICK STATUS CHECK")
print("=" * 80)

# Check customers
try:
    service = get_stm1_sheet()
    customers = get_customers_with_empty_called_times(service)
    print(f"\nAvailable customers: {len(customers)}")
    if customers:
        print(f"First row: {customers[0].get('row_number')}")
        print(f"Last row: {customers[-1].get('row_number')}")
    else:
        print("NO CUSTOMERS AVAILABLE")
except Exception as e:
    print(f"Error checking customers: {e}")

# Check calls
try:
    vapi = VAPIService(phone_number_id=STM1_PHONE_NUMBER_ID)
    calls = vapi.get_recent_calls(limit=20)
    pacific = ZoneInfo("America/Los_Angeles")
    now = datetime.now(pacific)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = 0
    for call in calls:
        created_at = call.get('createdAt', '')
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=ZoneInfo("UTC"))
                dt = dt.astimezone(pacific)
                if dt >= today_start:
                    today_count += 1
            except:
                pass
    print(f"\nCalls today: {today_count}")
except Exception as e:
    print(f"Error checking calls: {e}")

print("=" * 80)

