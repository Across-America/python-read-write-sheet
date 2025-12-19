"""Analyze call patterns to understand why transfers aren't happening"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import requests
from config import VAPI_API_KEY, STM1_ASSISTANT_ID

base_url = "https://api.vapi.ai"
headers = {
    "Authorization": f"Bearer {VAPI_API_KEY}",
    "Content-Type": "application/json"
}

print("=" * 80)
print("📊 ANALYZING CALL PATTERNS")
print("=" * 80)

params = {
    'assistantId': STM1_ASSISTANT_ID,
    'limit': 50
}

response = requests.get(
    f"{base_url}/call",
    headers=headers,
    params=params
)

response_data = response.json()
calls = response_data if isinstance(response_data, list) else response_data.get('calls', [])

print(f"\n📊 Analyzing {len(calls)} recent calls\n")

# Analyze by duration
duration_ranges = {
    '0-10s': 0,
    '10-30s': 0,
    '30-60s': 0,
    '60s+': 0
}

# Analyze by ended reason
ended_reasons = {}

# Check if availability question was asked
availability_keywords = ['do you have', 'have time', 'available', '15 minutes', '10 minutes', 'recorded statement']
calls_with_availability_question = 0
calls_with_yes_response = 0

for call in calls:
    duration = call.get('duration', 0) or 0
    ended_reason = call.get('endedReason', 'unknown')
    
    # Categorize by duration
    if duration <= 10:
        duration_ranges['0-10s'] += 1
    elif duration <= 30:
        duration_ranges['10-30s'] += 1
    elif duration <= 60:
        duration_ranges['30-60s'] += 1
    else:
        duration_ranges['60s+'] += 1
    
    # Count ended reasons
    ended_reasons[ended_reason] = ended_reasons.get(ended_reason, 0) + 1
    
    # Check transcript for availability question
    transcript = (call.get('transcript', '') or '').lower()
    summary = (call.get('analysis', {}).get('summary', '') or '').lower()
    full_text = transcript + ' ' + summary
    
    # Check if availability question was asked
    if any(keyword in full_text for keyword in availability_keywords):
        calls_with_availability_question += 1
        
        # Check if customer said yes
        yes_keywords = ['yes', 'yeah', 'sure', 'okay', 'ok', 'available', 'have time', 'can do']
        ivr_indicators = ['press', 'dial', 'extension', 'menu', 'option']
        has_ivr = any(indicator in full_text for indicator in ivr_indicators)
        
        if not has_ivr:
            if any(keyword in full_text for keyword in yes_keywords):
                calls_with_yes_response += 1

print("=" * 80)
print("📊 CALL DURATION ANALYSIS")
print("=" * 80)
for range_name, count in duration_ranges.items():
    percentage = (count / len(calls) * 100) if calls else 0
    print(f"   {range_name}: {count} calls ({percentage:.1f}%)")

print("\n" + "=" * 80)
print("📊 ENDED REASON ANALYSIS")
print("=" * 80)
for reason, count in sorted(ended_reasons.items(), key=lambda x: x[1], reverse=True):
    percentage = (count / len(calls) * 100) if calls else 0
    print(f"   {reason}: {count} ({percentage:.1f}%)")

print("\n" + "=" * 80)
print("📊 AVAILABILITY QUESTION ANALYSIS")
print("=" * 80)
print(f"   Total calls: {len(calls)}")
print(f"   Calls where availability question was asked: {calls_with_availability_question} ({calls_with_availability_question/len(calls)*100:.1f}%)")
print(f"   Calls with 'yes' response: {calls_with_yes_response} ({calls_with_yes_response/len(calls)*100:.1f}%)")
print(f"   Calls transferred: {ended_reasons.get('assistant-forwarded-call', 0)} ({ended_reasons.get('assistant-forwarded-call', 0)/len(calls)*100:.1f}%)")

print("\n" + "=" * 80)
print("💡 INSIGHTS")
print("=" * 80)

if calls_with_availability_question == 0:
    print("   ⚠️  Availability question is NOT being asked in most calls")
    print("   💡 Calls may be ending before the question is asked")
elif calls_with_yes_response == 0:
    print("   ⚠️  No customers are saying 'yes' to availability question")
    print("   💡 Customers may be:")
    print("      - Hanging up before answering")
    print("      - Saying 'no' or not available")
    print("      - Encountering IVR systems")
elif calls_with_yes_response > 0 and ended_reasons.get('assistant-forwarded-call', 0) == 0:
    print("   ⚠️  Customers ARE saying 'yes' but transfers are NOT happening")
    print("   💡 This indicates a problem with transfer tool execution")
else:
    print("   ✅ System appears to be working correctly")

