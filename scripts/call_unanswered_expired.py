"""
拨打之前未接通的过期保单客户
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services import SmartsheetService, VAPIService
from config import CANCELLATION_SHEET_ID
from workflows.cancellations import parse_date, get_call_stage, update_after_call
from datetime import date

# 之前未接通的客户行号（从之前的拨打结果）
UNANSWERED_ROW_NUMBERS = [273, 274, 276, 278, 281, 284, 285, 286]

def call_unanswered_customers():
    """拨打之前未接通的过期保单客户"""
    print("=" * 80)
    print("📞 拨打之前未接通的过期保单客户")
    print("=" * 80)
    
    # 初始化服务
    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
    vapi_service = VAPIService()
    
    # 获取所有客户
    print("\n🔍 加载客户数据...")
    all_customers = smartsheet_service.get_all_customers_with_stages()
    print(f"✅ 加载了 {len(all_customers)} 个客户记录")
    
    # 筛选出未接通的客户
    target_customers = []
    for customer in all_customers:
        row_num = customer.get('row_number')
        if row_num in UNANSWERED_ROW_NUMBERS:
            target_customers.append(customer)
    
    print(f"\n📋 找到 {len(target_customers)} 个未接通的客户:")
    for customer in target_customers:
        row_num = customer.get('row_number', 'N/A')
        phone = customer.get('phone_number', 'N/A')
        company = customer.get('company', 'Unknown')
        cancellation_date = customer.get('cancellation_date', 'N/A')
        print(f"   行 {row_num}: {company} - {phone} (Cancel: {cancellation_date})")
    
    if len(target_customers) == 0:
        print("\n❌ 没有找到未接通的客户")
        return False
    
    # 使用过期保单的 assistant ID
    EXPIRED_POLICY_ASSISTANT_ID = "aec4721c-360c-45b5-ba39-87320eab6fc9"
    
    print(f"\n🤖 使用 Assistant ID: {EXPIRED_POLICY_ASSISTANT_ID}")
    print(f"📞 准备拨打 {len(target_customers)} 个客户")
    print("\n" + "=" * 80)
    
    # 批量拨打
    print("📦 批量拨打模式 (同时拨打所有未接通的客户)")
    results = vapi_service.make_batch_call_with_assistant(
        target_customers,
        EXPIRED_POLICY_ASSISTANT_ID,
        schedule_immediately=True
    )
    
    if results:
        print(f"\n✅ 批量拨打完成")
        
        # 检查结果数量是否匹配
        if len(results) != len(target_customers):
            print(f"   ⚠️  警告: 结果数量 ({len(results)}) 与客户数量 ({len(target_customers)}) 不匹配")
        
        total_success = 0
        total_failed = 0
        
        for i, customer in enumerate(target_customers):
            # 获取对应的 call_data
            if i < len(results):
                call_data = results[i]
            else:
                call_data = results[0] if results else None
            
            if call_data:
                # 检查是否有 analysis，如果没有则尝试刷新
                if 'analysis' not in call_data or not call_data.get('analysis'):
                    print(f"   ⚠️  客户 {i+1} ({customer.get('company', 'Unknown')}): call_data 中没有 analysis")
                    if 'id' in call_data:
                        call_id = call_data['id']
                        print(f"      尝试刷新 call status for call_id: {call_id}")
                        try:
                            refreshed_data = vapi_service.check_call_status(call_id)
                            if refreshed_data and refreshed_data.get('analysis'):
                                call_data = refreshed_data
                                print(f"      ✅ 成功从刷新的 call status 获取 analysis")
                            else:
                                print(f"      ⚠️  刷新的 call status 也没有 analysis")
                        except Exception as e:
                            print(f"      ❌ 刷新 call status 失败: {e}")
                
                # 获取当前 stage（用于更新）
                current_stage = get_call_stage(customer)
                
                # 尝试更新 Smartsheet
                try:
                    success = update_after_call(smartsheet_service, customer, call_data, current_stage)
                    if success:
                        total_success += 1
                    else:
                        print(f"   ❌ 更新 Smartsheet 失败: {customer.get('company', 'Unknown')}")
                        total_failed += 1
                except Exception as e:
                    print(f"   ❌ 更新 Smartsheet 时发生异常: {customer.get('company', 'Unknown')}: {e}")
                    import traceback
                    traceback.print_exc()
                    total_failed += 1
            else:
                print(f"   ❌ 客户 {i+1} ({customer.get('company', 'Unknown')}) 没有 call data")
                total_failed += 1
        
        print(f"\n{'=' * 80}")
        print(f"🏁 拨打完成")
        print(f"{'=' * 80}")
        print(f"   ✅ 成功: {total_success}")
        print(f"   ❌ 失败: {total_failed}")
        print(f"   📊 总计: {len(target_customers)}")
        print(f"{'=' * 80}")
        
        return True
    else:
        print(f"\n❌ 批量拨打失败")
        return False

if __name__ == "__main__":
    print("⚠️  注意: 这将拨打 8 个之前未接通的过期保单客户")
    print("   使用已启用 Voicemail Detection 的 Assistant")
    print()
    
    call_unanswered_customers()

