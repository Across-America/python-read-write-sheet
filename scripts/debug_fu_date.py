"""
调试：查看所有 F/U Date 的客户
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services import SmartsheetService
from config import CANCELLATION_SHEET_ID
from workflows.cancellations import parse_date

smartsheet_service = SmartsheetService(sheet_id=CANCELLATION_SHEET_ID)
all_customers = smartsheet_service.get_all_customers_with_stages()

print("查找所有 F/U Date 包含 '2025-12-05' 或类似格式的客户:")
print("=" * 80)

target_strs = ["2025-12-05", "12-05", "12/05", "12/5", "12-5"]
matching = []
all_fu_dates = set()

for customer in all_customers:
    fu_date_str = str(customer.get('f_u_date', '')).strip()
    if fu_date_str:
        all_fu_dates.add(fu_date_str)
        # 检查是否匹配目标日期
        for target_str in target_strs:
            if target_str in fu_date_str:
        row_num = customer.get('row_number', 'N/A')
        cancellation_date = customer.get('cancellation_date', '')
        done = customer.get('done?', False)
        parsed_fu = parse_date(fu_date_str)
        parsed_cancel = parse_date(cancellation_date) if cancellation_date else None
        
        is_expired = False
        if parsed_fu and parsed_cancel:
            is_expired = parsed_cancel <= parsed_fu
        
        matching.append({
            'row': row_num,
            'fu_date': fu_date_str,
            'cancel_date': cancellation_date,
            'parsed_fu': parsed_fu,
            'parsed_cancel': parsed_cancel,
            'is_expired': is_expired,
            'done': done
        })

print(f"\n找到 {len(matching)} 个匹配的客户:\n")

for m in matching:
    print(f"行 {m['row']}:")
    print(f"  F/U Date (原始): {m['fu_date']}")
    print(f"  F/U Date (解析): {m['parsed_fu']}")
    print(f"  Cancellation Date: {m['cancel_date']} (解析: {m['parsed_cancel']})")
    print(f"  已过期: {m['is_expired']}")
    print(f"  Done: {m['done']}")
    print()

print(f"\n所有唯一的 F/U Date 格式 (前20个):")
for i, fu_date in enumerate(sorted(all_fu_dates)[:20], 1):
    parsed = parse_date(fu_date)
    print(f"  {i}. '{fu_date}' -> {parsed}")

