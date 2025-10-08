#!/usr/bin/env python3
"""
Test VAPI Call Status API
Check the status of a specific call ID
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import json
from config import VAPI_API_KEY

def check_call_status(call_id):
    """Check the status of a specific VAPI call"""
    base_url = "https://api.vapi.ai"

    print(f"\n🔍 Checking status for call: {call_id}")
    print("=" * 80)

    try:
        response = requests.get(
            f"{base_url}/call/{call_id}",
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}",
            }
        )

        print(f"📡 Response Status: {response.status_code}")

        if response.status_code == 200:
            call_data = response.json()
            print(f"\n✅ Call data retrieved successfully")
            print("=" * 80)
            print(json.dumps(call_data, indent=2))
            print("=" * 80)

            # Display key info
            print(f"\n📊 Key Information:")
            print(f"   • Status: {call_data.get('status', 'N/A')}")
            print(f"   • End Reason: {call_data.get('endedReason', 'N/A')}")
            print(f"   • Duration: {call_data.get('duration', 'N/A')}s")
            print(f"   • Cost: ${call_data.get('cost', 'N/A')}")
            print(f"   • Created At: {call_data.get('createdAt', 'N/A')}")
            print(f"   • Started At: {call_data.get('startedAt', 'N/A')}")
            print(f"   • Ended At: {call_data.get('endedAt', 'N/A')}")

            # Check analysis
            analysis = call_data.get('analysis', {})
            if analysis:
                print(f"\n📝 Analysis:")
                print(f"   • Summary: {analysis.get('summary', 'N/A')[:100]}...")
                print(f"   • Success Evaluation: {analysis.get('successEvaluation', 'N/A')}")
            else:
                print(f"\n📝 Analysis: Not available")

            return call_data
        else:
            print(f"❌ Failed to get call status")
            print(f"   Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python test_vapi_call_status.py <call_id>")
        print("\nExample:")
        print("  python test_vapi_call_status.py 0199c17f-4fd8-7aa2-867e-d7b206b18170")
        sys.exit(1)

    call_id = sys.argv[1]
    check_call_status(call_id)
