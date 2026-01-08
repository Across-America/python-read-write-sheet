"""
验证本地和GitHub Secrets中的token是否一致
通过测试token的有效性和访问权限来验证
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

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import STM1_SHEET_ID, SMARTSHEET_ACCESS_TOKEN, VAPI_API_KEY
import smartsheet

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

def get_github_secret_info(repo_owner, repo_name, secret_name, github_token):
    """获取GitHub Secret的信息（不返回值，只返回元数据）"""
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/secrets/{secret_name}"
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None  # Secret不存在
        else:
            return {'error': f'Status {response.status_code}'}
    except Exception as e:
        return {'error': str(e)}

def test_smartsheet_token(token):
    """测试Smartsheet token是否有效"""
    try:
        smart = smartsheet.Smartsheet(access_token=token)
        smart.errors_as_exceptions(True)
        
        # 测试1: 获取用户信息
        user = smart.Users.get_current_user()
        user_email = user.email
        
        # 测试2: 访问STM1 Sheet
        sheet = smart.Sheets.get_sheet(STM1_SHEET_ID)
        sheet_name = sheet.name
        row_count = len(sheet.rows)
        
        return {
            'valid': True,
            'user_email': user_email,
            'sheet_name': sheet_name,
            'row_count': row_count
        }
    except Exception as e:
        return {
            'valid': False,
            'error': str(e)
        }

def test_vapi_token(token):
    """测试VAPI token是否有效"""
    url = "https://api.vapi.ai/assistant"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return {
                'valid': True,
                'message': 'VAPI API accessible'
            }
        else:
            return {
                'valid': False,
                'error': f'Status {response.status_code}: {response.text[:100]}'
            }
    except Exception as e:
        return {
            'valid': False,
            'error': str(e)
        }

def verify_token_sync():
    """验证token同步状态"""
    print("=" * 80)
    print("Verify Token Sync: Local vs GitHub Actions")
    print("=" * 80)
    print()
    
    repo_owner = "Across-America"
    repo_name = "python-read-write-sheet"
    
    # 1. 检查本地token
    print("Step 1: Checking Local Tokens")
    print("=" * 80)
    
    local_smartsheet_token = SMARTSHEET_ACCESS_TOKEN
    local_vapi_token = VAPI_API_KEY
    
    print(f"   SMARTSHEET_ACCESS_TOKEN: {'Set' if local_smartsheet_token else 'Not Set'}")
    if local_smartsheet_token:
        print(f"      Length: {len(local_smartsheet_token)} characters")
        print(f"      Starts with: {local_smartsheet_token[:10]}...")
    
    print(f"   VAPI_API_KEY: {'Set' if local_vapi_token else 'Not Set'}")
    if local_vapi_token:
        print(f"      Length: {len(local_vapi_token)} characters")
        print(f"      Starts with: {local_vapi_token[:10]}...")
    
    print()
    
    # 2. 检查GitHub Secrets是否存在
    print("Step 2: Checking GitHub Secrets")
    print("=" * 80)
    
    github_token = get_github_token()
    if not github_token:
        print("[ERROR] GITHUB_TOKEN not found")
        print("   Cannot verify GitHub Secrets")
        return
    
    smartsheet_secret_info = get_github_secret_info(repo_owner, repo_name, 'SMARTSHEET_ACCESS_TOKEN', github_token)
    vapi_secret_info = get_github_secret_info(repo_owner, repo_name, 'VAPI_API_KEY', github_token)
    
    if smartsheet_secret_info and 'error' not in smartsheet_secret_info:
        print(f"   SMARTSHEET_ACCESS_TOKEN: [OK] Exists in GitHub Secrets")
        if 'updated_at' in smartsheet_secret_info:
            print(f"      Last updated: {smartsheet_secret_info['updated_at']}")
    elif smartsheet_secret_info is None:
        print(f"   SMARTSHEET_ACCESS_TOKEN: [ERROR] Not found in GitHub Secrets")
    else:
        print(f"   SMARTSHEET_ACCESS_TOKEN: [ERROR] {smartsheet_secret_info.get('error', 'Unknown error')}")
    
    if vapi_secret_info and 'error' not in vapi_secret_info:
        print(f"   VAPI_API_KEY: [OK] Exists in GitHub Secrets")
        if 'updated_at' in vapi_secret_info:
            print(f"      Last updated: {vapi_secret_info['updated_at']}")
    elif vapi_secret_info is None:
        print(f"   VAPI_API_KEY: [ERROR] Not found in GitHub Secrets")
    else:
        print(f"   VAPI_API_KEY: [ERROR] {vapi_secret_info.get('error', 'Unknown error')}")
    
    print()
    
    # 3. 测试本地token的有效性
    print("Step 3: Testing Local Token Validity")
    print("=" * 80)
    
    if local_smartsheet_token:
        print("   Testing SMARTSHEET_ACCESS_TOKEN...")
        smartsheet_result = test_smartsheet_token(local_smartsheet_token)
        if smartsheet_result['valid']:
            print(f"   [OK] Token is valid")
            print(f"      User: {smartsheet_result['user_email']}")
            print(f"      Sheet: {smartsheet_result['sheet_name']}")
            print(f"      Rows: {smartsheet_result['row_count']}")
        else:
            print(f"   [ERROR] Token is invalid: {smartsheet_result.get('error', 'Unknown error')}")
    else:
        print("   [SKIP] SMARTSHEET_ACCESS_TOKEN not set locally")
    
    print()
    
    if local_vapi_token:
        print("   Testing VAPI_API_KEY...")
        vapi_result = test_vapi_token(local_vapi_token)
        if vapi_result['valid']:
            print(f"   [OK] Token is valid")
            print(f"      {vapi_result['message']}")
        else:
            print(f"   [ERROR] Token is invalid: {vapi_result.get('error', 'Unknown error')}")
    else:
        print("   [SKIP] VAPI_API_KEY not set locally")
    
    print()
    
    # 4. 总结和建议
    print("=" * 80)
    print("Summary and Recommendations")
    print("=" * 80)
    
    all_ok = True
    recommendations = []
    
    if not local_smartsheet_token:
        all_ok = False
        recommendations.append("   - Set SMARTSHEET_ACCESS_TOKEN in .env file")
    elif not smartsheet_secret_info or 'error' in smartsheet_secret_info:
        all_ok = False
        recommendations.append("   - Run: python scripts/sync_token_to_github_secrets.py")
    elif not smartsheet_result['valid']:
        all_ok = False
        recommendations.append("   - Check SMARTSHEET_ACCESS_TOKEN validity")
    
    if not local_vapi_token:
        all_ok = False
        recommendations.append("   - Set VAPI_API_KEY in .env file")
    elif not vapi_secret_info or 'error' in vapi_secret_info:
        all_ok = False
        recommendations.append("   - Run: python scripts/sync_token_to_github_secrets.py")
    elif not vapi_result['valid']:
        all_ok = False
        recommendations.append("   - Check VAPI_API_KEY validity")
    
    if all_ok:
        print("[OK] All tokens are properly configured and valid!")
        print()
        print("   Local and GitHub Actions should use the same tokens.")
        print("   To ensure they are identical, run:")
        print("      python scripts/sync_token_to_github_secrets.py")
    else:
        print("[WARNING] Some issues detected:")
        for rec in recommendations:
            print(rec)
        print()
        print("   After fixing issues, run:")
        print("      python scripts/sync_token_to_github_secrets.py")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    try:
        verify_token_sync()
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
