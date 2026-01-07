# Scripts 清理计划 (2026-01-06)

## 需要保留的核心脚本

### 新创建的工具脚本（2026相关）
- `list_2026_sheets.py` - 列出2026文件夹中的所有sheet
- `process_2026_sheets.py` - 批量处理2026文件夹中的所有sheet
- `explore_folder_structure.py` - 探索Smartsheet文件夹结构

### 生产/运行脚本
- `deploy_renewal.py` - Renewal Workflow 部署脚本
- `run_renewal_production.py` - 手动运行 Renewal Workflow 生产环境
- `auto_stm1_calling.py` - 自动STM1调用工作流
- `run_stm1_now.py` - 立即运行STM1工作流

### 工具脚本
- `batch_update_missing_call_notes.py` - 批量更新缺失的调用备注
- `check_stm1_sheet.py` - STM1 sheet检查工具
- `production_readiness_check.py` - 生产环境就绪检查

### 测试脚本
- `test_comprehensive.py` - 全面详细测试
- `test_new_features.py` - 快速工作流测试

### 文档
- `README.md` - 脚本说明文档

## 需要删除的脚本

### 临时检查脚本（check_*.py）
- `check_actual_calling_order.py`
- `check_and_fix_workflow.md`
- `check_automation_issues.py`
- `check_available_customers.py`
- `check_call_notes_in_sheet.py`
- `check_called_rows.py`
- `check_cl1_run_status.py`
- `check_cl1_today.py`
- `check_customer.py`
- `check_github_actions.py`
- `check_recent_activity.py`
- `check_recent_called_rows.py`
- `check_recent_calls_count.py`
- `check_specific_customers.py`
- `check_stm1_last_friday.py`
- `check_stm1_progress.py`
- `check_stm1_running_now.py`
- `check_stm1_running.py`
- `check_stm1_status_detailed.py`
- `check_stm1_status.py`
- `check_today_workflow.py`
- `check_when_to_call_298.py`
- `check_why_not_calling.py`
- `check_why_skipped_298.py`
- `check_workflow_details.py`
- `check_workflow_issues.py`
- `check_workflow_logs.py`
- `check_workflow_status.md`
- `check_workflow_status.py`

### 临时分析脚本（analyze_*.py）
- `analyze_cl1_detailed.py`
- `analyze_cl1_yesterday.py`
- `analyze_why_no_calls.py`

### 调试脚本（debug_*.py）
- `debug_row.py`
- `debug_stm1_issue.py`

### 临时测试脚本（test_*.py，除了保留的）
- `test_auto_stm1_local.py`
- `test_cancellation_twice_daily.py`
- `test_cl1_same_day_past_due.py`
- `test_get_customers_ready.py`
- `test_row_298.py`
- `test_sorting.py`
- `test_token.py`

### 监控脚本（monitor_*.py）
- `monitor_stm1_simple.py`
- `monitor_stm1.py`

### 其他临时脚本
- `comprehensive_stm1_check.py`
- `comprehensive_test.py`
- `diagnose_automation_issue.py`
- `diagnose_automation_problem.py`
- `diagnose_cancellation_calls.py`
- `enable_stm1_now.py`
- `enable_workflow.py`
- `get_workflow_output.py`
- `manual_cl1_calling.py`
- `manual_run_cl1_now.py`
- `periodic_stm1_report.py`
- `quick_check_customers.py`
- `restart_stm1.py`
- `setup_and_enable_workflow.py`
- `setup_github_token.py`
- `start_stm1.py`
- `auto_start_stm1.py`

### PowerShell脚本（.ps1）
- `remove_stm1_autostart.ps1`
- `setup_stm1_autostart.ps1`

### 多余的文档文件（.md，除了README.md）
- `AUTOMATION_ISSUE_ANALYSIS.md`
- `CLEANUP_SUMMARY.md`
- `ENABLE_WORKFLOW_GUIDE.md`
- `GITHUB_ACTIONS_SETUP_GUIDE.md`
- `HOW_TO_GET_GITHUB_TOKEN.md`
- `QUICK_CHECK.md`
- `QUICK_ENABLE_STM1.md`
- `QUICK_ENABLE.md`
- `README_AUTOSTART.md`
- `README_WORKFLOW_CHECK.md`
- `SETUP_AUTOSTART_INSTRUCTIONS.md`
- `STM1_AUTOMATION_FAILURE_DIAGNOSIS.md`
- `TEST_CANCELLATION_TWICE_DAILY.md`
- `TEST_README.md`
- `TEST_RESULTS.md`

## 清理统计

- **保留**: 约 15 个核心脚本 + 1 个文档
- **删除**: 约 70+ 个临时脚本和文档
- **清理率**: 约 82%

