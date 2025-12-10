"""
通过 API 启用 Assistant 的 Voicemail Detection
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
import json
from config import VAPI_API_KEY

def enable_voicemail_detection(assistant_id):
    """通过 API 启用 assistant 的 voicemail detection"""
    base_url = "https://api.vapi.ai"
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    print("=" * 80)
    print(f"🔧 启用 Assistant 的 Voicemail Detection: {assistant_id}")
    print("=" * 80)
    
    try:
        # 首先获取当前的 assistant 配置
        print("\n📥 获取当前配置...")
        get_response = requests.get(
            f"{base_url}/assistant/{assistant_id}",
            headers=headers
        )
        
        if get_response.status_code != 200:
            print(f"❌ 获取 Assistant 配置失败")
            print(f"   Status Code: {get_response.status_code}")
            print(f"   Response: {get_response.text}")
            return False
        
        assistant = get_response.json()
        print("✅ 成功获取当前配置")
        
        # 获取当前的 voicemailDetection 配置
        current_voicemail = assistant.get('voicemailDetection', {})
        print(f"\n📋 当前 Voicemail Detection 配置:")
        print(json.dumps(current_voicemail, indent=2, ensure_ascii=False))
        
        # 准备更新的配置
        # 使用 twilio provider（因为电话服务使用的是 Twilio）
        # 增加检测时间和重试次数，以提高 voicemail 检测成功率
        phone_provider = assistant.get('phoneCallProvider', 'twilio')  # 从 assistant 配置获取
        print(f"\n📞 电话服务提供商: {phone_provider}")
        
        # 如果使用 Twilio，建议使用 twilio provider 进行 voicemail detection
        # 如果使用其他服务，可以使用 vapi provider
        voicemail_provider = "twilio" if phone_provider == "twilio" else "vapi"
        print(f"📞 将使用 Voicemail Detection Provider: {voicemail_provider}")
        
        # 根据 provider 使用不同的配置格式
        if voicemail_provider == "twilio":
            # Twilio provider 使用不同的配置格式
            updated_voicemail = {
                "provider": "twilio",
                "voicemailDetectionTypes": [
                    "machine_end_beep",
                    "machine_end_silence",
                    "human",
                    "fax",
                    "unknown",
                    "machine_end_other"
                ],
                "machineDetectionTimeout": 45
            }
        else:
            # VAPI provider 使用 backoffPlan
            updated_voicemail = {
                "provider": "vapi",
                "backoffPlan": {
                    "maxRetries": 10,  # 增加重试次数：从 6 增加到 10
                    "startAtSeconds": 3,  # 减少初始延迟：从 5 秒减少到 3 秒（更快开始检测）
                    "frequencySeconds": 3  # 减少重试间隔：从 5 秒减少到 3 秒（更频繁检测）
                },
                "beepMaxAwaitSeconds": 2  # 增加 beep 等待时间：从 0 增加到 2 秒（等待 beep 音）
            }
        
        # 如果已经有 beepDetection，保留它
        if "beepDetection" in current_voicemail:
            updated_voicemail["beepDetection"] = current_voicemail["beepDetection"]
        
        # 检查当前配置是否已经存在
        if not current_voicemail:
            print("⚠️  当前没有 voicemailDetection 配置，将创建新配置")
        else:
            print("✅ 当前已有 voicemailDetection 配置，将更新以确保完整")
        
        print(f"\n📝 准备更新的配置:")
        print(json.dumps(updated_voicemail, indent=2, ensure_ascii=False))
        
        # 更新 assistant 配置
        update_payload = {
            "voicemailDetection": updated_voicemail
        }
        
        print(f"\n🚀 发送更新请求...")
        update_response = requests.patch(
            f"{base_url}/assistant/{assistant_id}",
            headers=headers,
            json=update_payload
        )
        
        if update_response.status_code == 200:
            updated_assistant = update_response.json()
            print("✅ 成功更新 Assistant 配置！")
            
            # 验证更新
            updated_voicemail_config = updated_assistant.get('voicemailDetection', {})
            print(f"\n✅ 验证更新后的配置:")
            print(json.dumps(updated_voicemail_config, indent=2, ensure_ascii=False))
            
            # 检查配置是否存在且完整
            if updated_voicemail_config and updated_voicemail_config.get('provider'):
                print(f"\n🎉 Voicemail Detection 配置已更新！")
                print(f"   注意: VAPI API 不使用 'enabled' 字段")
                print(f"   只要 voicemailDetection 配置存在，功能就应该已启用")
                return True
            else:
                print(f"\n⚠️  警告: voicemailDetection 配置可能不完整")
                return False
        else:
            print(f"\n❌ 更新失败")
            print(f"   Status Code: {update_response.status_code}")
            print(f"   Response: {update_response.text}")
            
            # 尝试解析错误信息
            try:
                error_data = update_response.json()
                print(f"\n   错误详情:")
                print(json.dumps(error_data, indent=2, ensure_ascii=False))
            except:
                pass
            
            return False
            
    except Exception as e:
        print(f"\n❌ 操作失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 过期保单的 assistant ID
    expired_assistant_id = "aec4721c-360c-45b5-ba39-87320eab6fc9"
    
    print("⚠️  注意: 这将通过 API 更新 Assistant 配置")
    print("   确保你有权限修改此 Assistant")
    print()
    
    success = enable_voicemail_detection(expired_assistant_id)
    
    if success:
        print("\n" + "=" * 80)
        print("✅ 操作完成！Voicemail Detection 已启用")
        print("=" * 80)
        print("\n💡 建议:")
        print("   1. 可以运行 'python scripts/check_assistant_config.py' 验证配置")
        print("   2. 测试拨打一个电话，确认 voicemail 功能正常工作")
    else:
        print("\n" + "=" * 80)
        print("❌ 操作失败，请检查错误信息")
        print("=" * 80)

