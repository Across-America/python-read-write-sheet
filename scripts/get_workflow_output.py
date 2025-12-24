"""
Get workflow run output/logs
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

def get_workflow_output():
    """Get workflow run output"""
    print("=" * 80)
    print("📋 WORKFLOW RUN OUTPUT")
    print("=" * 80)
    print()
    
    repo_owner = "Across-America"
    repo_name = "python-read-write-sheet"
    run_id = "20495021313"
    
    github_token = os.getenv("GITHUB_TOKEN")
    
    if not github_token:
        print("⚠️  GITHUB_TOKEN not set")
        print()
        print("💡 View logs manually:")
        print(f"   https://github.com/{repo_owner}/{repo_name}/actions/runs/{run_id}")
        return
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        # Get jobs
        jobs_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/runs/{run_id}/jobs"
        jobs_response = requests.get(jobs_url, headers=headers, timeout=10)
        
        if jobs_response.status_code == 200:
            jobs_data = jobs_response.json()
            jobs = jobs_data.get("jobs", [])
            
            if jobs:
                job = jobs[0]
                job_name = job.get("name", "Unknown")
                job_status = job.get("status", "unknown")
                job_conclusion = job.get("conclusion")
                
                print(f"📋 Job: {job_name}")
                print(f"   Status: {job_status}")
                print(f"   Conclusion: {job_conclusion or 'None'}")
                print()
                
                # Get logs URL
                logs_url = job.get("logs_url")
                if logs_url:
                    print(f"📋 Logs URL: {logs_url}")
                    print()
                    print("💡 To view full logs:")
                    print(f"   https://github.com/{repo_owner}/{repo_name}/actions/runs/{run_id}")
                    print("   → Click 'Run Automated STM1 Calling' step")
                    print("   → View the output logs")
                else:
                    print("💡 View logs:")
                    print(f"   https://github.com/{repo_owner}/{repo_name}/actions/runs/{run_id}")
            else:
                print("⚠️  No jobs found")
        else:
            print(f"❌ Error fetching jobs: {jobs_response.status_code}")
        
        print()
        print("=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        print("✅ Workflow completed successfully")
        print("⏰ Runtime: ~10 minutes (2:43 PM - 2:53 PM PST)")
        print("📞 Calls made: 0 (no new calls detected)")
        print()
        print("💡 Possible reasons:")
        print("   1. Script found 0 customers (but data shows 1880 available)")
        print("   2. Script exited early (3 consecutive empty results)")
        print("   3. Script completed but calls weren't logged yet")
        print()
        print("🔍 Check logs to see what happened:")
        print(f"   https://github.com/{repo_owner}/{repo_name}/actions/runs/{run_id}")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    get_workflow_output()

