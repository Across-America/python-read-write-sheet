import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.vapi_service import VAPIService
from config import CANCELLATION_1ST_REMINDER_ASSISTANT_ID, CANCELLATION_2ND_REMINDER_ASSISTANT_ID, CANCELLATION_3RD_REMINDER_ASSISTANT_ID
from datetime import datetime

vapi = VAPIService()
calls = vapi.get_recent_calls(limit=200)
cl1_ids = [CANCELLATION_1ST_REMINDER_ASSISTANT_ID, CANCELLATION_2ND_REMINDER_ASSISTANT_ID, CANCELLATION_3RD_REMINDER_ASSISTANT_ID]

yesterday_calls = []
for c in calls:
    assistant_id = c.get('assistantId', '')
    if assistant_id not in cl1_ids:
        continue
    timestamp = c.get('startedAt') or c.get('createdAt', '')
    if timestamp and '2025-12-02' in timestamp:
        yesterday_calls.append(c)

print(f'Found {len(yesterday_calls)} CL1 calls on 2025-12-02')
for i, c in enumerate(yesterday_calls, 1):
    print(f"  {i}. {c.get('assistantId', '')[:8]}... - {c.get('startedAt') or c.get('createdAt', 'N/A')} - {c.get('endedReason', 'N/A')}")

