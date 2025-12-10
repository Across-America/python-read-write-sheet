"""
验证 CL1 workflow 时间修改是否正确
检查 UTC 时间到太平洋时间的转换
"""

from datetime import datetime
from zoneinfo import ZoneInfo

# 时区
pacific_tz = ZoneInfo("America/Los_Angeles")
utc_tz = ZoneInfo("UTC")

print("=" * 80)
print("🔍 验证 CL1 Workflow 时间修改")
print("=" * 80)

# 测试时间：UTC 18:00 和 19:00（新的 cron 时间）
test_times_utc = [
    datetime(2025, 6, 15, 18, 0, tzinfo=utc_tz),   # 夏令时期间
    datetime(2025, 6, 15, 19, 0, tzinfo=utc_tz),   # 夏令时期间
    datetime(2025, 12, 15, 18, 0, tzinfo=utc_tz), # 标准时间期间
    datetime(2025, 12, 15, 19, 0, tzinfo=utc_tz),  # 标准时间期间
]

print("\n📅 时区转换验证:")
print("-" * 80)

for utc_time in test_times_utc:
    pacific_time = utc_time.astimezone(pacific_tz)
    hour = pacific_time.hour
    is_11am = hour == 11
    
    status = "✅" if is_11am else "❌"
    print(f"{status} UTC {utc_time.strftime('%H:%M')} = Pacific {pacific_time.strftime('%H:%M %Z')} (小时: {hour})")

print("\n" + "=" * 80)
print("📋 检查结果:")
print("=" * 80)

# 验证逻辑
all_correct = True
for utc_time in test_times_utc:
    pacific_time = utc_time.astimezone(pacific_tz)
    if pacific_time.hour != 11:
        all_correct = False
        print(f"❌ UTC {utc_time.strftime('%H:%M')} 转换后不是 11:00 AM")
        break

if all_correct:
    print("✅ 所有 UTC 时间都正确转换为太平洋时间 11:00 AM")
    print("\n📝 说明:")
    print("   - UTC 18:00 → PDT 11:00 AM (夏令时，3月-11月)")
    print("   - UTC 19:00 → PST 11:00 AM (标准时间，11月-3月)")
    print("   - Python 代码会检查是否为 11:00 AM，只有匹配时才执行")
else:
    print("❌ 时区转换有问题，请检查！")

print("\n" + "=" * 80)
print("🔍 代码检查:")
print("=" * 80)

# 检查 main.py 中的 target_hour
try:
    with open("main.py", "r", encoding="utf-8") as f:
        content = f.read()
        if 'target_hour = 11' in content:
            print("✅ main.py 中 target_hour = 11 (正确)")
        else:
            print("❌ main.py 中 target_hour 不是 11")
        
        if 'not 11:00 AM' in content:
            print("✅ main.py 中日志信息已更新为 11:00 AM")
        else:
            print("⚠️  main.py 中日志信息可能未更新")
except Exception as e:
    print(f"❌ 无法读取 main.py: {e}")

# 检查 workflow 文件
try:
    with open(".github/workflows/daily-cancellation.yml", "r", encoding="utf-8") as f:
        content = f.read()
        if 'cron: "0 18 * * *"' in content and 'cron: "0 19 * * *"' in content:
            print("✅ daily-cancellation.yml 中 cron 时间已更新为 UTC 18:00 和 19:00")
        else:
            print("❌ daily-cancellation.yml 中 cron 时间未正确更新")
        
        if '11:00 AM' in content:
            print("✅ daily-cancellation.yml 中注释已更新为 11:00 AM")
        else:
            print("⚠️  daily-cancellation.yml 中注释可能未更新")
except Exception as e:
    print(f"❌ 无法读取 daily-cancellation.yml: {e}")

print("\n" + "=" * 80)

