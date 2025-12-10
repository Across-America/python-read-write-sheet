"""
设置 voicemailMessage 配置
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
import json
from config import VAPI_API_KEY

assistant_id = "aec4721c-360c-45b5-ba39-87320eab6fc9"
base_url = "https://api.vapi.ai"
headers = {
    "Authorization": f"Bearer {VAPI_API_KEY}",
    "Content-Type": "application/json"
}

print("=" * 80)
print("🔧 设置 VoicemailMessage")
print("=" * 80)

# 首先获取当前配置
print("\n📥 获取当前配置...")
get_response = requests.get(
    f"{base_url}/assistant/{assistant_id}",
    headers=headers
)

if get_response.status_code != 200:
    print(f"❌ 获取配置失败: {get_response.status_code}")
    sys.exit(1)

assistant = get_response.json()
first_message = assistant.get('firstMessage', '')

# 基于 firstMessage 创建 voicemailMessage
# 移除最后的问句，因为 voicemail 不需要交互
voicemail_message = first_message
if voicemail_message:
    # 移除最后的问句
    if "Would you like to speak with a representative for assistance?" in voicemail_message:
        voicemail_message = voicemail_message.replace(
            "Would you like to speak with a representative for assistance?",
            "If you need assistance, please call us at (951) 247-2003. Thank you."
        )
    # 或者使用简化的版本
    # voicemail_message = "Hello, this is Chris, an AI assistant, calling on behalf of All Solutions Insurance. This is a courtesy notice regarding your insurance policy. Per our records, your policy did not renew because the renewal payment was not received. At this time, our records show that you do not have active coverage. Please contact your carrier or log in to your online portal to make the payment as soon as possible. If you need assistance, please call us at (951) 247-2003. Thank you."

print(f"\n📝 准备设置的 voicemailMessage:")
print(f"   {voicemail_message[:300]}...")

# 更新配置
update_payload = {
    "voicemailMessage": voicemail_message
}

print(f"\n🚀 发送更新请求...")
update_response = requests.patch(
    f"{base_url}/assistant/{assistant_id}",
    headers=headers,
    json=update_payload
)

if update_response.status_code == 200:
    updated_assistant = update_response.json()
    print("✅ 成功更新 voicemailMessage！")
    
    # 验证
    updated_message = updated_assistant.get('voicemailMessage', '')
    if updated_message:
        print(f"\n✅ 验证更新后的 voicemailMessage:")
        print(f"   {updated_message[:300]}...")
        print(f"\n🎉 VoicemailMessage 已成功设置！")
    else:
        print(f"\n⚠️  警告: voicemailMessage 可能未正确设置")
else:
    print(f"\n❌ 更新失败")
    print(f"   Status Code: {update_response.status_code}")
    print(f"   Response: {update_response.text}")

