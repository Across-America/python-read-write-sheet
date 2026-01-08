"""
监控GitHub Actions workflow运行情况
"""
import sys
import os
import requests
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

# Fix Windows encoding issue
if sys.platform == 'win32':
    import io
    if not isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if not isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def get_github_token():
    """获取GitHub token"""
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        # 尝试从.env文件读取
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('GITHUB_TOKEN='):
                        token = line.split('=', 1)[1].strip()
                        break
    return token

def get_workflow_runs(repo_owner, repo_name, workflow_file, token, per_page=10):
    """获取workflow的运行记录"""
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/workflows/{workflow_file}/runs"
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    params = {
        'per_page': per_page
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Failed to get workflow runs: {e}")
        return None

def get_workflow_run_details(repo_owner, repo_name, run_id, token):
    """获取workflow运行的详细信息"""
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/runs/{run_id}"
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Failed to get workflow run details: {e}")
        return None

def get_workflow_run_jobs(repo_owner, repo_name, run_id, token):
    """获取workflow运行的jobs"""
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/runs/{run_id}/jobs"
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Failed to get workflow jobs: {e}")
        return None

def format_duration(seconds):
    """格式化持续时间"""
    if seconds is None:
        return "N/A"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

def format_datetime(dt_str):
    """格式化日期时间"""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        pacific_tz = ZoneInfo("America/Los_Angeles")
        dt_pacific = dt.astimezone(pacific_tz)
        return dt_pacific.strftime('%Y-%m-%d %I:%M %p %Z')
    except:
        return dt_str

def monitor_stm1_workflow():
    """监控STM1 workflow"""
    print("=" * 80)
    print("Monitor GitHub Actions - Daily STM1 Automated Calling")
    print("=" * 80)
    print()
    
    # 配置
    repo_owner = "Across-America"
    repo_name = "python-read-write-sheet"
    workflow_file = "daily-stm1.yml"
    
    # 获取token
    token = get_github_token()
    if not token:
        print("[ERROR] GITHUB_TOKEN not found")
        print("   Please set environment variable GITHUB_TOKEN or add GITHUB_TOKEN=your_token to .env file")
        print()
        print("   How to get token:")
        print("   1. Visit: https://github.com/settings/tokens")
        print("   2. Click 'Generate new token (classic)'")
        print("   3. Select scope: repo (all permissions)")
        print("   4. Generate and copy token")
        return
    
    # 获取workflow运行记录
    print(f"Fetching workflow runs...")
    print(f"   Repository: {repo_owner}/{repo_name}")
    print(f"   Workflow: {workflow_file}")
    print()
    
    runs_data = get_workflow_runs(repo_owner, repo_name, workflow_file, token, per_page=5)
    if not runs_data:
        return
    
    runs = runs_data.get('workflow_runs', [])
    if not runs:
        print("[WARNING] No runs found")
        return
    
    print(f"[OK] Found {len(runs)} recent runs")
    print()
    
    # 显示最近的运行
    print("=" * 80)
    print("Recent Runs")
    print("=" * 80)
    
    for i, run in enumerate(runs, 1):
        run_id = run.get('id')
        status = run.get('status')  # queued, in_progress, completed
        conclusion = run.get('conclusion')  # success, failure, cancelled, null
        created_at = run.get('created_at')
        updated_at = run.get('updated_at')
        head_branch = run.get('head_branch')
        event = run.get('event')  # schedule, workflow_dispatch, push
        
        # 状态图标
        if status == 'completed':
            if conclusion == 'success':
                status_icon = "[OK]"
            elif conclusion == 'failure':
                status_icon = "[FAIL]"
            elif conclusion == 'cancelled':
                status_icon = "[CANCEL]"
            else:
                status_icon = "[WARN]"
        elif status == 'in_progress':
            status_icon = "[RUNNING]"
        elif status == 'queued':
            status_icon = "[QUEUED]"
        else:
            status_icon = "[?]"
        
        print(f"\n{i}. {status_icon} Run #{run_id}")
        print(f"   Status: {status}")
        if conclusion:
            print(f"   Conclusion: {conclusion}")
        print(f"   Event: {event}")
        print(f"   Branch: {head_branch}")
        print(f"   Created: {format_datetime(created_at)}")
        print(f"   Updated: {format_datetime(updated_at)}")
        
        # 获取详细信息
        run_details = get_workflow_run_details(repo_owner, repo_name, run_id, token)
        if run_details:
            duration = run_details.get('run_duration_ms')
            if duration:
                duration_sec = duration / 1000
                print(f"   持续时间: {format_duration(int(duration_sec))}")
            
            html_url = run_details.get('html_url')
            if html_url:
                print(f"   URL: {html_url}")
        
        # 获取jobs信息
        jobs_data = get_workflow_run_jobs(repo_owner, repo_name, run_id, token)
        if jobs_data:
            jobs = jobs_data.get('jobs', [])
            if jobs:
                print(f"   Jobs:")
                for job in jobs:
                    job_name = job.get('name')
                    job_status = job.get('status')
                    job_conclusion = job.get('conclusion')
                    job_duration = job.get('completed_at')
                    job_started = job.get('started_at')
                    
                    if job_status == 'completed':
                        if job_conclusion == 'success':
                            job_icon = "[OK]"
                        elif job_conclusion == 'failure':
                            job_icon = "[FAIL]"
                        else:
                            job_icon = "[WARN]"
                    elif job_status == 'in_progress':
                        job_icon = "[RUNNING]"
                    else:
                        job_icon = "[QUEUED]"
                    
                    print(f"      {job_icon} {job_name}: {job_status}")
                    if job_conclusion:
                        print(f"         Conclusion: {job_conclusion}")
                    if job_started:
                        print(f"         Started: {format_datetime(job_started)}")
                    if job_duration:
                        print(f"         Completed: {format_datetime(job_duration)}")
    
    # 统计信息
    print("\n" + "=" * 80)
    print("Statistics")
    print("=" * 80)
    
    total_runs = len(runs)
    success_count = sum(1 for r in runs if r.get('conclusion') == 'success')
    failure_count = sum(1 for r in runs if r.get('conclusion') == 'failure')
    in_progress_count = sum(1 for r in runs if r.get('status') == 'in_progress')
    queued_count = sum(1 for r in runs if r.get('status') == 'queued')
    
    print(f"   Total runs: {total_runs}")
    print(f"   [OK] Success: {success_count}")
    print(f"   [FAIL] Failure: {failure_count}")
    print(f"   [RUNNING] In progress: {in_progress_count}")
    print(f"   [QUEUED] Queued: {queued_count}")
    
    # 检查最近的运行
    latest_run = runs[0]
    latest_status = latest_run.get('status')
    latest_conclusion = latest_run.get('conclusion')
    
    print("\n" + "=" * 80)
    print("Latest Run Status")
    print("=" * 80)
    
    if latest_status == 'completed':
        if latest_conclusion == 'success':
            print("[OK] Latest run succeeded")
        elif latest_conclusion == 'failure':
            print("[FAIL] Latest run failed")
            print("   Suggestion: Check logs to find the issue")
        else:
            print(f"[WARN] Latest run completed with unknown conclusion: {latest_conclusion}")
    elif latest_status == 'in_progress':
        print("[RUNNING] Latest run is in progress")
        print("   Suggestion: Wait for completion")
    elif latest_status == 'queued':
        print("[QUEUED] Latest run is queued")
        print("   Suggestion: Wait for start")
    else:
        print(f"[?] Latest run status unknown: {latest_status}")
    
    # 提供查看日志的链接
    if latest_run:
        html_url = latest_run.get('html_url')
        if html_url:
            print(f"\nView detailed logs: {html_url}")
    
    print("=" * 80)

if __name__ == "__main__":
    monitor_stm1_workflow()
