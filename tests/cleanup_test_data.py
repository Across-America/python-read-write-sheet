#!/usr/bin/env python3
"""
清理工具 - 删除所有测试数据残留
Use this if test data was not cleaned up properly
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services import SmartsheetService
from config import CANCELLATION_SHEET_ID


def find_test_rows():
    """查找所有测试数据行"""
    print("\n" + "=" * 80)
    print("🔍 搜索测试数据...")
    print("=" * 80)

    service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
    sheet = service.smart.Sheets.get_sheet(CANCELLATION_SHEET_ID)

    # Build column map once
    col_id_to_title = {col.id: col.title for col in sheet.columns}

    test_rows = []

    for row in sheet.rows:
        # 检查关键字段是否包含测试标识
        is_test_row = False
        row_info = {
            'row_id': row.id,
            'row_number': row.row_number,
            'client_id': '',
            'company': '',
            'phone_number': ''
        }

        for cell in row.cells:
            col_title = col_id_to_title.get(cell.column_id)
            if not col_title:
                continue

            value = str(cell.display_value) if cell.display_value else ''

            if col_title == 'Client ID':
                row_info['client_id'] = value
                if 'TEST-' in value.upper():
                    is_test_row = True

            elif col_title == 'Company':
                row_info['company'] = value
                if 'TEST COMPANY' in value.upper():
                    is_test_row = True

            elif col_title == 'Phone number':
                row_info['phone_number'] = value
                if value == '9999999999':
                    is_test_row = True

        if is_test_row:
            test_rows.append(row_info)

    return test_rows, service


def main():
    """主函数"""
    # 查找测试数据
    test_rows, service = find_test_rows()

    if not test_rows:
        print("\n✅ 没有发现测试数据残留")
        print("=" * 80)
        return

    # 显示找到的测试数据
    print(f"\n⚠️  发现 {len(test_rows)} 个测试行:")
    print("-" * 80)

    for row in test_rows:
        print(f"\n行 {row['row_number']} (Row ID: {row['row_id']})")
        print(f"  Client ID: {row['client_id']}")
        print(f"  Company: {row['company']}")
        print(f"  Phone: {row['phone_number']}")

    print("\n" + "=" * 80)

    # 询问是否删除
    response = input(f"\n是否删除这 {len(test_rows)} 个测试行? (y/N): ").strip().lower()

    if response not in ['y', 'yes']:
        print("❌ 清理已取消")
        return

    # 删除测试数据
    print(f"\n🧹 删除测试数据...")
    row_ids = [row['row_id'] for row in test_rows]

    print(f"   🔄 正在调用 Smartsheet API...")
    print(f"   📋 删除 {len(row_ids)} 个行: {row_ids}")

    try:
        import time
        start = time.time()
        result = service.smart.Sheets.delete_rows(CANCELLATION_SHEET_ID, row_ids)
        elapsed = time.time() - start
        print(f"   ⏱️  API 调用耗时: {elapsed:.2f}s")
        print(f"✅ 成功删除 {len(test_rows)} 个测试行")
    except Exception as e:
        print(f"❌ 删除失败: {e}")
        import traceback
        traceback.print_exc()

    # 验证
    print(f"\n🔍 验证删除结果...")
    test_rows_after, _ = find_test_rows()

    if not test_rows_after:
        print("✅ 所有测试数据已清理")
    else:
        print(f"⚠️  仍有 {len(test_rows_after)} 个测试行残留")

    print("=" * 80)


if __name__ == "__main__":
    main()
