"""Get full prompt from STM1 assistant"""
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

response = requests.get(
    f"{base_url}/assistant/{STM1_ASSISTANT_ID}",
    headers=headers
)
assistant = response.json()

model = assistant.get('model', {})
messages = model.get('messages', [])

for msg in messages:
    if msg.get('role') == 'system':
        prompt = msg.get('content', '')
        print("=" * 80)
        print("FULL PROMPT:")
        print("=" * 80)
        print(prompt)
        print("=" * 80)
        break

