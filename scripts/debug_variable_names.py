#!/usr/bin/env python3
"""
调试变量名格式 - 检查 VAPI First Message 中的变量名格式
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import json
import re
from config import VAPI_API_KEY
from workflows.renewals import get_renewal_assistant_id_for_stage


def debug_variable_names():
    """调试变量名格式"""
    print("=" * 80)
    print("🔍 调试变量名格式")
    print("=" * 80)
    
    assistant_id = get_renewal_assistant_id_for_stage(0)
    base_url = "https://api.vapi.ai"
    
    try:
        response = requests.get(
            f"{base_url}/assistant/{assistant_id}",
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code != 200:
            print(f"❌ 获取失败: {response.status_code}")
            return
        
        assistant_data = response.json()
        first_message = assistant_data.get('firstMessage', '')
        
        print("\n📋 First Message 内容:")
        print("-" * 80)
        print(first_message)
        print("-" * 80)
        
        # 提取所有变量
        variables_in_message = re.findall(r'\{\{([^}]+)\}\}', first_message)
        
        print("\n📋 First Message 中使用的变量（精确格式）:")
        print("-" * 80)
        for var in variables_in_message:
            # 显示原始格式（包括空格）
            print(f"  '{{{{ {var} }}}}'")
            # 显示变量名（去除首尾空格）
            var_clean = var.strip()
            print(f"    变量名: '{var_clean}'")
            print(f"    长度: {len(var_clean)}")
            print(f"    包含空格: {'是' if ' ' in var_clean else '否'}")
            if ' ' in var_clean:
                print(f"    空格位置: {[i for i, c in enumerate(var_clean) if c == ' ']}")
            print()
        
        print("\n" + "=" * 80)
        print("📋 我们传递的变量名:")
        print("=" * 80)
        
        # 模拟我们传递的变量
        our_variables = {
            "First Name": "number",
            "Last Name": "random",
            "LOB": "HOME",
            "Company": "Rick insurance",
            "Expiration Date": "November 26, 2025",
            "renewal payment": "one hundred twenty-one thousand six hundred twenty-four dollars"
        }
        
        for var_name, var_value in our_variables.items():
            print(f"  '{var_name}': '{var_value}'")
            print(f"    长度: {len(var_name)}")
            print(f"    包含空格: {'是' if ' ' in var_name else '否'}")
            if ' ' in var_name:
                print(f"    空格位置: {[i for i, c in enumerate(var_name) if c == ' ']}")
            print()
        
        # 检查匹配
        print("\n" + "=" * 80)
        print("🔍 变量名匹配检查:")
        print("=" * 80)
        
        for var_in_message in variables_in_message:
            var_clean = var_in_message.strip()
            if var_clean in our_variables:
                print(f"✅ '{var_clean}' - 匹配")
            else:
                print(f"❌ '{var_clean}' - 不匹配")
                # 尝试查找相似的
                for our_var in our_variables.keys():
                    if var_clean.lower() == our_var.lower():
                        print(f"   ⚠️  大小写不同: '{our_var}'")
                    elif var_clean.replace(' ', '_') == our_var.replace(' ', '_'):
                        print(f"   ⚠️  空格/下划线不同: '{our_var}'")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    debug_variable_names()

