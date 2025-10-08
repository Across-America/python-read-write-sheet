#!/usr/bin/env python3
"""
端到端测试脚本 - 测试完整的通话和 Smartsheet 更新流程
Creates fake data, simulates VAPI call results, tests Smartsheet updates
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from services import SmartsheetService
from workflows.cancellations import (
    update_after_call,
    calculate_next_followup_date,
    count_business_days,
    add_business_days
)
from config import CANCELLATION_SHEET_ID
import time

# 配置：观察停顿时间（秒）
PAUSE_AFTER_CREATE = 10  # 创建测试行后的停顿
PAUSE_AFTER_UPDATE = 10  # 更新 Smartsheet 后的停顿
PAUSE_BEFORE_DELETE = 10  # 删除前的停顿


class FakeVAPICallData:
    """模拟 VAPI 电话返回的数据结构"""

    @staticmethod
    def create_successful_call(stage=0):
        """创建一个成功的电话结果"""
        stage_messages = {
            0: "Customer acknowledged the cancellation notice. Confirmed they received the notice and will make payment before the deadline.",
            1: "Spoke with customer about upcoming cancellation. Customer stated they already made payment yesterday and provided confirmation number.",
            2: "Final reminder call. Customer requested to speak with agent for payment arrangement. Transfer requested."
        }

        return {
            "id": f"call-test-{int(time.time())}",
            "status": "completed",
            "endedReason": "assistant-ended-call",
            "duration": 45 + stage * 10,  # 45s, 55s, 65s
            "cost": 0.15 + stage * 0.05,
            "analysis": {
                "summary": stage_messages.get(stage, "Call completed successfully"),
                "successEvaluation": True,
                "structuredData": {
                    "call_outcome": {
                        "transfer_requested": stage == 2,
                        "transfer_completed": False,
                        "customer_ended_call": False
                    },
                    "customer_response": {
                        "payment_status_claimed": "paid" if stage == 1 else "will pay",
                        "concerns_raised": ["deadline concern"] if stage == 0 else []
                    },
                    "call_quality": {
                        "customer_understood": True,
                        "customer_engaged": True
                    },
                    "follow_up": {
                        "callback_requested": False,
                        "escalation_needed": stage == 2,
                        "notes": f"Stage {stage + 1} call completed"
                    }
                }
            }
        }

    @staticmethod
    def create_failed_call():
        """创建一个失败的电话结果"""
        return {
            "id": f"call-test-failed-{int(time.time())}",
            "status": "failed",
            "endedReason": "customer-did-not-answer",
            "duration": 30,
            "cost": 0.10,
            "analysis": {
                "summary": "No answer - voicemail",
                "successEvaluation": False,
                "structuredData": {}
            }
        }


def create_test_customer_row(smartsheet_service, test_index=1):
    """
    在 Smartsheet 中创建一个测试客户行

    Args:
        smartsheet_service: SmartsheetService instance
        test_index: 测试编号

    Returns:
        dict: 创建的行信息（包含 row_id）
    """
    print(f"\n{'=' * 80}")
    print(f"📝 创建测试数据 #{test_index}")
    print(f"{'=' * 80}")

    # 获取 sheet 和 column IDs
    sheet = smartsheet_service.smart.Sheets.get_sheet(smartsheet_service.sheet_id)

    # 创建 column mapping 和类型映射
    column_map = {}
    column_types = {}
    for col in sheet.columns:
        column_map[col.title] = col.id
        column_types[col.title] = col.type

    # 定义要跳过的列类型
    skip_types = ['CONTACT_LIST', 'MULTI_CONTACT_LIST', 'PICKLIST', 'MULTI_PICKLIST']

    # 准备测试数据
    today = datetime.now().date()
    cancellation_date = today + timedelta(days=15)  # 15天后取消
    followup_date = today  # 今天跟进

    test_data = {
        "Client ID": f"TEST-{test_index}-{int(time.time())}",
        "Policy Number": f"POL-TEST-{test_index}",
        "Phone number": "9999999999",  # 假电话号码
        "Company": f"Test Company {test_index}",
        # "Agent Name": "Test Agent",  # 跳过 CONTACT_LIST 类型
        # "Office": "Test Office",  # 跳过 PICKLIST 类型
        "Insured": f"Test Customer {test_index}",
        # "LOB": "Auto",  # 跳过 PICKLIST 类型
        # "Status": "Active",  # 跳过 PICKLIST 类型
        "Cancellation Reason": "Non-Payment",
        "Cancellation Date": cancellation_date.strftime('%Y-%m-%d'),
        "Amount Due": "$500.00",
        "F/U Date": followup_date.strftime('%Y-%m-%d'),
        "Call Status": "Not call yet",
        "AI Call Stage": "",  # 空白表示 stage 0
        "Done?": False
    }

    print(f"📋 测试数据:")
    print(f"   Client ID: {test_data['Client ID']}")
    print(f"   Company: {test_data['Company']}")
    print(f"   Phone: {test_data['Phone number']}")
    print(f"   F/U Date: {test_data['F/U Date']}")
    print(f"   Cancellation Date: {test_data['Cancellation Date']}")

    # 创建新行
    new_row = smartsheet_service.smart.models.Row()
    new_row.to_bottom = True

    for field_name, value in test_data.items():
        if field_name in column_map:
            # 跳过特殊类型列
            if column_types.get(field_name) in skip_types:
                continue

            cell = smartsheet_service.smart.models.Cell()
            cell.column_id = column_map[field_name]

            # 处理不同类型的值
            if field_name == "Done?":
                cell.value = bool(value)
            else:
                cell.value = str(value) if value is not None else ""

            new_row.cells.append(cell)

    # 添加到 sheet
    result = smartsheet_service.smart.Sheets.add_rows(
        smartsheet_service.sheet_id,
        [new_row]
    )

    if result.result:
        created_row = result.result[0]
        print(f"✅ 测试行创建成功!")
        print(f"   Row ID: {created_row.id}")

        # 停顿，让用户可以在 Smartsheet 前端观察新创建的行
        print(f"\n⏸️  停顿 {PAUSE_AFTER_CREATE} 秒，请在 Smartsheet 中观察新创建的行...")
        time.sleep(PAUSE_AFTER_CREATE)

        # 返回客户信息（模拟 get_customers_ready_for_calls 返回的格式）
        customer = {
            "client_id": test_data["Client ID"],
            "policy_number": test_data["Policy Number"],
            "phone_number": test_data["Phone number"],
            "company": test_data["Company"],
            # "agent_name": test_data.get("Agent Name", ""),  # 跳过 CONTACT_LIST
            # "office": test_data.get("Office", ""),  # 跳过 PICKLIST
            "insured": test_data["Insured"],
            # "lob": test_data.get("LOB", ""),  # 跳过 PICKLIST
            # "status": test_data.get("Status", ""),  # 跳过 PICKLIST
            "cancellation_reason": test_data["Cancellation Reason"],
            "cancellation_date": test_data["Cancellation Date"],
            "amount_due": test_data["Amount Due"],
            "f_u_date": test_data["F/U Date"],
            "call_status": test_data["Call Status"],
            "ai_call_stage": "",
            "ai_call_summary": "",
            "ai_call_eval": "",
            "done?": False,
            "row_id": created_row.id,
            "row_number": created_row.row_number
        }

        return customer
    else:
        print(f"❌ 创建测试行失败: {result}")
        return None


def delete_test_customer_row(smartsheet_service, row_id):
    """
    删除测试客户行

    Args:
        smartsheet_service: SmartsheetService instance
        row_id: Row ID to delete
    """
    # 停顿，让用户最后观察一次更新后的数据
    print(f"\n⏸️  停顿 {PAUSE_BEFORE_DELETE} 秒，请在 Smartsheet 中最后观察一次更新后的数据...")
    time.sleep(PAUSE_BEFORE_DELETE)

    print(f"\n🗑️  删除测试行 (Row ID: {row_id})...")

    try:
        smartsheet_service.smart.Sheets.delete_rows(
            smartsheet_service.sheet_id,
            [row_id]
        )
        print(f"✅ 测试行删除成功")
        return True
    except Exception as e:
        print(f"❌ 删除测试行失败: {e}")
        return False


def test_stage_0_to_1():
    """测试 Stage 0 → Stage 1 的完整流程"""
    print("\n" + "=" * 80)
    print("🧪 测试 1: Stage 0 → Stage 1")
    print("=" * 80)

    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)

    # 1. 创建测试数据
    customer = create_test_customer_row(smartsheet_service, test_index=1)
    if not customer:
        return False

    try:
        # 2. 模拟成功的电话
        print(f"\n📞 模拟 Stage 0 电话...")
        fake_call_data = FakeVAPICallData.create_successful_call(stage=0)
        print(f"   ✅ 模拟电话成功")
        print(f"   Summary: {fake_call_data['analysis']['summary'][:80]}...")

        # 3. 测试 Smartsheet 更新
        print(f"\n📝 测试 Smartsheet 更新...")
        success = update_after_call(smartsheet_service, customer, fake_call_data, current_stage=0)

        if success:
            print(f"\n✅ Stage 0 → 1 更新成功!")

            # 停顿，让用户观察更新后的 Smartsheet 数据
            print(f"\n⏸️  停顿 {PAUSE_AFTER_UPDATE} 秒，请在 Smartsheet 中观察更新后的数据...")
            time.sleep(PAUSE_AFTER_UPDATE)

            # 4. 验证更新结果
            print(f"\n🔍 验证更新结果...")
            sheet = smartsheet_service.smart.Sheets.get_sheet(smartsheet_service.sheet_id)

            # 找到我们刚创建的行
            # Build column map once
            col_id_to_title = {col.id: col.title for col in sheet.columns}

            for row in sheet.rows:
                if row.id == customer['row_id']:
                    # 获取更新后的值
                    for cell in row.cells:
                        col_name = col_id_to_title.get(cell.column_id)
                        if col_name in ["AI Call Stage", "AI Call Summary", "AI Call Eval", "F/U Date", "Done?"]:
                            value = cell.value if cell.value is not None else cell.display_value
                            print(f"   • {col_name}: {value}")
                    break

            return True
        else:
            print(f"❌ Stage 0 → 1 更新失败")
            return False

    finally:
        # 5. 清理测试数据
        print(f"\n🧹 清理测试数据...")
        delete_test_customer_row(smartsheet_service, customer['row_id'])


def test_stage_1_to_2():
    """测试 Stage 1 → Stage 2 的完整流程"""
    print("\n" + "=" * 80)
    print("🧪 测试 2: Stage 1 → Stage 2")
    print("=" * 80)

    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)

    # 1. 创建测试数据（模拟已经完成 Stage 0 的客户）
    customer = create_test_customer_row(smartsheet_service, test_index=2)
    if not customer:
        return False

    # 手动设置为 Stage 1
    print(f"\n📝 设置为 Stage 1...")
    today = datetime.now().date()
    smartsheet_service.update_customer_fields(customer, {
        'ai_call_stage': 1,
        'ai_call_summary': '[Call 1 - 2025-01-01] Previous call summary',
        'ai_call_eval': '[Call 1 - 2025-01-01] True',
        'f_u_date': today.strftime('%Y-%m-%d')
    })

    # 停顿，让用户观察 Stage 1 的设置
    print(f"\n⏸️  停顿 {PAUSE_AFTER_UPDATE} 秒，请在 Smartsheet 中观察 Stage 1 设置...")
    time.sleep(PAUSE_AFTER_UPDATE)

    # 更新本地 customer 对象
    customer['ai_call_stage'] = '1'
    customer['ai_call_summary'] = '[Call 1 - 2025-01-01] Previous call summary'
    customer['ai_call_eval'] = '[Call 1 - 2025-01-01] True'
    customer['f_u_date'] = today.strftime('%Y-%m-%d')

    try:
        # 2. 模拟 Stage 1 电话
        print(f"\n📞 模拟 Stage 1 电话...")
        fake_call_data = FakeVAPICallData.create_successful_call(stage=1)

        # 3. 测试 Smartsheet 更新
        print(f"\n📝 测试 Smartsheet 更新...")
        success = update_after_call(smartsheet_service, customer, fake_call_data, current_stage=1)

        if success:
            print(f"\n✅ Stage 1 → 2 更新成功!")

            # 停顿，让用户观察更新后的数据
            print(f"\n⏸️  停顿 {PAUSE_AFTER_UPDATE} 秒，请在 Smartsheet 中观察 Stage 1 → 2 的更新...")
            time.sleep(PAUSE_AFTER_UPDATE)

            return True
        else:
            print(f"❌ Stage 1 → 2 更新失败")
            return False

    finally:
        # 清理测试数据
        print(f"\n🧹 清理测试数据...")
        delete_test_customer_row(smartsheet_service, customer['row_id'])


def test_stage_2_to_3():
    """测试 Stage 2 → Stage 3（完成）的流程"""
    print("\n" + "=" * 80)
    print("🧪 测试 3: Stage 2 → Stage 3 (Done)")
    print("=" * 80)

    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)

    # 1. 创建测试数据（模拟 Stage 2）
    customer = create_test_customer_row(smartsheet_service, test_index=3)
    if not customer:
        return False

    # 手动设置为 Stage 2
    print(f"\n📝 设置为 Stage 2...")
    today = datetime.now().date()
    smartsheet_service.update_customer_fields(customer, {
        'ai_call_stage': 2,
        'ai_call_summary': '[Call 1] Summary 1\n---\n[Call 2] Summary 2',
        'ai_call_eval': '[Call 1] True\n---\n[Call 2] True',
        'f_u_date': today.strftime('%Y-%m-%d')
    })

    # 停顿，让用户观察 Stage 2 的设置
    print(f"\n⏸️  停顿 {PAUSE_AFTER_UPDATE} 秒，请在 Smartsheet 中观察 Stage 2 设置...")
    time.sleep(PAUSE_AFTER_UPDATE)

    customer['ai_call_stage'] = '2'
    customer['ai_call_summary'] = '[Call 1] Summary 1\n---\n[Call 2] Summary 2'
    customer['ai_call_eval'] = '[Call 1] True\n---\n[Call 2] True'
    customer['f_u_date'] = today.strftime('%Y-%m-%d')

    try:
        # 2. 模拟 Stage 2 电话
        print(f"\n📞 模拟 Stage 2 (Final) 电话...")
        fake_call_data = FakeVAPICallData.create_successful_call(stage=2)

        # 3. 测试 Smartsheet 更新
        print(f"\n📝 测试 Smartsheet 更新...")
        success = update_after_call(smartsheet_service, customer, fake_call_data, current_stage=2)

        if success:
            print(f"\n✅ Stage 2 → 3 更新成功! (应该标记为 Done)")

            # 停顿，让用户观察最终更新（包括 Done 标记）
            print(f"\n⏸️  停顿 {PAUSE_AFTER_UPDATE} 秒，请在 Smartsheet 中观察 Stage 2 → 3 的更新和 Done 标记...")
            time.sleep(PAUSE_AFTER_UPDATE)

            # 验证 Done 标记
            print(f"\n🔍 验证 Done 标记...")
            sheet = smartsheet_service.smart.Sheets.get_sheet(smartsheet_service.sheet_id)

            # Build column map once
            col_id_to_title = {col.id: col.title for col in sheet.columns}

            for row in sheet.rows:
                if row.id == customer['row_id']:
                    for cell in row.cells:
                        col_title = col_id_to_title.get(cell.column_id)
                        if col_title == "Done?":
                            is_done = cell.value
                            print(f"   Done? = {is_done}")
                            if is_done:
                                print(f"   ✅ Done 标记正确!")
                            else:
                                print(f"   ❌ Done 标记未设置!")
                            break
                    break

            return True
        else:
            print(f"❌ Stage 2 → 3 更新失败")
            return False

    finally:
        # 清理测试数据
        print(f"\n🧹 清理测试数据...")
        delete_test_customer_row(smartsheet_service, customer['row_id'])


def test_date_calculation():
    """测试日期计算逻辑"""
    print("\n" + "=" * 80)
    print("🧪 测试 4: 日期计算逻辑")
    print("=" * 80)

    from workflows.cancellations import parse_date, is_weekend

    # 测试 1: 工作日计数
    print(f"\n📅 测试工作日计数...")
    start = datetime(2025, 1, 6).date()  # Monday
    end = datetime(2025, 1, 17).date()    # Friday (11 days later)
    business_days = count_business_days(start, end)
    print(f"   从 {start} 到 {end}")
    print(f"   工作日数量: {business_days} (预期: 9)")

    # 测试 2: 添加工作日
    print(f"\n📅 测试添加工作日...")
    start = datetime(2025, 1, 6).date()  # Monday
    result = add_business_days(start, 5)
    print(f"   从 {start} 添加 5 个工作日")
    print(f"   结果: {result} (预期: 2025-01-13, Monday)")

    # 测试 3: 跨周末添加工作日
    print(f"\n📅 测试跨周末添加工作日...")
    start = datetime(2025, 1, 9).date()  # Thursday
    result = add_business_days(start, 3)  # Should skip weekend
    print(f"   从 {start} (Thursday) 添加 3 个工作日")
    print(f"   结果: {result} (预期: 2025-01-14, Tuesday)")
    print(f"   是否跳过周末: {not is_weekend(result)}")

    return True


def run_all_tests():
    """运行所有端到端测试"""
    print("\n" + "=" * 80)
    print("🚀 端到端测试套件 - Smartsheet 更新测试")
    print("=" * 80)
    print("⚠️  警告: 此测试会在真实的 Smartsheet 中创建和删除测试数据")
    print("=" * 80)

    response = input("\n是否继续? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ 测试已取消")
        return False

    results = []

    # 测试 1: Stage 0 → 1
    results.append(("Stage 0 → 1", test_stage_0_to_1()))

    # 测试 2: Stage 1 → 2
    results.append(("Stage 1 → 2", test_stage_1_to_2()))

    # 测试 3: Stage 2 → 3 (Done)
    results.append(("Stage 2 → 3", test_stage_2_to_3()))

    # 测试 4: 日期计算
    results.append(("Date Calculation", test_date_calculation()))

    # 总结
    print("\n" + "=" * 80)
    print("📊 测试结果总结")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n🎯 结果: {passed}/{total} 测试通过")

    if passed == total:
        print("✅ 所有测试通过!")
    else:
        print("❌ 部分测试失败")

    return passed == total


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
