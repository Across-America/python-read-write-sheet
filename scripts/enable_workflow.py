"""
Enable GitHub Actions workflow via API
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

def enable_workflow():
    """Enable GitHub Actions workflow"""
    print("=" * 80)
    print("🔧 ENABLING GITHUB ACTIONS WORKFLOW")
    print("=" * 80)
    print()
    
    repo_owner = "Across-America"
    repo_name = "python-read-write-sheet"
    workflow_file = "daily-stm1.yml"
    
    # Check for GitHub token
    github_token = os.getenv("GITHUB_TOKEN")
    
    if not github_token:
        print("❌ GITHUB_TOKEN not found in environment variables")
        print()
        print("💡 To enable workflow via API:")
        print("   1. Create GitHub Personal Access Token:")
        print("      https://github.com/settings/tokens")
        print("      Permissions: repo, workflow")
        print()
        print("   2. Set token:")
        print("      Windows PowerShell: $env:GITHUB_TOKEN='your_token'")
        print("      Windows CMD: set GITHUB_TOKEN=your_token")
        print()
        print("   3. Run this script again")
        print()
        print("💡 Alternative: Enable manually at:")
        print(f"   https://github.com/{repo_owner}/{repo_name}/actions/workflows/{workflow_file}")
        print("   → Click 'Enable workflow' button")
        return False
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        # First, get workflow ID
        print("📡 Fetching workflow information...")
        workflows_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/workflows"
        response = requests.get(workflows_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Error: GitHub API returned status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
        workflows = response.json().get("workflows", [])
        workflow_id = None
        
        for workflow in workflows:
            if workflow.get("path") == f".github/workflows/{workflow_file}":
                workflow_id = workflow.get("id")
                workflow_name = workflow.get("name", "Unknown")
                workflow_state = workflow.get("state", "unknown")
                
                print(f"✅ Found workflow: {workflow_name}")
                print(f"   ID: {workflow_id}")
                print(f"   Current state: {workflow_state}")
                print()
                
                if workflow_state == "active":
                    print("✅ Workflow is already ENABLED!")
                    print("   No action needed.")
                    return True
                
                if workflow_state == "disabled":
                    print("🔧 Enabling workflow...")
                    
                    # Enable workflow
                    enable_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/workflows/{workflow_id}/enable"
                    enable_response = requests.put(enable_url, headers=headers, timeout=10)
                    
                    if enable_response.status_code == 204:
                        print("✅ Workflow ENABLED successfully!")
                        print()
                        print("📋 Next steps:")
                        print("   1. Workflow will run at next scheduled time:")
                        print("      • UTC 16:00 (9 AM PDT)")
                        print("      • UTC 17:00 (9 AM PST)")
                        print()
                        print("   2. Or manually trigger now:")
                        print(f"      https://github.com/{repo_owner}/{repo_name}/actions/workflows/{workflow_file}")
                        print("      → Click 'Run workflow' button")
                        print()
                        return True
                    else:
                        print(f"❌ Error enabling workflow: {enable_response.status_code}")
                        print(f"   Response: {enable_response.text}")
                        return False
                
                print(f"⚠️  Unknown workflow state: {workflow_state}")
                return False
        
        print(f"❌ Workflow '{workflow_file}' not found")
        return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    enable_workflow()

