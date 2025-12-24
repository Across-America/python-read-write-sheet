"""
Comprehensive STM1 System Check - Check everything!
"""
import sys
import os
from pathlib import Path

# Fix Windows encoding issue
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services import VAPIService
from workflows.stm1 import get_stm1_sheet, validate_stm1_customer_data
from config import STM1_PHONE_NUMBER_ID, STM1_ASSISTANT_ID
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import subprocess
import requests

def check_github_workflow():
    """Check GitHub Actions workflow status"""
    print("\n" + "=" * 80)
    print("1️⃣ GITHUB ACTIONS WORKFLOW STATUS")
    print("=" * 80)
    
    repo_owner = "Across-America"
    repo_name = "python-read-write-sheet"
    workflow_file = "daily-stm1.yml"
    
    github_token = os.getenv("GITHUB_TOKEN")
    
    if github_token:
        try:
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Get workflow info
            workflows_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/workflows"
            response = requests.get(workflows_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                workflows = response.json().get("workflows", [])
                for workflow in workflows:
                    if workflow.get("path") == f".github/workflows/{workflow_file}":
                        workflow_state = workflow.get("state", "unknown")
                        workflow_name = workflow.get("name", "Unknown")
                        
                        print(f"   Workflow: {workflow_name}")
                        print(f"   State: {workflow_state}")
                        
                        if workflow_state == "disabled":
                            print("   ❌ WORKFLOW IS DISABLED!")
                            print("   🔧 Enable at: https://github.com/{}/{}/actions/workflows/{}".format(
                                repo_owner, repo_name, workflow_file))
                        elif workflow_state == "active":
                            print("   ✅ Workflow is ACTIVE")
                        
                        # Get recent runs
                        runs_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/workflows/{workflow_file}/runs"
                        runs_response = requests.get(runs_url, headers=headers, params={"per_page": 5}, timeout=10)
                        
                        if runs_response.status_code == 200:
                            runs_data = runs_response.json()
                            workflow_runs = runs_data.get("workflow_runs", [])
                            
                            if workflow_runs:
                                print(f"   Recent runs: {len(workflow_runs)}")
                                for run in workflow_runs[:3]:
                                    status = run.get("status", "unknown")
                                    conclusion = run.get("conclusion", "N/A")
                                    created_at = run.get("created_at", "")
                                    if created_at:
                                        try:
                                            created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                                            pacific_tz = ZoneInfo("America/Los_Angeles")
                                            created_dt_pacific = created_dt.astimezone(pacific_tz)
                                            time_str = created_dt_pacific.strftime('%Y-%m-%d %I:%M %p %Z')
                                        except:
                                            time_str = created_at
                                    else:
                                        time_str = "N/A"
                                    
                                    icon = "✅" if conclusion == "success" else "❌" if conclusion == "failure" else "🔄" if status == "in_progress" else "⏳"
                                    print(f"      {icon} {time_str} - {status} ({conclusion})")
                        break
            else:
                print(f"   ⚠️  API Error: {response.status_code}")
                print("   💡 Check manually: https://github.com/{}/{}/actions/workflows/{}".format(
                    repo_owner, repo_name, workflow_file))
        except Exception as e:
            print(f"   ⚠️  Error checking via API: {e}")
            print("   💡 Check manually: https://github.com/{}/{}/actions/workflows/{}".format(
                repo_owner, repo_name, workflow_file))
    else:
        print("   ⚠️  GITHUB_TOKEN not set - cannot check via API")
        print("   💡 Check manually: https://github.com/{}/{}/actions/workflows/{}".format(
            repo_owner, repo_name, workflow_file))
        print("   💡 Or set token: $env:GITHUB_TOKEN='your_token'")

def check_local_process():
    """Check if STM1 is running locally"""
    print("\n" + "=" * 80)
    print("2️⃣ LOCAL PROCESS STATUS")
    print("=" * 80)
    
    try:
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV', '/NH'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=5
        )
        
        stm1_found = False
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if 'python.exe' in line.lower():
                    parts = line.split(',')
                    if len(parts) >= 2:
                        pid = parts[1].strip('"')
                        try:
                            wmic_result = subprocess.run(
                                ['wmic', 'process', 'where', f'ProcessId={pid}', 'get', 'CommandLine', '/format:list'],
                                capture_output=True,
                                text=True,
                                encoding='utf-8',
                                errors='ignore',
                                timeout=5
                            )
                            
                            if wmic_result.returncode == 0:
                                for wmic_line in wmic_result.stdout.split('\n'):
                                    if 'CommandLine=' in wmic_line:
                                        cmdline = wmic_line.split('CommandLine=', 1)[1].strip()
                                        if 'auto_stm1_calling.py' in cmdline:
                                            print(f"   ✅ STM1 process found: PID {pid}")
                                            stm1_found = True
                                        break
                        except:
                            pass
        
        if not stm1_found:
            print("   ❌ STM1 process NOT running locally")
            print("   💡 Start with: python scripts/start_stm1.py")
    except Exception as e:
        print(f"   ⚠️  Error checking process: {e}")

def check_vapi_calls():
    """Check VAPI calls today"""
    print("\n" + "=" * 80)
    print("3️⃣ VAPI CALLS STATUS")
    print("=" * 80)
    
    pacific_tz = ZoneInfo("America/Los_Angeles")
    now_pacific = datetime.now(pacific_tz)
    today_start = now_pacific.replace(hour=9, minute=0, second=0, microsecond=0)
    
    try:
        vapi_service = VAPIService(phone_number_id=STM1_PHONE_NUMBER_ID)
        recent_calls = vapi_service.get_recent_calls(limit=100)
        
        if not recent_calls:
            print("   ⚠️  No recent calls found")
            return
        
        # Filter calls from today (since 9 AM)
        calls_today = []
        calls_last_hour = []
        one_hour_ago = now_pacific - timedelta(hours=1)
        
        for call in recent_calls:
            created_at = call.get('createdAt', '')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if created_dt.tzinfo is None:
                            created_dt = pacific_tz.localize(created_dt)
                    else:
                        created_dt = created_at
                    
                    created_dt_pacific = created_dt.astimezone(pacific_tz)
                    
                    if created_dt_pacific >= today_start:
                        calls_today.append({
                            'time': created_dt_pacific,
                            'status': call.get('status', 'unknown'),
                            'ended_reason': call.get('endedReason', 'N/A')
                        })
                    
                    if created_dt_pacific >= one_hour_ago:
                        calls_last_hour.append({
                            'time': created_dt_pacific,
                            'status': call.get('status', 'unknown')
                        })
                except:
                    pass
        
        print(f"   📞 Calls since 9 AM today: {len(calls_today)}")
        print(f"   📞 Calls in last hour: {len(calls_last_hour)}")
        
        if calls_today:
            # Status breakdown
            status_counts = {}
            reason_counts = {}
            transferred_count = 0
            
            for call in calls_today:
                status = call['status']
                reason = call['ended_reason']
                status_counts[status] = status_counts.get(status, 0) + 1
                if reason and reason != 'N/A':
                    reason_counts[reason] = reason_counts.get(reason, 0) + 1
                if reason == 'assistant-forwarded-call':
                    transferred_count += 1
            
            print(f"   📊 Status breakdown:")
            for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
                print(f"      • {status}: {count}")
            
            if transferred_count > 0:
                print(f"   🔄 Transferred calls: {transferred_count}")
            
            # Recent calls
            if calls_last_hour:
                print(f"\n   📋 Recent calls (last hour):")
                for call in sorted(calls_last_hour, key=lambda x: x['time'], reverse=True)[:5]:
                    time_str = call['time'].strftime('%H:%M:%S')
                    print(f"      • {time_str} - {call['status']}")
        else:
            print("   ⚠️  NO CALLS since 9 AM today")
            print("   💡 This suggests workflow may not have run")
    
    except Exception as e:
        print(f"   ❌ Error checking calls: {e}")
        import traceback
        traceback.print_exc()

def check_smartsheet():
    """Check Smartsheet status"""
    print("\n" + "=" * 80)
    print("4️⃣ SMARTSHEET STATUS")
    print("=" * 80)
    
    try:
        smartsheet_service = get_stm1_sheet()
        all_customers = smartsheet_service.get_all_customers_with_stages()
        
        print(f"   📊 Total customers: {len(all_customers)}")
        
        # Count customers with empty called_times
        customers_with_empty_called_times = []
        customers_called_today = []
        
        pacific_tz = ZoneInfo("America/Los_Angeles")
        today_str = datetime.now(pacific_tz).strftime('%Y-%m-%d')
        
        for customer in all_customers:
            called_times = customer.get('called_times', '') or customer.get('called_times_', '')
            if not called_times or called_times == '' or called_times == '0' or str(called_times).strip() == '':
                customers_with_empty_called_times.append(customer)
            
            # Check if called today
            call_notes = customer.get('call_notes', '') or customer.get('stm1_call_notes', '')
            if call_notes and today_str in call_notes:
                customers_called_today.append(customer)
        
        print(f"   📞 Customers with empty called_times: {len(customers_with_empty_called_times)}")
        print(f"   📞 Customers called today: {len(customers_called_today)}")
        
        # Check transfer status
        transferred_customers = [c for c in all_customers 
                                if (c.get('transferred_to_aacs_or_not', '') or '').lower() == 'yes']
        print(f"   🔄 Customers transferred: {len(transferred_customers)}")
        
    except Exception as e:
        print(f"   ❌ Error checking Smartsheet: {e}")
        import traceback
        traceback.print_exc()

def check_calling_hours():
    """Check if within calling hours"""
    print("\n" + "=" * 80)
    print("5️⃣ CALLING HOURS STATUS")
    print("=" * 80)
    
    pacific_tz = ZoneInfo("America/Los_Angeles")
    now_pacific = datetime.now(pacific_tz)
    current_hour = now_pacific.hour
    current_minute = now_pacific.minute
    
    print(f"   ⏰ Current time: {now_pacific.strftime('%I:%M %p %Z')}")
    
    if 9 <= current_hour < 17:
        print("   ✅ Within calling hours (9 AM - 4:55 PM)")
        if current_hour == 16 and current_minute >= 55:
            print("   ⚠️  Close to stop time (4:55 PM)")
    else:
        print("   ⏸️  Outside calling hours (9 AM - 4:55 PM)")
        if current_hour < 9:
            hours_until = 9 - current_hour
            minutes_until = 60 - current_minute
            print(f"   ⏰ Will start in ~{hours_until}h {minutes_until}m")

def check_configuration():
    """Check configuration"""
    print("\n" + "=" * 80)
    print("6️⃣ CONFIGURATION STATUS")
    print("=" * 80)
    
    from config import STM1_ASSISTANT_ID, STM1_PHONE_NUMBER_ID, STM1_CALLING_START_HOUR, STM1_CALLING_END_HOUR
    
    print(f"   🤖 Assistant ID: {STM1_ASSISTANT_ID[:20]}...")
    print(f"   📱 Phone Number ID: {STM1_PHONE_NUMBER_ID[:20]}...")
    print(f"   ⏰ Calling hours: {STM1_CALLING_START_HOUR}:00 AM - {STM1_CALLING_END_HOUR}:00 PM PST")
    
    # Check environment variables
    smartsheet_token = os.getenv("SMARTSHEET_ACCESS_TOKEN")
    vapi_key = os.getenv("VAPI_API_KEY")
    
    print(f"   🔑 SMARTSHEET_ACCESS_TOKEN: {'✅ Set' if smartsheet_token else '❌ Not set'}")
    print(f"   🔑 VAPI_API_KEY: {'✅ Set' if vapi_key else '❌ Not set'}")

def comprehensive_check():
    """Run comprehensive check"""
    print("=" * 80)
    print("🔍 COMPREHENSIVE STM1 SYSTEM CHECK")
    print("=" * 80)
    print(f"⏰ Check time: {datetime.now(ZoneInfo('America/Los_Angeles')).strftime('%I:%M %p %Z')}")
    
    check_github_workflow()
    check_local_process()
    check_vapi_calls()
    check_smartsheet()
    check_calling_hours()
    check_configuration()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY & RECOMMENDATIONS")
    print("=" * 80)
    
    pacific_tz = ZoneInfo("America/Los_Angeles")
    now_pacific = datetime.now(pacific_tz)
    current_hour = now_pacific.hour
    
    print("\n💡 Recommendations:")
    
    if 9 <= current_hour < 17:
        print("   • If workflow is disabled, enable it in GitHub Actions")
        print("   • If no local process, start with: python scripts/start_stm1.py")
        print("   • Monitor calls with: python scripts/monitor_stm1.py")
    else:
        print("   • Outside calling hours - workflow will run tomorrow at 9 AM")
        print("   • Check GitHub Actions to ensure workflow is enabled")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    comprehensive_check()

