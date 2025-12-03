"""
生产环境就绪检查
检查系统是否准备好进入生产环境
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import (
    VAPI_API_KEY,
    SMARTSHEET_ACCESS_TOKEN,
    RENEWAL_PLR_SHEET_ID,
    RENEWAL_1ST_REMINDER_ASSISTANT_ID,
    RENEWAL_3RD_REMINDER_ASSISTANT_ID,
    NON_RENEWAL_1ST_REMINDER_ASSISTANT_ID,
    NON_RENEWAL_3RD_REMINDER_ASSISTANT_ID
)
from services.smartsheet_service import SmartsheetService
from services.vapi_service import VAPIService

def check_configuration():
    """检查配置"""
    print("=" * 80)
    print("🔍 配置检查")
    print("=" * 80)
    
    issues = []
    
    # Check API keys
    if not VAPI_API_KEY:
        issues.append("❌ VAPI_API_KEY 未配置")
    else:
        print(f"✅ VAPI_API_KEY: 已配置")
    
    if not SMARTSHEET_ACCESS_TOKEN:
        issues.append("❌ SMARTSHEET_ACCESS_TOKEN 未配置")
    else:
        print(f"✅ SMARTSHEET_ACCESS_TOKEN: 已配置")
    
    # Check Assistant IDs
    assistants = {
        "RENEWAL_1ST_REMINDER_ASSISTANT_ID": RENEWAL_1ST_REMINDER_ASSISTANT_ID,
        "RENEWAL_3RD_REMINDER_ASSISTANT_ID": RENEWAL_3RD_REMINDER_ASSISTANT_ID,
        "NON_RENEWAL_1ST_REMINDER_ASSISTANT_ID": NON_RENEWAL_1ST_REMINDER_ASSISTANT_ID,
        "NON_RENEWAL_3RD_REMINDER_ASSISTANT_ID": NON_RENEWAL_3RD_REMINDER_ASSISTANT_ID,
    }
    
    for name, assistant_id in assistants.items():
        if not assistant_id or assistant_id == "your_assistant_id_here":
            issues.append(f"❌ {name} 未配置或无效")
        else:
            print(f"✅ {name}: {assistant_id[:20]}...")
    
    # Check Sheet ID
    if not RENEWAL_PLR_SHEET_ID:
        issues.append("❌ RENEWAL_PLR_SHEET_ID 未配置")
    else:
        print(f"✅ RENEWAL_PLR_SHEET_ID: {RENEWAL_PLR_SHEET_ID}")
    
    return len(issues) == 0, issues

def check_services():
    """检查服务连接"""
    print("\n" + "=" * 80)
    print("🔍 服务连接检查")
    print("=" * 80)
    
    issues = []
    
    # Check Smartsheet
    try:
        service = SmartsheetService(sheet_id=RENEWAL_PLR_SHEET_ID)
        customers = service.get_all_customers_with_stages()
        print(f"✅ Smartsheet 连接成功: 找到 {len(customers)} 个客户")
    except Exception as e:
        issues.append(f"❌ Smartsheet 连接失败: {e}")
        print(f"❌ Smartsheet 连接失败: {e}")
    
    # Check VAPI (basic check)
    try:
        vapi = VAPIService()
        print(f"✅ VAPI Service 初始化成功")
    except Exception as e:
        issues.append(f"❌ VAPI Service 初始化失败: {e}")
        print(f"❌ VAPI Service 初始化失败: {e}")
    
    return len(issues) == 0, issues

def check_test_coverage():
    """检查测试覆盖"""
    print("\n" + "=" * 80)
    print("🔍 测试覆盖检查")
    print("=" * 80)
    
    warnings = []
    
    print("⚠️  测试状态:")
    print("   ✅ 已测试: Renewal 1st/2nd Reminder (3个客户)")
    print("   ⚠️  未测试: Renewal 3rd Reminder")
    print("   ⚠️  未测试: Non-Renewal 1st/2nd Reminder")
    print("   ⚠️  未测试: Non-Renewal 3rd Reminder")
    print("   ⚠️  未测试: 所有8个客户")
    print("   ⚠️  未测试: 多stage调用流程")
    
    warnings.append("建议在生产前测试所有4种assistant")
    warnings.append("建议在生产前测试所有8个客户")
    warnings.append("建议在生产前测试完整的多stage流程")
    
    return warnings

def main():
    """主函数"""
    print("=" * 80)
    print("🚀 生产环境就绪检查")
    print("=" * 80)
    
    all_ok = True
    
    # Check configuration
    config_ok, config_issues = check_configuration()
    if not config_ok:
        all_ok = False
        print("\n❌ 配置问题:")
        for issue in config_issues:
            print(f"   {issue}")
    
    # Check services
    services_ok, service_issues = check_services()
    if not services_ok:
        all_ok = False
        print("\n❌ 服务连接问题:")
        for issue in service_issues:
            print(f"   {issue}")
    
    # Check test coverage
    test_warnings = check_test_coverage()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 总结")
    print("=" * 80)
    
    if all_ok:
        print("✅ 基础配置和服务连接: 正常")
    else:
        print("❌ 基础配置和服务连接: 有问题，需要修复")
    
    print("\n⚠️  测试覆盖:")
    for warning in test_warnings:
        print(f"   {warning}")
    
    print("\n" + "=" * 80)
    print("💡 建议")
    print("=" * 80)
    
    if all_ok:
        print("✅ 系统基础功能正常，可以开始生产部署")
        print("⚠️  但建议在生产前:")
        print("   1. 测试所有4种assistant (Renewal 1st/2nd, Renewal 3rd, Non-Renewal 1st/2nd, Non-Renewal 3rd)")
        print("   2. 测试所有8个客户")
        print("   3. 验证多stage调用流程")
        print("   4. 进行小规模生产测试（例如：只测试1-2个客户）")
    else:
        print("❌ 系统存在配置或连接问题，需要先修复")
    
    print("=" * 80)
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())



