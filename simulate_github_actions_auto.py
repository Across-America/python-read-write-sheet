"""
Simulate GitHub Actions environment - Auto mode (no user interaction)
Usage: python simulate_github_actions_auto.py [--test]
"""
import sys
import os
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

# Set UTF-8 encoding for Windows (only if not already set)
if sys.platform == 'win32' and not hasattr(sys.stdout, 'buffer'):
    import io
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except:
            pass

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def simulate_github_actions(test_mode=False, force_time=False):
    """Simulate GitHub Actions environment"""
    print("=" * 80)
    print("Simulating GitHub Actions Environment")
    print("=" * 80)
    print()
    
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Test mode (no actual calls)')
    parser.add_argument('--force-time', action='store_true', help='Force run even if time check fails')
    args = parser.parse_args()
    
    test_mode = test_mode or args.test
    force_time = force_time or args.force_time
    
    # Simulate GitHub Actions environment
    # When triggered by cron schedule, GITHUB_EVENT_NAME is NOT 'workflow_dispatch'
    original_event_name = os.environ.get('GITHUB_EVENT_NAME')
    
    if force_time:
        # Force run by simulating manual trigger
        os.environ['GITHUB_EVENT_NAME'] = 'workflow_dispatch'
        print("⚠️  FORCE MODE: Simulating manual trigger (bypassing time check)")
    else:
        # Simulate cron trigger
        os.environ['GITHUB_EVENT_NAME'] = 'schedule'
        print("Environment: Simulating cron trigger (GITHUB_EVENT_NAME=schedule)")
    
    print()
    
    # Check current time
    pacific_tz = ZoneInfo("America/Los_Angeles")
    now_pacific = datetime.now(pacific_tz)
    current_hour = now_pacific.hour
    
    print("Time Check:")
    print(f"  Pacific Time: {now_pacific.strftime('%Y-%m-%d %H:%M %p %Z')}")
    print(f"  Current Hour: {current_hour}")
    
    target_hours = [11, 16]  # 11:00 AM and 4:00 PM
    
    if not force_time and current_hour not in target_hours:
        print(f"  ⚠️  Current time is NOT 11:00 AM or 4:00 PM Pacific")
        print(f"  Script would skip due to time check")
        print()
        print("  Use --force-time to bypass time check")
        if original_event_name:
            os.environ['GITHUB_EVENT_NAME'] = original_event_name
        else:
            os.environ.pop('GITHUB_EVENT_NAME', None)
        return False
    else:
        print(f"  ✅ Time check passed (or forced)")
    
    # Check weekend
    from scripts.process_sheet_by_date import is_weekend
    today = now_pacific.date()
    if is_weekend(today) and not force_time:
        print(f"  ⚠️  Today is {today.strftime('%A')} (weekend)")
        print(f"  Script would skip due to weekend check")
        print()
        print("  Use --force-time to bypass weekend check")
        if original_event_name:
            os.environ['GITHUB_EVENT_NAME'] = original_event_name
        else:
            os.environ.pop('GITHUB_EVENT_NAME', None)
        return False
    
    print()
    print("=" * 80)
    if test_mode:
        print("Running Renewal Workflow (TEST MODE - No actual calls)")
    else:
        print("Running Renewal Workflow (PRODUCTION MODE - Will make actual calls)")
    print("=" * 80)
    print()
    
    # Import and run
    try:
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
        if test_mode:
            print("🧪 TEST MODE - No actual calls or updates will be made")
        print()
        
        # Find year folder
        print(f"Finding folder for year {year}...")
        folder_id = find_year_folder(year)
        
        if not folder_id:
            print(f"❌ Could not find folder for year {year}")
            return False
        
        print(f"✅ Found year folder (ID: {folder_id})")
        print()
        
        # Find sheet by month
        print(f"Finding sheet for month {month}...")
        sheet_info = find_sheet_by_month(folder_id, month)
        
        if not sheet_info:
            print(f"❌ Could not find sheet for month {month} in year {year} folder")
            return False
        
        print(f"✅ Found sheet: {sheet_info['name']} (ID: {sheet_info['id']})")
        print()
        
        # Process the sheet
        success = process_sheet(sheet_info['id'], sheet_info['name'], test_mode=test_mode)
        
        if success:
            print()
            print("=" * 80)
            if test_mode:
                print("✅ Simulation Complete (TEST MODE)")
            else:
                print("✅ Simulation Complete - Calls should have been made")
            print("=" * 80)
            return True
        else:
            print()
            print("=" * 80)
            print("❌ Simulation Failed")
            print("=" * 80)
            return False
        
    except Exception as e:
        print()
        print("=" * 80)
        print(f"❌ Error during simulation: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Restore original environment
        if original_event_name:
            os.environ['GITHUB_EVENT_NAME'] = original_event_name
        else:
            os.environ.pop('GITHUB_EVENT_NAME', None)


if __name__ == "__main__":
    success = simulate_github_actions()
    sys.exit(0 if success else 1)

