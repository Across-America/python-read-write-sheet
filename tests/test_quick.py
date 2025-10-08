#!/usr/bin/env python3
"""
快速测试脚本 - 单个测试用例
Creates one test row, simulates call, updates Smartsheet, then cleans up
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from services import SmartsheetService
from workflows.cancellations import update_after_call
from config import CANCELLATION_SHEET_ID
import time


def quick_test():
    """快速测试：创建 → 更新 → 清理"""

    print("\n" + "=" * 80)
    print("⚡️ 快速端到端测试")
    print("=" * 80)
    print("流程: 创建测试行 → 模拟电话 → 更新 Smartsheet → 清理")
    print("=" * 80)

    smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
    sheet = smartsheet_service.smart.Sheets.get_sheet(CANCELLATION_SHEET_ID)

    # 获取列 IDs 和类型
    column_map = {col.title: col.id for col in sheet.columns}
    column_types = {col.title: col.type for col in sheet.columns}
    skip_types = ['CONTACT_LIST', 'MULTI_CONTACT_LIST', 'PICKLIST', 'MULTI_PICKLIST']

    # 准备测试数据
    today = datetime.now().date()
    test_id = int(time.time())

    print(f"\n📝 步骤 1: 创建测试行...")
    test_data = {
        "Client ID": f"TEST-{test_id}",
        "Policy Number": f"POL-TEST-{test_id}",
        "Phone number": "9999999999",
        "Company": f"Test Company {test_id}",
        # "Agent Name": "Test Agent",  # 跳过 CONTACT_LIST 类型
        "Cancellation Date": (today + timedelta(days=15)).strftime('%Y-%m-%d'),
        "Amount Due": "$500.00",
        "F/U Date": today.strftime('%Y-%m-%d'),
        "Done?": False
    }

    # 创建新行
    new_row = smartsheet_service.smart.models.Row()
    new_row.to_bottom = True

    for field_name, value in test_data.items():
        if field_name in column_map:
            # 跳过特殊类型列
            if column_types.get(field_name) in skip_types:
                print(f"   ⏭️  跳过 CONTACT 类型列: {field_name}")
                continue

            cell = smartsheet_service.smart.models.Cell()
            cell.column_id = column_map[field_name]
            cell.value = bool(value) if field_name == "Done?" else str(value)
            new_row.cells.append(cell)

    result = smartsheet_service.smart.Sheets.add_rows(CANCELLATION_SHEET_ID, [new_row])
    created_row = result.result[0]
    row_id = created_row.id

    print(f"✅ 测试行创建成功 (Row ID: {row_id})")

    try:
        # 模拟客户数据
        customer = {
            "client_id": test_data["Client ID"],
            "company": test_data["Company"],
            "cancellation_date": test_data["Cancellation Date"],
            "f_u_date": test_data["F/U Date"],
            "ai_call_summary": "",
            "ai_call_eval": "",
            "row_id": row_id,
            "row_number": created_row.row_number
        }

        # 模拟 VAPI 返回数据
        print(f"\n📞 步骤 2: 模拟电话结果...")
        fake_call = {
            "id": f"call-{test_id}",
            "duration": 45,
            "cost": 0.15,
            "analysis": {
                "summary": "测试电话：客户确认收到通知，承诺在截止日期前付款",
                "successEvaluation": True,
                "structuredData": {}
            }
        }
        print(f"✅ 模拟电话成功")

        # 更新 Smartsheet
        print(f"\n📝 步骤 3: 更新 Smartsheet...")
        success = update_after_call(smartsheet_service, customer, fake_call, current_stage=0)

        if success:
            print(f"\n✅ 测试成功!")

            # 验证更新
            print(f"\n🔍 步骤 4: 验证更新结果...")
            sheet = smartsheet_service.smart.Sheets.get_sheet(CANCELLATION_SHEET_ID)

            # Build column map once
            col_id_to_title = {col.id: col.title for col in sheet.columns}

            for row in sheet.rows:
                if row.id == row_id:
                    print(f"\n更新后的字段值:")
                    for cell in row.cells:
                        col_name = col_id_to_title.get(cell.column_id)
                        if col_name in ["AI Call Stage", "AI Call Summary", "F/U Date"]:
                            value = cell.value if cell.value else cell.display_value
                            print(f"   • {col_name}: {value}")
                    break
        else:
            print(f"❌ 测试失败")

    finally:
        # 清理
        print(f"\n🧹 步骤 5: 清理测试数据...")
        smartsheet_service.smart.Sheets.delete_rows(CANCELLATION_SHEET_ID, [row_id])
        print(f"✅ 测试行已删除")

    print(f"\n" + "=" * 80)
    print("✅ 快速测试完成!")
    print("=" * 80)


if __name__ == "__main__":
    response = input("\n⚠️  将在真实 Smartsheet 中创建测试数据。继续? (y/N): ").strip().lower()
    if response in ['y', 'yes']:
        quick_test()
    else:
        print("❌ 测试已取消")
