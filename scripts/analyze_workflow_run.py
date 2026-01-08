"""
分析GitHub Actions workflow运行情况
检查是否拨打了电话，是否有call notes等
"""
import sys
import os
import requests
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
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('GITHUB_TOKEN='):
                        token = line.split('=', 1)[1].strip()
                        break
    return token

def get_workflow_run(repo_owner, repo_name, run_id, token):
    """获取workflow运行信息"""
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
        print(f"[ERROR] Failed to get workflow run: {e}")
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

def get_job_logs(repo_owner, repo_name, job_id, token):
    """获取job的日志"""
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/jobs/{job_id}/logs"
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"[ERROR] Failed to get job logs: {e}")
        return None

def analyze_workflow_run(run_id=None):
    """分析workflow运行情况"""
    print("=" * 80)
    print("Analyze GitHub Actions Workflow Run")
    print("=" * 80)
    print()
    
    repo_owner = "Across-America"
    repo_name = "python-read-write-sheet"
    
    token = get_github_token()
    if not token:
        print("[ERROR] GITHUB_TOKEN not found")
        return
    
    # 如果没有指定run_id，获取最新的运行
    if not run_id:
        from scripts.monitor_github_actions import get_workflow_runs
        runs_data = get_workflow_runs(repo_owner, repo_name, "daily-stm1.yml", token, per_page=1)
        if runs_data and runs_data.get('workflow_runs'):
            run_id = runs_data['workflow_runs'][0].get('id')
            print(f"Using latest run: {run_id}")
        else:
            print("[ERROR] No runs found")
            return
    
    print(f"Analyzing run: {run_id}")
    print()
    
    # 获取workflow运行信息
    run_info = get_workflow_run(repo_owner, repo_name, run_id, token)
    if run_info:
        print("=" * 80)
        print("Workflow Run Information")
        print("=" * 80)
        print(f"Status: {run_info.get('status')}")
        print(f"Conclusion: {run_info.get('conclusion')}")
        print(f"Event: {run_info.get('event')}")
        print(f"Branch: {run_info.get('head_branch')}")
        print(f"Created: {run_info.get('created_at')}")
        print(f"Updated: {run_info.get('updated_at')}")
        print(f"Duration: {run_info.get('run_duration_ms', 0) / 1000:.1f} seconds")
        print()
    
    # 获取jobs
    jobs_data = get_workflow_run_jobs(repo_owner, repo_name, run_id, token)
    if not jobs_data:
        return
    
    jobs = jobs_data.get('jobs', [])
    if not jobs:
        print("[WARNING] No jobs found")
        return
    
    print(f"Found {len(jobs)} job(s)")
    print()
    
    # 分析每个job的日志
    for job in jobs:
        job_id = job.get('id')
        job_name = job.get('name')
        job_status = job.get('status')
        job_conclusion = job.get('conclusion')
        
        print("=" * 80)
        print(f"Job: {job_name}")
        print(f"Status: {job_status}")
        if job_conclusion:
            print(f"Conclusion: {job_conclusion}")
        print("=" * 80)
        print()
        
        # 获取日志
        print("Fetching logs...")
        logs = get_job_logs(repo_owner, repo_name, job_id, token)
        
        if not logs:
            print("[ERROR] Could not fetch logs")
            continue
        
        log_lines = logs.split('\n')
        print(f"Total log lines: {len(log_lines)}")
        print()
        
        # 分析关键信息
        print("=" * 80)
        print("Key Metrics")
        print("=" * 80)
        
        # 统计
        metrics = {
            'script_started': 0,
            'services_initialized': 0,
            'customers_loaded': 0,
            'calls_initiated': 0,
            'calls_completed': 0,
            'smartsheet_updated': 0,
            'errors': 0,
            'warnings': 0,
        }
        
        key_phrases = {
            'script_started': ['AUTOMATED STM1 CALLING', 'Running from'],
            'services_initialized': ['INITIALIZING SERVICES', 'Services initialized'],
            'customers_loaded': ['Loading customers', 'Found.*customers'],
            'calls_initiated': ['Call #', 'Call initiated', 'Initiating call'],
            'calls_completed': ['Call completed', 'Call ended'],
            'smartsheet_updated': ['Smartsheet updated', 'Call Notes: Updated'],
            'errors': ['ERROR', 'Failed', 'Exception', '404', 'Not Found'],
            'warnings': ['WARNING', 'Too early', 'No customers'],
        }
        
        for line in log_lines:
            line_lower = line.lower()
            for metric, phrases in key_phrases.items():
                for phrase in phrases:
                    if phrase.lower() in line_lower:
                        metrics[metric] += 1
                        break
        
        # 显示统计
        print(f"Script Started: {metrics['script_started']} occurrence(s)")
        print(f"Services Initialized: {metrics['services_initialized']} occurrence(s)")
        print(f"Customers Loaded: {metrics['customers_loaded']} occurrence(s)")
        print(f"Calls Initiated: {metrics['calls_initiated']} occurrence(s)")
        print(f"Calls Completed: {metrics['calls_completed']} occurrence(s)")
        print(f"Smartsheet Updated: {metrics['smartsheet_updated']} occurrence(s)")
        print(f"Errors: {metrics['errors']} occurrence(s)")
        print(f"Warnings: {metrics['warnings']} occurrence(s)")
        print()
        
        # 查找具体的call记录
        print("=" * 80)
        print("Call Records")
        print("=" * 80)
        
        call_records = []
        for i, line in enumerate(log_lines):
            if 'Call #' in line or 'Call initiated' in line:
                # 获取上下文（前后各5行）
                start = max(0, i - 5)
                end = min(len(log_lines), i + 10)
                context = '\n'.join(log_lines[start:end])
                call_records.append({
                    'line_num': i + 1,
                    'context': context
                })
        
        if call_records:
            print(f"Found {len(call_records)} call record(s)")
            print()
            # 只显示前5个
            for i, record in enumerate(call_records[:5], 1):
                print(f"Call Record #{i} (Line {record['line_num']}):")
                print(record['context'][:300])
                print()
        else:
            print("[WARNING] No call records found!")
            print("   This means no calls were initiated during this run.")
            print()
        
        # 查找错误
        if metrics['errors'] > 0:
            print("=" * 80)
            print("Errors Found")
            print("=" * 80)
            
            error_lines = []
            for i, line in enumerate(log_lines):
                if any(keyword in line for keyword in ['ERROR', 'Failed', 'Exception', '404', 'Not Found']):
                    error_lines.append({
                        'line_num': i + 1,
                        'line': line[:200]
                    })
            
            # 显示前10个错误
            for error in error_lines[:10]:
                try:
                    error_line = error['line'].encode('ascii', errors='replace').decode('ascii')
                    print(f"Line {error['line_num']}: {error_line}")
                except:
                    print(f"Line {error['line_num']}: [Error displaying line]")
            print()
        
        # 查找关键时间点
        print("=" * 80)
        print("Timeline")
        print("=" * 80)
        
        timeline = []
        for i, line in enumerate(log_lines):
            if any(phrase in line for phrase in [
                'AUTOMATED STM1 CALLING',
                'INITIALIZING SERVICES',
                'Loading customers',
                'Call #',
                'Call initiated',
                'Smartsheet updated',
                'STOPPING',
                'Summary'
            ]):
                timeline.append({
                    'line_num': i + 1,
                    'event': line[:100]
                })
        
        # 显示前20个时间点
        for event in timeline[:20]:
            print(f"Line {event['line_num']}: {event['event']}")
        print()
        
        # 最后50行（最重要的部分）
        print("=" * 80)
        print("Last 50 Lines (Most Recent Activity)")
        print("=" * 80)
        last_lines = log_lines[-50:]
        for line in last_lines:
            if line.strip():  # 只显示非空行
                print(line)
        print()
        
        # 总结
        print("=" * 80)
        print("Summary")
        print("=" * 80)
        
        if metrics['calls_initiated'] > 0:
            print(f"[OK] {metrics['calls_initiated']} call(s) were initiated")
        else:
            print("[WARNING] No calls were initiated")
            print("   Possible reasons:")
            print("   1. Time check prevented calling (too early)")
            print("   2. No customers with empty called_times")
            print("   3. Smartsheet access failed")
            print("   4. Workflow was cancelled before calls started")
        
        if metrics['smartsheet_updated'] > 0:
            print(f"[OK] {metrics['smartsheet_updated']} Smartsheet update(s) succeeded")
        else:
            print("[WARNING] No Smartsheet updates detected")
            print("   This means call_notes were not updated")
        
        if metrics['errors'] > 0:
            print(f"[WARNING] {metrics['errors']} error(s) detected - check logs above")
        
        if job_conclusion == 'cancelled':
            print("[INFO] Workflow was cancelled")
            print("   This may explain why there are no call notes")
            print("   The workflow may have been manually cancelled or timed out")
        
        print()
        print(f"Full logs URL: https://github.com/{repo_owner}/{repo_name}/actions/runs/{run_id}")
        print("=" * 80)

if __name__ == "__main__":
    import sys
    run_id = None
    if len(sys.argv) > 1:
        run_id = sys.argv[1]
    analyze_workflow_run(run_id)
