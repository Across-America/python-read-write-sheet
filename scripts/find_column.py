#!/usr/bin/env python3
"""
查找 Smartsheet 中的列
用于查找 "offered premium" 或其他列
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services import SmartsheetService
from config import (
    RENEWAL_PLR_SHEET_ID,
    CANCELLATION_SHEET_ID,
    RENEWAL_WORKSPACE_NAME
)
try:
    from config.settings import STM1_SHEET_ID
except ImportError:
    STM1_SHEET_ID = None


def find_column_in_sheet(sheet_id, column_name, sheet_name=None):
    """
    在指定的 sheet 中查找列
    
    Args:
        sheet_id: Sheet ID
        column_name: 要查找的列名（支持部分匹配，不区分大小写）
        sheet_name: Sheet 名称（可选，用于显示）
    """
    try:
        print(f"\n{'=' * 80}")
        if sheet_name:
            print(f"🔍 在 Sheet '{sheet_name}' (ID: {sheet_id}) 中查找列: '{column_name}'")
        else:
            print(f"🔍 在 Sheet ID {sheet_id} 中查找列: '{column_name}'")
        print(f"{'=' * 80}")
        
        service = SmartsheetService(sheet_id=sheet_id)
        sheet = service.smart.Sheets.get_sheet(sheet_id)
        
        # 获取所有列
        found_columns = []
        for col in sheet.columns:
            # 不区分大小写的部分匹配
            if column_name.lower() in col.title.lower():
                found_columns.append({
                    'id': col.id,
                    'title': col.title,
                    'type': col.type,
                    'index': col.index,
                    'primary': getattr(col, 'primary', False)
                })
        
        if found_columns:
            print(f"\n✅ 找到 {len(found_columns)} 个匹配的列:\n")
            for col in found_columns:
                print(f"   📋 列名: {col['title']}")
                print(f"      ID: {col['id']}")
                print(f"      类型: {col['type']}")
                print(f"      索引: {col['index']}")
                print(f"      主键: {col['primary']}")
                print()
            
            # 如果找到完全匹配的列，显示详细信息
            exact_match = [c for c in found_columns if c['title'].lower() == column_name.lower()]
            if exact_match:
                print(f"✨ 完全匹配的列:")
                col = exact_match[0]
                print(f"   📋 {col['title']} (ID: {col['id']})")
                print(f"   📝 标准化字段名: {service._normalize_field_name(col['title'])}")
        else:
            print(f"\n❌ 未找到包含 '{column_name}' 的列")
            print(f"\n📋 所有列名:")
            for col in sheet.columns:
                print(f"   • {col.title}")
        
        return found_columns
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return []


def search_all_sheets(column_name):
    """
    在所有主要 sheet 中搜索列
    
    Args:
        column_name: 要查找的列名
    """
    print(f"\n{'=' * 80}")
    print(f"🔍 在所有主要 Sheet 中搜索列: '{column_name}'")
    print(f"{'=' * 80}")
    
    sheets_to_search = [
        (RENEWAL_PLR_SHEET_ID, "Renewal PLR Sheet"),
        (CANCELLATION_SHEET_ID, "Cancellation Sheet"),
    ]
    if STM1_SHEET_ID:
        sheets_to_search.append((STM1_SHEET_ID, "STM1 Sheet"))
    
    all_results = {}
    for sheet_id, sheet_name in sheets_to_search:
        results = find_column_in_sheet(sheet_id, column_name, sheet_name)
        if results:
            all_results[sheet_name] = results
    
    return all_results


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='查找 Smartsheet 中的列')
    parser.add_argument('column_name', nargs='?', default='offered premium',
                       help='要查找的列名（默认: offered premium）')
    parser.add_argument('--sheet-id', type=int, help='指定 Sheet ID（如果不指定，则搜索所有主要 sheet）')
    parser.add_argument('--sheet-name', help='指定 Sheet 名称（用于显示）')
    
    args = parser.parse_args()
    
    if args.sheet_id:
        # 搜索指定的 sheet
        find_column_in_sheet(args.sheet_id, args.column_name, args.sheet_name)
    else:
        # 搜索所有主要 sheet
        search_all_sheets(args.column_name)


if __name__ == "__main__":
    main()

