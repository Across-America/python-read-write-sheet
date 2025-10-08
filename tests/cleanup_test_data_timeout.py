#!/usr/bin/env python3
"""
清理工具（带超时） - 删除所有测试数据残留
Use this if cleanup_test_data.py hangs
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services import SmartsheetService
from config import CANCELLATION_SHEET_ID
import signal


class TimeoutError(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutError("操作超时!")


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


def delete_rows_one_by_one(service, row_ids, timeout_seconds=10):
    """逐个删除行（带超时）"""
    deleted_count = 0
    failed_ids = []

    for i, row_id in enumerate(row_ids, 1):
        print(f"\n   🗑️  删除行 {i}/{len(row_ids)} (ID: {row_id})...")

        # Set timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)

        try:
            import time
            start = time.time()
            service.smart.Sheets.delete_rows(CANCELLATION_SHEET_ID, [row_id])
            elapsed = time.time() - start
            signal.alarm(0)  # Cancel timeout

            print(f"      ✅ 成功 ({elapsed:.2f}s)")
            deleted_count += 1

        except TimeoutError:
            signal.alarm(0)
            print(f"      ❌ 超时 ({timeout_seconds}s)")
            failed_ids.append(row_id)

        except Exception as e:
            signal.alarm(0)
            print(f"      ❌ 失败: {e}")
            failed_ids.append(row_id)

    return deleted_count, failed_ids


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

    # 删除测试数据（逐个）
    print(f"\n🧹 删除测试数据（逐个删除，每个超时限制 10s）...")
    row_ids = [row['row_id'] for row in test_rows]

    deleted_count, failed_ids = delete_rows_one_by_one(service, row_ids, timeout_seconds=10)

    # 结果汇总
    print(f"\n" + "=" * 80)
    print(f"📊 删除结果:")
    print(f"   ✅ 成功: {deleted_count}/{len(row_ids)}")
    print(f"   ❌ 失败: {len(failed_ids)}/{len(row_ids)}")

    if failed_ids:
        print(f"\n⚠️  失败的行 IDs:")
        for fid in failed_ids:
            print(f"   • {fid}")
        print(f"\n💡 提示: 请手动在 Smartsheet 中删除这些行")

    # 验证
    print(f"\n🔍 验证删除结果...")
    test_rows_after, _ = find_test_rows()

    if not test_rows_after:
        print("✅ 所有测试数据已清理")
    else:
        print(f"⚠️  仍有 {len(test_rows_after)} 个测试行残留")

    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(1)
