"""
同步本地.env文件中的token到GitHub Secrets
自动将SMARTSHEET_ACCESS_TOKEN和VAPI_API_KEY同步到GitHub Secrets
"""
import sys
import os
import requests
import base64
import json
from pathlib import Path

# Fix Windows encoding issue
if sys.platform == 'win32':
    import io
    if not isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if not isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    from nacl import encoding, public
except ImportError:
    print("[ERROR] PyNaCl library is required for encrypting secrets")
    print("   Install it with: pip install pynacl")
    sys.exit(1)

def get_github_token():
    """获取GitHub Personal Access Token"""
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

def get_local_env_tokens():
    """从.env文件读取本地token"""
    env_path = Path(__file__).parent.parent / '.env'
    tokens = {}
    
    if not env_path.exists():
        print(f"[ERROR] .env file not found at {env_path}")
        return tokens
    
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                
                if key in ['SMARTSHEET_ACCESS_TOKEN', 'VAPI_API_KEY']:
                    tokens[key] = value
    
    return tokens

def get_repo_public_key(owner, repo, github_token):
    """获取仓库的public key用于加密secrets"""
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/public-key"
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Failed to get public key: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Status code: {e.response.status_code}")
            print(f"   Response: {e.response.text}")
        return None

def encrypt_secret(public_key: str, secret_value: str) -> str:
    """使用public key加密secret值"""
    public_key_bytes = base64.b64decode(public_key)
    public_key_obj = public.PublicKey(public_key_bytes)
    box = public.SealedBox(public_key_obj)
    encrypted = box.encrypt(secret_value.encode('utf-8'))
    return base64.b64encode(encrypted).decode('utf-8')

def update_github_secret(owner, repo, secret_name, encrypted_value, key_id, github_token):
    """更新GitHub Secret"""
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/{secret_name}"
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
    }
    data = {
        'encrypted_value': encrypted_value,
        'key_id': key_id
    }
    
    try:
        response = requests.put(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to update secret {secret_name}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Status code: {e.response.status_code}")
            print(f"   Response: {e.response.text}")
        return False

def sync_tokens():
    """同步本地token到GitHub Secrets"""
    print("=" * 80)
    print("Sync Local Tokens to GitHub Secrets")
    print("=" * 80)
    print()
    
    # 1. 获取GitHub token
    github_token = get_github_token()
    if not github_token:
        print("[ERROR] GITHUB_TOKEN not found")
        print("   Please set GITHUB_TOKEN environment variable or add it to .env file")
        print("   GITHUB_TOKEN is a Personal Access Token with 'repo' scope")
        return False
    
    print(f"[OK] GitHub token found (starts with: {github_token[:10]}...)")
    print()
    
    # 2. 获取本地token
    local_tokens = get_local_env_tokens()
    if not local_tokens:
        print("[ERROR] No tokens found in .env file")
        print("   Make sure SMARTSHEET_ACCESS_TOKEN and/or VAPI_API_KEY exist in .env")
        return False
    
    print("Local tokens found:")
    for key in local_tokens:
        value = local_tokens[key]
        print(f"   {key}: {len(value)} characters (starts with: {value[:10]}...)")
    print()
    
    # 3. 获取仓库信息
    # 默认仓库：Across-America/python-read-write-sheet
    repo_owner = "Across-America"
    repo_name = "python-read-write-sheet"
    
    print(f"Repository: {repo_owner}/{repo_name}")
    print()
    
    # 4. 获取public key
    print("Step 1: Getting repository public key...")
    public_key_info = get_repo_public_key(repo_owner, repo_name, github_token)
    if not public_key_info:
        print("[ERROR] Failed to get public key")
        return False
    
    public_key = public_key_info['key']
    key_id = public_key_info['key_id']
    print(f"[OK] Public key retrieved (key_id: {key_id})")
    print()
    
    # 5. 更新每个secret
    success_count = 0
    failed_secrets = []
    
    for secret_name, secret_value in local_tokens.items():
        print(f"Step 2: Updating {secret_name}...")
        
        # 加密secret
        try:
            encrypted_value = encrypt_secret(public_key, secret_value)
        except Exception as e:
            print(f"[ERROR] Failed to encrypt {secret_name}: {e}")
            failed_secrets.append(secret_name)
            continue
        
        # 更新GitHub Secret
        if update_github_secret(repo_owner, repo_name, secret_name, encrypted_value, key_id, github_token):
            print(f"[OK] {secret_name} updated successfully")
            success_count += 1
        else:
            print(f"[ERROR] Failed to update {secret_name}")
            failed_secrets.append(secret_name)
        print()
    
    # 6. 总结
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"   Successfully updated: {success_count} secret(s)")
    if failed_secrets:
        print(f"   Failed to update: {len(failed_secrets)} secret(s)")
        print(f"   Failed secrets: {', '.join(failed_secrets)}")
    else:
        print("   All secrets updated successfully!")
    print()
    
    if success_count > 0:
        print("[INFO] Secrets have been updated in GitHub")
        print("   Next steps:")
        print("   1. Go to: https://github.com/Across-America/python-read-write-sheet/settings/secrets/actions")
        print("   2. Verify the secrets are updated")
        print("   3. Re-run the workflow to test")
        print()
    
    return len(failed_secrets) == 0

if __name__ == "__main__":
    try:
        success = sync_tokens()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
