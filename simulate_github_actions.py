"""
Simulate GitHub Actions environment for testing renewal workflow
This script mimics the conditions when GitHub Actions runs the workflow
"""
import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 80)
print("Simulating GitHub Actions Environment")
print("=" * 80)
print()

# Simulate GitHub Actions environment variables
# When triggered by cron schedule, GITHUB_EVENT_NAME is NOT 'workflow_dispatch'
# So we don't set it (or set it to 'schedule')
original_event_name = os.environ.get('GITHUB_EVENT_NAME')
os.environ['GITHUB_EVENT_NAME'] = 'schedule'  # Simulate cron trigger

print("Environment Variables:")
print(f"  GITHUB_EVENT_NAME: {os.environ.get('GITHUB_EVENT_NAME')} (simulated cron trigger)")
print()

# Check current time
pacific_tz = ZoneInfo("America/Los_Angeles")
now_pacific = datetime.now(pacific_tz)
current_hour = now_pacific.hour

print("Current Time Check:")
print(f"  Pacific Time: {now_pacific.strftime('%Y-%m-%d %H:%M %p %Z')}")
print(f"  Current Hour: {current_hour}")
print()

target_hours = [11, 16]  # 11:00 AM and 4:00 PM

if current_hour not in target_hours:
    print("⚠️  WARNING: Current time is NOT 11:00 AM or 4:00 PM Pacific")
    print(f"   Script will skip due to time check")
    print()
    print("Options:")
    print("  1. Wait until 11:00 AM or 4:00 PM Pacific")
    print("  2. Manually set time by modifying the script")
    print("  3. Force run by setting GITHUB_EVENT_NAME='workflow_dispatch'")
    print()
    
    response = input("Do you want to force run anyway? (y/N): ").strip().lower()
    if response == 'y':
        os.environ['GITHUB_EVENT_NAME'] = 'workflow_dispatch'  # Force run
        print("✅ Forcing run (simulating manual trigger)")
    else:
        print("⏭️  Skipping - time check would prevent run")
        # Restore original
        if original_event_name:
            os.environ['GITHUB_EVENT_NAME'] = original_event_name
        else:
            os.environ.pop('GITHUB_EVENT_NAME', None)
        sys.exit(0)
else:
    print(f"✅ Current time matches target hours ({target_hours}) - workflow should run")
    print()

# Check if weekend
from scripts.process_sheet_by_date import is_weekend
today = now_pacific.date()
if is_weekend(today):
    print(f"⚠️  WARNING: Today is {today.strftime('%A')} (weekend)")
    print("   Script will skip due to weekend check")
    print()
    response = input("Do you want to force run anyway? (y/N): ").strip().lower()
    if response != 'y':
        print("⏭️  Skipping - weekend check would prevent run")
        if original_event_name:
            os.environ['GITHUB_EVENT_NAME'] = original_event_name
        else:
            os.environ.pop('GITHUB_EVENT_NAME', None)
        sys.exit(0)

print()
print("=" * 80)
print("Running Renewal Workflow (Simulating GitHub Actions)")
print("=" * 80)
print()
print("Note: This will make ACTUAL phone calls (not test mode)")
print()

# Confirm before running
response = input("Proceed with actual calls? (y/N): ").strip().lower()
if response != 'y':
    print("⏭️  Cancelled")
    if original_event_name:
        os.environ['GITHUB_EVENT_NAME'] = original_event_name
    else:
        os.environ.pop('GITHUB_EVENT_NAME', None)
    sys.exit(0)

print()
print("🚀 Starting workflow...")
print()

# Import and run the script
try:
    # Import the functions we need
    from scripts.process_sheet_by_date import (
        find_year_folder,
        find_sheet_by_month,
        process_sheet
    )
    
    # Get current date
    now = datetime.now(pacific_tz)
    year = now.year
    month = now.month
    
    print(f"Processing Sheet by Date")
    print(f"Year: {year}, Month: {month}")
    print()
    
    # Find year folder
    print(f"Finding folder for year {year}...")
    folder_id = find_year_folder(year)
    
    if not folder_id:
        print(f"Could not find folder for year {year}")
        sys.exit(1)
    
    print(f"Found year folder (ID: {folder_id})")
    print()
    
    # Find sheet by month
    print(f"Finding sheet for month {month}...")
    sheet_info = find_sheet_by_month(folder_id, month)
    
    if not sheet_info:
        print(f"Could not find sheet for month {month} in year {year} folder")
        sys.exit(1)
    
    print(f"Found sheet: {sheet_info['name']} (ID: {sheet_info['id']})")
    print()
    
    # Process the sheet (NOT in test mode - will make actual calls)
    print("⚠️  WARNING: This will make ACTUAL phone calls!")
    print()
    success = process_sheet(sheet_info['id'], sheet_info['name'], test_mode=False)
    
    if success:
        print()
        print("=" * 80)
        print("✅ Simulation Complete - Calls should have been made")
        print("=" * 80)
    else:
        print()
        print("=" * 80)
        print("❌ Simulation Failed")
        print("=" * 80)
    
except Exception as e:
    print()
    print("=" * 80)
    print(f"❌ Error during simulation: {e}")
    print("=" * 80)
    import traceback
    traceback.print_exc()
finally:
    # Restore original environment
    if original_event_name:
        os.environ['GITHUB_EVENT_NAME'] = original_event_name
    else:
        os.environ.pop('GITHUB_EVENT_NAME', None)

