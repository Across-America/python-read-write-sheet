"""
Verify that the workflow is configured for production mode (actual calls)
This script checks all the conditions that ensure calls will be made
"""
import sys
import os

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("=" * 80)
print("Verifying Production Mode Configuration")
print("=" * 80)
print()

checks_passed = 0
checks_failed = 0

# Check 1: VAPI API Key
print("1. VAPI API Key Check")
print("-" * 80)
vapi_key = os.getenv('VAPI_API_KEY')
if vapi_key:
    print(f"   OK: VAPI_API_KEY is set (length: {len(vapi_key)} characters)")
    checks_passed += 1
else:
    print("   FAIL: VAPI_API_KEY environment variable is not set")
    print("   -> Calls cannot be made without VAPI API key")
    checks_failed += 1
print()

# Check 2: Smartsheet Access Token
print("2. Smartsheet Access Token Check")
print("-" * 80)
smartsheet_token = os.getenv('SMARTSHEET_ACCESS_TOKEN')
if smartsheet_token:
    print(f"   OK: SMARTSHEET_ACCESS_TOKEN is set (length: {len(smartsheet_token)} characters)")
    checks_passed += 1
else:
    print("   FAIL: SMARTSHEET_ACCESS_TOKEN environment variable is not set")
    print("   -> Cannot access Smartsheet without access token")
    checks_failed += 1
print()

# Check 3: GitHub Actions Configuration
print("3. GitHub Actions Configuration Check")
print("-" * 80)
github_actions_file = ".github/workflows/daily-renewal.yml"
if os.path.exists(github_actions_file):
    with open(github_actions_file, 'r', encoding='utf-8') as f:
        content = f.read()
        if '--test' in content:
            print("   WARNING: Found '--test' flag in workflow file")
            print("   -> This would prevent actual calls")
            checks_failed += 1
        else:
            print("   OK: No '--test' flag found in workflow file")
            checks_passed += 1
        
        if 'VAPI_API_KEY' in content:
            print("   OK: VAPI_API_KEY is configured in workflow")
            checks_passed += 1
        else:
            print("   FAIL: VAPI_API_KEY not found in workflow configuration")
            checks_failed += 1
else:
    print(f"   WARNING: Could not find {github_actions_file}")
    print("   -> Cannot verify GitHub Actions configuration")
print()

# Check 4: Process Script Configuration
print("4. Process Script Configuration Check")
print("-" * 80)
process_script = "scripts/process_sheet_by_date.py"
if os.path.exists(process_script):
    with open(process_script, 'r', encoding='utf-8') as f:
        content = f.read()
        if 'test_mode=False' in content or 'test_mode=args.test' in content:
            print("   OK: Script uses test_mode parameter (defaults to False)")
            checks_passed += 1
        else:
            print("   WARNING: Could not verify test_mode configuration")
        
        if 'PRODUCTION MODE' in content:
            print("   OK: Script has production mode logging")
            checks_passed += 1
        else:
            print("   WARNING: Could not find production mode logging")
else:
    print(f"   WARNING: Could not find {process_script}")
print()

# Summary
print("=" * 80)
print("Summary")
print("=" * 80)
print(f"   Checks Passed: {checks_passed}")
print(f"   Checks Failed: {checks_failed}")
print()

if checks_failed == 0:
    print("SUCCESS: All checks passed!")
    print("   -> Workflow is configured for production mode")
    print("   -> Calls will be made when customers are ready")
else:
    print("WARNING: Some checks failed!")
    print("   -> Please review the failed checks above")
    print("   -> Workflow may not make actual calls")

print("=" * 80)

