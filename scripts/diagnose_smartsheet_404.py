"""
诊断Smartsheet 404错误
检查GitHub Actions中的环境变量和Sheet访问
"""
import sys
import os
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

from config import STM1_SHEET_ID, SMARTSHEET_ACCESS_TOKEN
import smartsheet

def diagnose():
    """诊断404错误"""
    print("=" * 80)
    print("Diagnosing Smartsheet 404 Error")
    print("=" * 80)
    print()
    
    # 检查环境变量
    print("1. Environment Variables")
    print("=" * 80)
    env_token = os.getenv('SMARTSHEET_ACCESS_TOKEN')
    config_token = SMARTSHEET_ACCESS_TOKEN
    
    print(f"   SMARTSHEET_ACCESS_TOKEN from env: {'Set' if env_token else 'Not Set'}")
    if env_token:
        print(f"   Length: {len(env_token)} characters")
        print(f"   Starts with: {env_token[:10]}...")
    
    print(f"   SMARTSHEET_ACCESS_TOKEN from config: {'Set' if config_token else 'Not Set'}")
    if config_token:
        print(f"   Length: {len(config_token)} characters")
        print(f"   Starts with: {config_token[:10]}...")
    
    # 检查是否在GitHub Actions中
    is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
    print(f"\n   GITHUB_ACTIONS: {is_github_actions}")
    
    if is_github_actions:
        print("   [INFO] Running in GitHub Actions")
        if not env_token:
            print("   [ERROR] SMARTSHEET_ACCESS_TOKEN not set in GitHub Actions!")
            print("   [SOLUTION] Add SMARTSHEET_ACCESS_TOKEN to GitHub Secrets")
    else:
        print("   [INFO] Running locally")
    
    print()
    
    # 测试API访问
    print("2. Testing Smartsheet API Access")
    print("=" * 80)
    
    # 使用环境变量中的token（如果存在），否则使用config中的token
    token_to_use = env_token or config_token
    
    if not token_to_use:
        print("[ERROR] No SMARTSHEET_ACCESS_TOKEN available")
        print("   Please set SMARTSHEET_ACCESS_TOKEN environment variable or in .env file")
        return
    
    try:
        smart = smartsheet.Smartsheet(access_token=token_to_use)
        smart.errors_as_exceptions(True)
        
        # 测试1: 获取用户信息
        print("\n   Test 1: Get current user")
        try:
            user = smart.Users.get_current_user()
            print(f"   [OK] API token is valid")
            print(f"      User: {user.email}")
        except Exception as e:
            print(f"   [ERROR] API token invalid: {e}")
            return
        
        # 测试2: 访问Sheet
        print(f"\n   Test 2: Access Sheet ID {STM1_SHEET_ID}")
        try:
            sheet = smart.Sheets.get_sheet(STM1_SHEET_ID)
            print(f"   [OK] Sheet is accessible")
            print(f"      Sheet name: {sheet.name}")
            print(f"      Total rows: {len(sheet.rows)}")
        except smartsheet.exceptions.ApiError as e:
            error_code = e.error.result.code if hasattr(e.error, 'result') else 'Unknown'
            error_message = e.error.result.message if hasattr(e.error, 'result') else str(e)
            status_code = e.error.result.statusCode if hasattr(e.error, 'result') else 'Unknown'
            
            print(f"   [ERROR] Cannot access sheet")
            print(f"      Error code: {error_code}")
            print(f"      Status code: {status_code}")
            print(f"      Message: {error_message}")
            
            if status_code == 404:
                print(f"\n   [DIAGNOSIS] 404 Not Found means:")
                print(f"      - Sheet ID {STM1_SHEET_ID} does not exist")
                print(f"      - OR API token does not have access to this sheet")
                print(f"      - OR Sheet has been deleted or moved")
        except Exception as e:
            print(f"   [ERROR] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
    
    except Exception as e:
        print(f"[ERROR] Failed to initialize Smartsheet client: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # 建议
    print("3. Recommendations")
    print("=" * 80)
    
    if is_github_actions:
        if not env_token:
            print("[CRITICAL] SMARTSHEET_ACCESS_TOKEN not set in GitHub Actions")
            print("   Solution:")
            print("   1. Go to: https://github.com/Across-America/python-read-write-sheet/settings/secrets/actions")
            print("   2. Add or update SMARTSHEET_ACCESS_TOKEN secret")
            print("   3. Make sure the token has access to the STM1 sheet")
        else:
            print("[INFO] SMARTSHEET_ACCESS_TOKEN is set in GitHub Actions")
            print("   If still getting 404, check:")
            print("   1. Token has correct permissions")
            print("   2. Sheet ID is correct")
            print("   3. Sheet still exists and is accessible")
    else:
        print("[INFO] Running locally - check .env file for SMARTSHEET_ACCESS_TOKEN")
    
    print("=" * 80)

if __name__ == "__main__":
    diagnose()
