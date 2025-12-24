"""
Auto start/restart STM1 workflow
"""
import sys
import os
from pathlib import Path

# Fix Windows encoding issue
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import requests
from datetime import datetime
from zoneinfo import ZoneInfo

def cancel_stuck_runs(github_token, repo_owner, repo_name, workflow_file):
    """Cancel stuck workflow runs"""
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        # Get recent runs
        runs_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/workflows/{workflow_file}/runs"
        response = requests.get(runs_url, headers=headers, params={"per_page": 10, "status": "in_progress"}, timeout=10)
        
        if response.status_code != 200:
            print(f"⚠️  Cannot fetch runs: {response.status_code}")
            return False
        
        runs_data = response.json()
        workflow_runs = runs_data.get("workflow_runs", [])
        
        if not workflow_runs:
            print("✅ No stuck runs found")
            return True
        
        cancelled_count = 0
        for run in workflow_runs:
            run_id = run.get("id")
            status = run.get("status")
            
            if status == "in_progress" or status == "queued":
                # Cancel the run
                cancel_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/runs/{run_id}/cancel"
                cancel_response = requests.post(cancel_url, headers=headers, timeout=10)
                
                if cancel_response.status_code == 202:
                    print(f"✅ Cancelled stuck run: {run_id}")
                    cancelled_count += 1
                else:
                    print(f"⚠️  Failed to cancel run {run_id}: {cancel_response.status_code}")
        
        if cancelled_count > 0:
            print(f"✅ Cancelled {cancelled_count} stuck run(s)")
            return True
        else:
            print("✅ No runs needed to be cancelled")
            return True
    
    except Exception as e:
        print(f"❌ Error cancelling runs: {e}")
        return False

def trigger_workflow(github_token, repo_owner, repo_name, workflow_file):
    """Trigger workflow manually"""
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        # Get workflow ID first
        workflows_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/workflows"
        response = requests.get(workflows_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Error fetching workflows: {response.status_code}")
            return False
        
        workflows = response.json().get("workflows", [])
        workflow_id = None
        
        for workflow in workflows:
            if workflow.get("path") == f".github/workflows/{workflow_file}":
                workflow_id = workflow.get("id")
                break
        
        if not workflow_id:
            print(f"❌ Workflow '{workflow_file}' not found")
            return False
        
        # Get default branch
        repo_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        repo_response = requests.get(repo_url, headers=headers, timeout=10)
        default_branch = "master"  # default fallback
        if repo_response.status_code == 200:
            default_branch = repo_response.json().get("default_branch", "master")
        
        # Trigger workflow
        trigger_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/workflows/{workflow_id}/dispatches"
        trigger_data = {
            "ref": default_branch
        }
        
        trigger_response = requests.post(trigger_url, headers=headers, json=trigger_data, timeout=10)
        
        if trigger_response.status_code == 204:
            print("✅ Workflow triggered successfully!")
            return True
        else:
            print(f"❌ Failed to trigger workflow: {trigger_response.status_code}")
            print(f"   Response: {trigger_response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Error triggering workflow: {e}")
        import traceback
        traceback.print_exc()
        return False

def auto_start_stm1():
    """Auto start/restart STM1 workflow"""
    print("=" * 80)
    print("🚀 AUTO START STM1 WORKFLOW")
    print("=" * 80)
    print()
    
    repo_owner = "Across-America"
    repo_name = "python-read-write-sheet"
    workflow_file = "daily-stm1.yml"
    
    github_token = os.getenv("GITHUB_TOKEN")
    
    if not github_token:
        print("❌ GITHUB_TOKEN not found")
        print()
        print("💡 Set token first:")
        print("   $env:GITHUB_TOKEN='your_token'")
        print()
        print("💡 Or enable workflow manually:")
        print(f"   https://github.com/{repo_owner}/{repo_name}/actions/workflows/{workflow_file}")
        print("   → Click 'Run workflow' button")
        return False
    
    # Step 1: Cancel stuck runs
    print("📋 Step 1: Checking for stuck runs...")
    print("-" * 80)
    cancel_stuck_runs(github_token, repo_owner, repo_name, workflow_file)
    print()
    
    # Wait a moment for cancellation to process
    import time
    print("⏳ Waiting 3 seconds for cancellation to process...")
    time.sleep(3)
    print()
    
    # Step 2: Trigger new workflow run
    print("📋 Step 2: Triggering new workflow run...")
    print("-" * 80)
    success = trigger_workflow(github_token, repo_owner, repo_name, workflow_file)
    print()
    
    if success:
        print("=" * 80)
        print("🎉 STM1 WORKFLOW STARTED!")
        print("=" * 80)
        print()
        print("📋 Next steps:")
        print(f"   1. Monitor workflow: https://github.com/{repo_owner}/{repo_name}/actions")
        print(f"   2. Check status: python scripts/check_stm1_running_now.py")
        print(f"   3. Monitor calls: python scripts/monitor_stm1.py")
        print()
        return True
    else:
        print("=" * 80)
        print("❌ FAILED TO START WORKFLOW")
        print("=" * 80)
        print()
        print("💡 Try manually:")
        print(f"   https://github.com/{repo_owner}/{repo_name}/actions/workflows/{workflow_file}")
        print("   → Click 'Run workflow' button")
        print()
        return False

if __name__ == "__main__":
    success = auto_start_stm1()
    sys.exit(0 if success else 1)

