#!/usr/bin/env python3
"""
Twilio直接API实现 - 支持自定义来电显示
确保显示公司号码: +1 951 247 2003
"""

import os
from twilio.rest import Client
from twilio.twiml import VoiceResponse
from dotenv import load_dotenv
import requests
import json

# Load environment variables
load_dotenv()

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', 'your_twilio_sid')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', 'your_twilio_token')
TWILIO_PHONE_NUMBER = "+19093256365"  # 你的Twilio号码（用于拨出）

# 🏢 公司来电显示号码 - 硬性要求
COMPANY_CALLER_ID = "+19512472003"  # 必须显示的公司号码

# OpenAI Configuration (用于AI语音生成)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'your_openai_key')

class TwilioDirectCaller:
    def __init__(self):
        self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    def verify_company_number(self):
        """
        验证公司号码是否已在Twilio中验证
        """
        try:
            # 获取已验证的来电显示号码列表
            outgoing_caller_ids = self.client.outgoing_caller_ids.list()
            
            verified_numbers = [caller_id.phone_number for caller_id in outgoing_caller_ids]
            
            if COMPANY_CALLER_ID in verified_numbers:
                print(f"✅ 公司号码 {COMPANY_CALLER_ID} 已验证")
                return True
            else:
                print(f"❌ 公司号码 {COMPANY_CALLER_ID} 未验证")
                print(f"📋 已验证的号码: {verified_numbers}")
                return False
                
        except Exception as e:
            print(f"❌ 检查验证状态时出错: {e}")
            return False
    
    def add_company_number_for_verification(self):
        """
        添加公司号码进行验证
        """
        try:
            print(f"📞 正在添加公司号码 {COMPANY_CALLER_ID} 进行验证...")
            
            outgoing_caller_id = self.client.outgoing_caller_ids.create(
                phone_number=COMPANY_CALLER_ID
            )
            
            print(f"✅ 验证请求已发送")
            print(f"📋 验证码将发送到: {COMPANY_CALLER_ID}")
            print(f"🔍 验证SID: {outgoing_caller_id.sid}")
            
            return outgoing_caller_id.sid
            
        except Exception as e:
            print(f"❌ 添加验证时出错: {e}")
            return None
    
    def generate_personalized_twiml(self, customer_info):
        """
        生成个性化的TwiML响应
        """
        response = VoiceResponse()
        
        # 个性化问候语
        customer_name = customer_info.get('insured', 'Customer')
        agent_name = customer_info.get('agent_name', 'Agent')
        policy_number = customer_info.get('policy_number', '')
        
        greeting = f"Hello {customer_name}, this is {agent_name} from All Solution Insurance. "
        greeting += f"I'm calling regarding your policy {policy_number}. "
        greeting += "How can I assist you today?"
        
        # 使用AI语音合成（可选）
        response.say(greeting, voice='alice', language='en-US')
        
        # 添加交互选项
        gather = response.gather(
            input='speech dtmf',
            timeout=10,
            speech_timeout='auto'
        )
        gather.say("Please let me know how I can help you, or press 1 to speak with a representative.")
        
        # 如果没有输入，重复消息
        response.say("I didn't hear anything. Please call us back if you need assistance. Thank you!")
        
        return str(response)
    
    def make_call_with_company_caller_id(self, to_number, customer_info):
        """
        使用公司号码作为来电显示拨打电话
        
        Args:
            to_number (str): 目标电话号码
            customer_info (dict): 客户信息
        
        Returns:
            str: Call SID if successful, None if failed
        """
        
        # 首先检查公司号码是否已验证
        if not self.verify_company_number():
            print(f"⚠️ 公司号码未验证，请先运行验证流程")
            return None
        
        try:
            print(f"📞 拨打电话到: {to_number}")
            print(f"🏢 来电显示: {COMPANY_CALLER_ID}")
            print(f"👤 客户: {customer_info.get('insured', 'Unknown')}")
            
            # 生成TwiML URL（需要一个web服务器来提供TwiML）
            # 这里使用一个简单的TwiML
            twiml_response = self.generate_personalized_twiml(customer_info)
            
            # 创建通话
            call = self.client.calls.create(
                to=to_number,
                from_=COMPANY_CALLER_ID,  # 🎯 使用公司号码作为来电显示
                twiml=twiml_response,  # 直接使用TwiML内容
                timeout=30,
                time_limit=300  # 5分钟通话限制
            )
            
            print(f"✅ 通话已发起")
            print(f"📞 Call SID: {call.sid}")
            print(f"📊 状态: {call.status}")
            print(f"🏢 客户将看到来电显示: {COMPANY_CALLER_ID}")
            
            return call.sid
            
        except Exception as e:
            print(f"❌ 拨打电话时出错: {e}")
            return None
    
    def check_call_status(self, call_sid):
        """
        检查通话状态
        """
        try:
            call = self.client.calls(call_sid).fetch()
            
            print(f"📊 通话状态: {call.status}")
            print(f"⏱️ 持续时间: {call.duration} 秒")
            print(f"💰 价格: ${call.price} {call.price_unit}")
            
            return {
                'status': call.status,
                'duration': call.duration,
                'price': call.price,
                'start_time': call.start_time,
                'end_time': call.end_time
            }
            
        except Exception as e:
            print(f"❌ 检查通话状态时出错: {e}")
            return None

def test_company_caller_id():
    """
    测试公司来电显示功能
    """
    print("🧪 测试Twilio直接API - 公司来电显示")
    print("=" * 60)
    
    caller = TwilioDirectCaller()
    
    # 测试客户信息
    customer_info = {
        'insured': 'WILSON JOHN',
        'agent_name': 'Suzette Murrell',
        'policy_number': 'CP0032322',
        'phone_number': '6262387555'
    }
    
    # 检查验证状态
    if not caller.verify_company_number():
        print("\n🔧 需要验证公司号码")
        print("请运行以下命令添加验证:")
        print("caller.add_company_number_for_verification()")
        return
    
    # 拨打测试电话
    test_number = "+16262387555"  # 测试号码
    call_sid = caller.make_call_with_company_caller_id(test_number, customer_info)
    
    if call_sid:
        print(f"\n✅ 测试成功!")
        print(f"📞 Call SID: {call_sid}")
        print(f"🏢 客户将看到来电显示: {COMPANY_CALLER_ID}")
    else:
        print(f"\n❌ 测试失败")

if __name__ == "__main__":
    test_company_caller_id()
