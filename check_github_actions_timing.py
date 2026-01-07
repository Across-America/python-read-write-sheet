"""
Check GitHub Actions timing and why calls might not be made
"""
import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("=" * 80)
print("GitHub Actions Timing Analysis")
print("=" * 80)
print()

pacific_tz = ZoneInfo("America/Los_Angeles")
utc_tz = ZoneInfo("UTC")

now_pacific = datetime.now(pacific_tz)
now_utc = datetime.now(utc_tz)

print(f"Current Pacific Time: {now_pacific.strftime('%Y-%m-%d %H:%M %p %Z')}")
print(f"Current UTC Time: {now_utc.strftime('%Y-%m-%d %H:%M %p %Z')}")
print(f"Pacific Offset: {now_pacific.utcoffset()}")
print()

print("GitHub Actions Cron Times -> Pacific Time:")
print("-" * 80)

# Check each cron time
cron_times = [
    (18, 0, "11:00 AM PDT (summer)"),
    (19, 0, "11:00 AM PST (winter)"),
    (23, 0, "4:00 PM PDT (summer)"),
    (0, 0, "4:00 PM PST (winter, next day)")
]

for utc_hour, utc_min, description in cron_times:
    if utc_hour == 0:
        # Next day
        utc_dt = datetime(2026, 1, 8, utc_hour, utc_min, tzinfo=utc_tz)
    else:
        utc_dt = datetime(2026, 1, 7, utc_hour, utc_min, tzinfo=utc_tz)
    
    pacific_dt = utc_dt.astimezone(pacific_tz)
    print(f"  UTC {utc_hour:02d}:{utc_min:02d} -> Pacific {pacific_dt.strftime('%I:%M %p %Z')} ({description})")

print()
print("=" * 80)
print("Time Check Logic")
print("=" * 80)
print()

target_hours = [11, 16]  # 11:00 AM and 4:00 PM
current_hour = now_pacific.hour

print(f"Target hours: {target_hours} (11:00 AM and 4:00 PM Pacific)")
print(f"Current hour: {current_hour} ({now_pacific.strftime('%I:%M %p')})")

if current_hour in target_hours:
    print("✅ Current time matches target hours - workflow should run")
else:
    print("❌ Current time does NOT match target hours - workflow will skip")
    print(f"   Workflow will only run at 11:00 AM or 4:00 PM Pacific")

print()
print("=" * 80)
print("Summary")
print("=" * 80)
print()

if current_hour < 11:
    print("⏰ Morning run (11:00 AM) has not happened yet today")
elif current_hour == 11:
    print("⏰ Currently at morning run time (11:00 AM)")
elif current_hour < 16:
    print("⏰ Morning run (11:00 AM) should have happened")
    print("⏰ Afternoon run (4:00 PM) has not happened yet")
elif current_hour == 16:
    print("⏰ Currently at afternoon run time (4:00 PM)")
else:
    print("⏰ Both runs (11:00 AM and 4:00 PM) should have happened today")

print()
print("To check if workflow ran, check GitHub Actions logs:")
print("  https://github.com/Across-America/python-read-write-sheet/actions")

