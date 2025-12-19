"""快速检查周五运行情况"""
import sys
import io
from pathlib import Path
from datetime import date, timedelta

# 设置输出编码为 UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from workflows.cancellations import is_weekend

print("=" * 70)
print("Friday Run Status Check")
print("=" * 70)

# 找到最近的周五
today = date.today()
days_until_friday = (4 - today.weekday()) % 7
if days_until_friday == 0 and today.weekday() == 4:
    friday = today
elif days_until_friday == 0:
    friday = today - timedelta(days=1)
else:
    friday = today + timedelta(days=days_until_friday)

print(f"\nNext Friday: {friday.strftime('%Y-%m-%d (%A)')}")
print(f"Weekday value: {friday.weekday()} (0=Mon, 4=Fri, 5=Sat, 6=Sun)")
print(f"Is weekend: {is_weekend(friday)}")

if not is_weekend(friday):
    print("\n[OK] Friday is a workday - WILL RUN!")
else:
    print("\n[ERROR] Friday incorrectly identified as weekend!")

print("\n" + "=" * 70)
print("Schedule Configuration:")
print("=" * 70)
print("CL1 (Cancellations): 11:00 AM Pacific (daily, including Friday)")
print("N1 (Renewals):       4:00 PM Pacific (daily, including Friday)")
print("\nGitHub Actions Cron:")
print("  CL1: 0 18 * * * and 0 19 * * * (daily)")
print("  N1:  0 23 * * * and 0 0 * * * (daily)")
print("=" * 70)

