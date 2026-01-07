"""
Run renewal workflow as if it were triggered by GitHub Actions cron schedule
This simulates the exact environment GitHub Actions would use
"""
import sys
import os
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

print("=" * 80)
print("Running as GitHub Actions (Cron Schedule)")
print("=" * 80)
print()

# Check current time
pacific_tz = ZoneInfo("America/Los_Angeles")
now_pacific = datetime.now(pacific_tz)
current_hour = now_pacific.hour

print(f"Current Pacific Time: {now_pacific.strftime('%Y-%m-%d %H:%M %p %Z')}")
print(f"Current Hour: {current_hour}")
print()

target_hours = [11, 16]

if current_hour not in target_hours:
    print(f"WARNING: Current time ({current_hour}:00) is NOT 11:00 AM or 4:00 PM Pacific")
    print(f"   In GitHub Actions, the script would SKIP due to time check")
    print()
    print("Options:")
    print("  1. Wait until 11:00 AM or 4:00 PM Pacific")
    print("  2. Use --force flag to bypass time check")
    print()
    
    if '--force' not in sys.argv:
        print("Skipping (use --force to bypass)")
        sys.exit(0)
    else:
        print("FORCE MODE: Bypassing time check")
        # Set as manual trigger to bypass time check
        os.environ['GITHUB_EVENT_NAME'] = 'workflow_dispatch'
else:
    print(f"OK: Current time matches target hours - workflow should run")
    # Simulate cron trigger
    os.environ['GITHUB_EVENT_NAME'] = 'schedule'

print()
print("=" * 80)
print("Executing: python scripts/process_sheet_by_date.py")
print("=" * 80)
print()

# Check if test mode
test_mode = '--test' in sys.argv
if test_mode:
    print("TEST MODE - No actual calls will be made")
    print()

# Run the script
script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'process_sheet_by_date.py')
cmd = [sys.executable, script_path]
if test_mode:
    cmd.append('--test')

try:
    result = subprocess.run(cmd, env=os.environ.copy(), check=False)
    sys.exit(result.returncode)
except KeyboardInterrupt:
    print("\nCancelled by user")
    sys.exit(1)
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

