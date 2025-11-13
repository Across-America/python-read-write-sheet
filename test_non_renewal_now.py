#!/usr/bin/env python3
"""
测试运行 Non-Renewal Workflow（测试模式）
"""
import sys
import io
import os

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Set workflow type
os.environ['WORKFLOW_TYPE'] = 'non_renewals'

from workflows.non_renewals import run_non_renewals_calling

print("=" * 80)
print("🧪 测试模式 - Non-Renewal Workflow")
print("=" * 80)
print("⚠️  这是测试模式，不会实际拨打电话")
print("=" * 80)
print()

# Run in test mode
success = run_non_renewals_calling(
    test_mode=True,      # Test mode - no actual calls
    schedule_at=None,     # Call immediately
    auto_confirm=True    # Skip confirmation
)

print()
print("=" * 80)
if success:
    print("✅ 测试完成")
else:
    print("❌ 测试失败")
print("=" * 80)

